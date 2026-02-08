"""
Orchestration workflows for Episteme

These are higher-level workflows that coordinate multiple tasks/services.
Phase 0: Basic stubs
Phase 1: Signal extraction workflows
"""
import logging
from asgiref.sync import async_to_sync
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task
def assistant_response_workflow(thread_id: str, user_message_id: str):
    """
    Enhanced workflow with agent inflection detection
    
    Workflow:
    1. Check for agent confirmation (if pending suggestion)
    2. Analyze for agent inflection points (every N turns)
    3. Generate assistant response OR spawn agent
    4. Extract signals from user message (batched)
    
    Args:
        thread_id: Chat thread ID
        user_message_id: User message that triggered this workflow
    """
    from apps.chat.models import Message, ChatThread
    from apps.chat.services import ChatService
    
    # Get thread and message
    thread = ChatThread.objects.get(id=thread_id)
    user_message = Message.objects.get(id=user_message_id)
    
    # STEP 1: Check for agent confirmation
    # If there's a pending agent suggestion, check if user is confirming
    if thread.metadata and thread.metadata.get('pending_agent_suggestion'):
        from apps.agents.confirmation import check_for_agent_confirmation
        from apps.agents.orchestrator import AgentOrchestrator
        
        confirmation = async_to_sync(check_for_agent_confirmation)(thread, user_message)
        
        if confirmation and confirmation['confirmed']:
            # User confirmed! Spawn agent
            result = async_to_sync(AgentOrchestrator.run_agent_in_chat)(
                thread=thread,
                agent_type=confirmation['agent_type'],
                user=thread.user,
                **confirmation['params']
            )
            
            # Clear pending suggestion
            thread.metadata['pending_agent_suggestion'] = None
            thread.save()
            
            # Agent is running - workflow complete
            return {
                'status': 'agent_spawned',
                'agent_type': confirmation['agent_type'],
                **result
            }
    
    # STEP 2: Analyze for agent inflection points
    # Increment counter and check threshold
    thread.turns_since_agent_check = (thread.turns_since_agent_check or 0) + 1
    
    AGENT_CHECK_INTERVAL = 3  # Check every 3 turns
    
    should_check_agents = (
        thread.turns_since_agent_check >= AGENT_CHECK_INTERVAL or
        thread.last_agent_check_at is None
    )
    
    if should_check_agents:
        from apps.agents.inflection_detector import InflectionDetector
        from apps.agents.messages import create_agent_suggestion_message
        
        # Analyze for inflection points
        inflection = async_to_sync(InflectionDetector.analyze_for_agent_need)(thread)
        
        # Emit event for tracking
        from apps.events.services import EventService
        from apps.events.models import ActorType
        
        EventService.append(
            event_type='CONVERSATION_ANALYZED_FOR_AGENT',
            payload=inflection,
            actor_type=ActorType.SYSTEM,
            thread_id=thread.id,
            case_id=thread.primary_case.id if thread.primary_case else None
        )
        
        # Reset counter
        thread.turns_since_agent_check = 0
        thread.last_agent_check_at = timezone.now()
        thread.last_suggested_agent = inflection.get('suggested_agent', '')
        
        # If high confidence, create suggestion
        if inflection['needs_agent'] and inflection['confidence'] > 0.75:
            # Store pending suggestion
            thread.metadata = thread.metadata or {}
            thread.metadata['pending_agent_suggestion'] = inflection
            
            # Create suggestion message
            async_to_sync(create_agent_suggestion_message)(thread, inflection)
            
            thread.save()
            
            # Don't generate normal response - let user decide
            return {
                'status': 'agent_suggested',
                'agent_type': inflection['suggested_agent'],
                'confidence': inflection['confidence']
            }
        
        thread.save()
    
    # STEP 2.5: Check for proactive interventions (pattern detection)
    # This runs after agent checks but before generating response
    try:
        from apps.chat.interventions import InterventionService
        
        intervention_msg = InterventionService.check_and_intervene(thread)
        if intervention_msg:
            logger.info(
                "proactive_intervention_triggered",
                extra={
                    "thread_id": str(thread.id),
                    "message_id": str(intervention_msg.id),
                    "content_type": intervention_msg.content_type
                }
            )
    except Exception:
        logger.exception(
            "intervention_check_failed",
            extra={"thread_id": str(thread.id)}
        )
    
    # STEP 3: Generate normal assistant response (Phase 1: with memory integration)
    response = ChatService.generate_assistant_response(
        thread_id=thread.id,
        user_message_id=user_message.id
    )
    
    # Phase 1: Batched signal extraction with threshold
    # Accumulate messages and extract when threshold is met
    signals_extracted = 0
    try:
        from apps.signals.batch_extraction import (
            should_trigger_batch_extraction,
            get_unprocessed_messages,
            extract_signals_from_batch
        )
        
        # Accumulate message stats for batching
        thread.accumulate_for_extraction(len(user_message.content))
        
        # Check if we should trigger batch extraction (2 turns or 30 chars)
        if should_trigger_batch_extraction(thread, char_threshold=30, turn_threshold=2):
            # Get all unprocessed messages since last extraction
            unprocessed_messages = get_unprocessed_messages(thread)
            
            if unprocessed_messages:
                # Extract from batch in single LLM call
                signals_extracted = extract_signals_from_batch(
                    thread=thread,
                    messages=unprocessed_messages
                )
                
                logger.info(
                    "batch_signals_extracted",
                    extra={
                        "thread_id": str(thread.id),
                        "messages_in_batch": len(unprocessed_messages),
                        "signals_extracted": signals_extracted
                    }
                )

        else:
            logger.debug(
                "batch_threshold_not_met",
                extra={
                    "thread_id": str(thread.id),
                    "chars_accumulated": thread.chars_since_extraction,
                    "turns_accumulated": thread.turns_since_extraction
                }
            )
    except Exception:
        logger.exception(
            "batch_signal_extraction_failed",
            extra={
                "thread_id": str(thread.id),
                "message_id": str(user_message.id)
            }
        )

    # STEP 4: Check for structure readiness (progressive disclosure)
    # Only check if user has this preference enabled and no case exists
    try:
        user_prefs = thread.user.preferences
        
        if user_prefs.structure_auto_detect and not thread.primary_case:
            from apps.agents.structure_detector import StructureReadinessDetector
            from apps.signals.models import Signal
            
            # Check if we should evaluate structure readiness
            if StructureReadinessDetector.should_check_structure_readiness(
                thread, 
                sensitivity=user_prefs.structure_sensitivity
            ):
                # Get recent signals
                recent_signals = list(Signal.objects.filter(
                    thread=thread,
                    dismissed_at__isnull=True
                ).order_by('-sequence_index')[:20])
                
                # Fast threshold check first
                if StructureReadinessDetector.check_fast_thresholds(
                    thread, recent_signals, user_prefs.structure_sensitivity
                ):
                    # Run deep LLM analysis
                    structure_analysis = async_to_sync(
                        StructureReadinessDetector.analyze_structure_readiness
                    )(thread, recent_signals, user_prefs.structure_sensitivity)
                    
                    # If high confidence, suggest structure
                    if structure_analysis['ready'] and structure_analysis['confidence'] > 0.7:
                        # Emit suggestion event
                        from apps.events.services import EventService
                        from apps.events.models import EventType, ActorType
                        
                        EventService.append(
                            event_type=EventType.STRUCTURE_SUGGESTED,
                            payload=structure_analysis,
                            actor_type=ActorType.SYSTEM,
                            thread_id=thread.id,
                            case_id=thread.primary_case.id if thread.primary_case else None
                        )
                        
                        # Store suggestion in thread metadata
                        thread.metadata = thread.metadata or {}
                        thread.metadata['pending_structure_suggestion'] = structure_analysis
                        thread.metadata['last_structure_suggestion_at'] = timezone.now().isoformat()
                        thread.save(update_fields=['metadata'])
                        
                        logger.info(
                            "structure_suggested",
                            extra={
                                "thread_id": str(thread.id),
                                "structure_type": structure_analysis['structure_type'],
                                "confidence": structure_analysis['confidence']
                            }
                        )
    except Exception:
        logger.exception(
            "structure_detection_failed",
            extra={"thread_id": str(thread.id)},
        )
    
    # Title generation now happens inline in the SSE stream (unified_stream view)

    return {
        'status': 'completed',
        'message_id': str(response.id),
        'signals_extracted': signals_extracted,
    }


