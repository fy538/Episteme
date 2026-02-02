"""
Orchestration workflows for Episteme

These are higher-level workflows that coordinate multiple tasks/services.
Phase 0: Basic stubs
Phase 1: Signal extraction workflows
"""
import logging
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
    import asyncio
    
    # Get thread and message
    thread = ChatThread.objects.get(id=thread_id)
    user_message = Message.objects.get(id=user_message_id)
    
    # STEP 1: Check for agent confirmation
    # If there's a pending agent suggestion, check if user is confirming
    if thread.metadata and thread.metadata.get('pending_agent_suggestion'):
        from apps.agents.confirmation import check_for_agent_confirmation
        from apps.agents.orchestrator import AgentOrchestrator
        
        confirmation = asyncio.run(check_for_agent_confirmation(thread, user_message))
        
        if confirmation and confirmation['confirmed']:
            # User confirmed! Spawn agent
            result = asyncio.run(AgentOrchestrator.run_agent_in_chat(
                thread=thread,
                agent_type=confirmation['agent_type'],
                user=thread.user,
                **confirmation['params']
            ))
            
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
        inflection = asyncio.run(InflectionDetector.analyze_for_agent_need(thread))
        
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
            asyncio.run(create_agent_suggestion_message(thread, inflection))
            
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
        
        # Check if we should trigger batch extraction
        if should_trigger_batch_extraction(thread, char_threshold=500, turn_threshold=5):
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
                    structure_analysis = asyncio.run(
                        StructureReadinessDetector.analyze_structure_readiness(
                            thread, recent_signals, user_prefs.structure_sensitivity
                        )
                    )
                    
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
    
    # Trigger async title generation (best-effort)
    try:
        generate_chat_title_workflow.delay(thread_id=str(thread.id))
    except Exception:
        logger.exception(
            "chat_title_task_enqueue_failed",
            extra={"thread_id": str(thread.id)},
        )
    
    return {
        'status': 'completed',
        'message_id': str(response.id),
        'signals_extracted': signals_extracted,
    }


@shared_task
def generate_chat_title_workflow(thread_id: str):
    """
    Generate a concise title for a chat thread.

    Trigger rules:
    - After 2 user messages, OR
    - After 1 user message if it's > 200 chars
    - Only if title is blank or "New Chat"
    """
    from apps.chat.models import ChatThread, Message, MessageRole
    from apps.common.ai_services import generate_chat_title
    import asyncio

    try:
        thread = ChatThread.objects.get(id=thread_id)

        if thread.title and thread.title != "New Chat":
            return {"status": "skipped", "reason": "title_already_set"}

        user_messages = Message.objects.filter(
            thread=thread,
            role=MessageRole.USER
        ).order_by('created_at')

        count = user_messages.count()
        if count == 0:
            return {"status": "skipped", "reason": "no_user_messages"}

        first_msg = user_messages.first()
        if count < 2 and len(first_msg.content) <= 200:
            return {"status": "skipped", "reason": "threshold_not_met"}

        messages_text = [msg.content for msg in user_messages[:5]]
        title = asyncio.run(generate_chat_title(messages_text))

        if title:
            thread.title = title
            thread.save(update_fields=['title'])
            return {"status": "completed", "title": title}

        return {"status": "skipped", "reason": "empty_title"}
    except Exception:
        logger.exception("generate_chat_title_failed", extra={"thread_id": thread_id})
        return {"status": "failed"}


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
    DEPRECATED: Use process_document_workflow instead.
    
    Phase 2: Extract signals from an uploaded document
    
    This workflow is deprecated in favor of chunking and vector search.
    Signal extraction from documents is lossy and doesn't preserve context.
    
    Args:
        document_id: Document to process
    """
    import warnings
    warnings.warn(
        "extract_document_signals_workflow is deprecated. "
        "Use process_document_workflow instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    from apps.projects.models import Document
    from apps.signals.document_extractors import get_document_extractor
    from apps.events.services import EventService
    from apps.events.models import EventType, ActorType
    
    try:
        document = Document.objects.get(id=document_id)
        
        # Update status
        document.processing_status = 'processing'
        document.save()
        
        # Extract signals
        extractor = get_document_extractor()
        signals = extractor.extract_from_document(document)
        
        # Save signals with events
        for signal in signals:
            # Create event
            event = EventService.append(
                event_type=EventType.SIGNAL_EXTRACTED,
                payload={
                    'signal_type': signal.type,
                    'text': signal.text,
                    'confidence': signal.confidence,
                    'source_type': 'document',
                    'document_id': str(document.id),
                },
                actor_type=ActorType.SYSTEM,
                case_id=document.case_id,
            )
            
            # Link event and save
            signal.event_id = event.id
            signal.save()
        
        # Update document
        document.processing_status = 'completed'
        document.signals_extracted = len(signals)
        document.save()
        
        return {
            'status': 'completed',
            'document_id': str(document.id),
            'signals_extracted': len(signals),
        }
        
    except Exception:
        logger.exception(
            "extract_document_signals_workflow_failed",
            extra={"document_id": str(document_id)},
        )
        # Update document status
        try:
            document = Document.objects.get(id=document_id)
            document.processing_status = 'failed'
            document.save()
        except Exception:
            logger.exception(
                "extract_document_signals_workflow_status_update_failed",
                extra={"document_id": str(document_id)},
            )
        raise


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
        
        # Emit event
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
        
        # Emit event
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
        
        # Emit event
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