@shared_task
def generate_signal_embeddings(signal_ids: list):
    """
    Generate embeddings for signals (called after unified analysis).

    Args:
        signal_ids: List of signal IDs to generate embeddings for

    Returns:
        Dict with status and count
    """
    from apps.signals.models import Signal

    try:
        signals = Signal.objects.filter(id__in=signal_ids)
        generated = 0

        for signal in signals:
            # Skip if already has embedding
            if signal.embedding:
                continue

            # Generate embedding
            try:
                from apps.common.embeddings import generate_embedding
                embedding = generate_embedding(signal.text)
                signal.embedding = embedding
                signal.save(update_fields=['embedding'])
                generated += 1
            except Exception as e:
                logger.warning(f"Failed to generate embedding for signal {signal.id}: {e}")
                continue

        logger.info(
            "signal_embeddings_generated",
            extra={"count": generated, "total": len(signal_ids)}
        )

        return {
            'status': 'completed',
            'generated': generated,
            'total': len(signal_ids)
        }

    except Exception:
        logger.exception(
            "generate_signal_embeddings_failed",
            extra={"signal_ids": signal_ids}
        )
        return {
            'status': 'failed',
            'signal_ids': signal_ids
        }


@shared_task
def extract_signals_workflow(message_id: str):
    """
    Phase 1: Extract signals from a message

    Args:
        message_id: Message to extract signals from
    """
    # Phase 1 implementation
    pass


@shared_task
def draft_case_workflow(case_id: str):
    """
    Phase 1: Draft a case from recent signals
    
    Args:
        case_id: Case to draft
    """
    # Phase 1 implementation
    pass


@shared_task
def process_document_workflow(document_id: str):
    """
    Phase 2: Process document - chunk, embed, and index.
    
    This is the new document processing workflow that replaces
    signal extraction with semantic chunking.
    
    Workflow:
    1. Extract text from file
    2. Chunk document
    3. Generate embeddings
    4. Index in vector database
    5. Update document status
    
    Args:
        document_id: Document to process
    
    Returns:
        Processing result
    """
    from apps.projects.models import Document
    from apps.projects.services import DocumentService
    from apps.events.services import EventService
    from apps.events.models import EventType, ActorType
    
    try:
        document = Document.objects.get(id=document_id)
        
        # Process document
        DocumentService.process_document(document)
        
        # Emit event
        EventService.append(
            event_type=EventType.WORKFLOW_COMPLETED,
            payload={
                'workflow': 'process_document',
                'document_id': str(document.id),
                'chunks': document.chunk_count,
            },
            actor_type=ActorType.SYSTEM,
            case_id=document.case_id,
        )
        
        return {
            'status': 'completed',
            'document_id': str(document.id),
            'chunks_created': document.chunk_count,
            'indexed_at': document.indexed_at.isoformat() if document.indexed_at else None,
        }
        
    except Exception:
        logger.exception(
            "process_document_workflow_failed",
            extra={"document_id": str(document_id)},
        )
        # Update document status on failure
        try:
            document = Document.objects.get(id=document_id)
            document.processing_status = 'failed'
            document.save()
        except Exception:
            logger.exception(
                "process_document_workflow_status_update_failed",
                extra={"document_id": str(document_id)},
            )
        raise


@shared_task
def extract_document_signals_workflow(document_id: str):
    """
    DEPRECATED: This workflow has been removed.
    Use process_document_workflow instead.
    """
    raise NotImplementedError(
        "extract_document_signals_workflow is deprecated and has been removed. "
        "Use process_document_workflow instead."
    )


@shared_task
def generate_research_workflow(inquiry_id: str, user_id: int):
    """
    Generate research document asynchronously (Phase 2B).
    
    Workflow:
    1. Get inquiry and user
    2. Generate comprehensive research
    3. Create research document
    4. Emit completion event
    
    Args:
        inquiry_id: Inquiry to research
        user_id: User requesting research
    
    Returns:
        Document creation result
    """
    from apps.inquiries.models import Inquiry
    from apps.agents.document_generator import AIDocumentGenerator
    from django.contrib.auth.models import User
    from apps.events.services import EventService
    from apps.events.models import EventType, ActorType
    
    try:
        inquiry = Inquiry.objects.get(id=inquiry_id)
        user = User.objects.get(id=user_id)
        
        # Generate research
        generator = AIDocumentGenerator()
        research_doc = generator.generate_research_for_inquiry(inquiry, user)
        
        # Emit operational event
        EventService.append(
            event_type=EventType.WORKFLOW_COMPLETED,
            payload={
                'workflow': 'generate_research',
                'inquiry_id': str(inquiry_id),
                'document_id': str(research_doc.id),
                'title': research_doc.title
            },
            actor_type=ActorType.SYSTEM,
            case_id=inquiry.case_id
        )

        # Emit provenance events
        EventService.append(
            event_type=EventType.RESEARCH_COMPLETED,
            payload={
                'inquiry_id': str(inquiry_id),
                'inquiry_title': inquiry.title,
                'research_type': 'research',
                'document_id': str(research_doc.id),
                'title': research_doc.title,
            },
            actor_type=ActorType.ASSISTANT,
            case_id=inquiry.case_id,
        )
        EventService.append(
            event_type=EventType.DOCUMENT_ADDED,
            payload={
                'document_id': str(research_doc.id),
                'document_name': research_doc.title,
                'document_type': research_doc.document_type,
                'source': 'generated',
            },
            actor_type=ActorType.ASSISTANT,
            case_id=inquiry.case_id,
        )

        return {
            'status': 'completed',
            'document_id': str(research_doc.id),
            'title': research_doc.title,
            'document_type': research_doc.document_type
        }
    except Exception as e:
        logger.exception(
            "generate_research_workflow_failed",
            extra={"inquiry_id": str(inquiry_id), "user_id": user_id},
        )
        return {
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def generate_debate_workflow(inquiry_id: str, personas: list, user_id: int):
    """
    Generate debate document asynchronously (Phase 2B).
    
    Args:
        inquiry_id: Inquiry to debate
        personas: List of personas to simulate
        user_id: User requesting debate
    
    Returns:
        Document creation result
    """
    from apps.inquiries.models import Inquiry
    from apps.agents.document_generator import AIDocumentGenerator
    from django.contrib.auth.models import User
    from apps.events.services import EventService
    from apps.events.models import EventType, ActorType
    
    try:
        inquiry = Inquiry.objects.get(id=inquiry_id)
        user = User.objects.get(id=user_id)
        
        # Generate debate
        generator = AIDocumentGenerator()
        debate_doc = generator.generate_debate_for_inquiry(inquiry, personas, user)
        
        # Emit operational event
        EventService.append(
            event_type=EventType.WORKFLOW_COMPLETED,
            payload={
                'workflow': 'generate_debate',
                'inquiry_id': str(inquiry_id),
                'document_id': str(debate_doc.id),
                'personas': [p['name'] for p in personas]
            },
            actor_type=ActorType.SYSTEM,
            case_id=inquiry.case_id
        )

        # Emit provenance events
        EventService.append(
            event_type=EventType.RESEARCH_COMPLETED,
            payload={
                'inquiry_id': str(inquiry_id),
                'inquiry_title': inquiry.title,
                'research_type': 'debate',
                'document_id': str(debate_doc.id),
                'title': debate_doc.title,
            },
            actor_type=ActorType.ASSISTANT,
            case_id=inquiry.case_id,
        )
        EventService.append(
            event_type=EventType.DOCUMENT_ADDED,
            payload={
                'document_id': str(debate_doc.id),
                'document_name': debate_doc.title,
                'document_type': getattr(debate_doc, 'document_type', 'debate'),
                'source': 'generated',
            },
            actor_type=ActorType.ASSISTANT,
            case_id=inquiry.case_id,
        )

        return {
            'status': 'completed',
            'document_id': str(debate_doc.id),
            'title': debate_doc.title
        }
    except Exception as e:
        logger.exception(
            "generate_debate_workflow_failed",
            extra={"inquiry_id": str(inquiry_id), "user_id": user_id},
        )
        return {
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def generate_critique_workflow(inquiry_id: str, user_id: int):
    """
    Generate critique document asynchronously (Phase 2B).
    
    Args:
        inquiry_id: Inquiry to critique
        user_id: User requesting critique
    
    Returns:
        Document creation result
    """
    from apps.inquiries.models import Inquiry
    from apps.agents.document_generator import AIDocumentGenerator
    from django.contrib.auth.models import User
    from apps.events.services import EventService
    from apps.events.models import EventType, ActorType
    
    try:
        inquiry = Inquiry.objects.get(id=inquiry_id)
        user = User.objects.get(id=user_id)
        
        # Generate critique
        generator = AIDocumentGenerator()
        critique_doc = generator.generate_critique_for_inquiry(inquiry, user)
        
        # Emit operational event
        EventService.append(
            event_type=EventType.WORKFLOW_COMPLETED,
            payload={
                'workflow': 'generate_critique',
                'inquiry_id': str(inquiry_id),
                'document_id': str(critique_doc.id)
            },
            actor_type=ActorType.SYSTEM,
            case_id=inquiry.case_id
        )

        # Emit provenance events
        EventService.append(
            event_type=EventType.RESEARCH_COMPLETED,
            payload={
                'inquiry_id': str(inquiry_id),
                'inquiry_title': inquiry.title,
                'research_type': 'critique',
                'document_id': str(critique_doc.id),
                'title': critique_doc.title,
            },
            actor_type=ActorType.ASSISTANT,
            case_id=inquiry.case_id,
        )
        EventService.append(
            event_type=EventType.DOCUMENT_ADDED,
            payload={
                'document_id': str(critique_doc.id),
                'document_name': critique_doc.title,
                'document_type': getattr(critique_doc, 'document_type', 'critique'),
                'source': 'generated',
            },
            actor_type=ActorType.ASSISTANT,
            case_id=inquiry.case_id,
        )

        return {
            'status': 'completed',
            'document_id': str(critique_doc.id),
            'title': critique_doc.title
        }
    except Exception as e:
        logger.exception(
            "generate_critique_workflow_failed",
            extra={"inquiry_id": str(inquiry_id), "user_id": user_id},
        )
        return {
            'status': 'failed',
            'error': str(e)
        }
