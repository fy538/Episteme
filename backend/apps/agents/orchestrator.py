"""
Agent orchestration service

Manages agent execution with progress tracking and inline chat integration.
"""
import logging
import uuid as uuid_module
from typing import Dict, Any, List, Optional
from django.utils import timezone
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

from apps.chat.models import ChatThread, Message
from apps.chat.services import ChatService
from apps.events.services import EventService
from apps.events.models import EventType, ActorType


class AgentOrchestrator:
    """
    Orchestrate agent execution with progress tracking.
    
    Creates placeholder messages, emits progress events, and injects
    results back into chat for seamless user experience.
    """
    
    @staticmethod
    async def run_agent_in_chat(
        thread: ChatThread,
        agent_type: str,
        user,
        **params
    ) -> Dict[str, Any]:
        """
        Run an agent and stream results into chat
        
        Args:
            thread: Chat thread
            agent_type: 'research' | 'critique' | 'brief'
            user: User requesting
            **params: Agent-specific parameters (topic, target_signal_id, etc.)
        
        Returns:
            {
                'task_id': str,
                'correlation_id': str,
                'placeholder_message_id': str,
                'status': 'running'
            }
        """
        # Create correlation ID for this workflow
        correlation_id = uuid_module.uuid4()
        
        # Get case context
        case = thread.primary_case
        if not case:
            raise ValueError("Thread must have a linked case to run agents")
        
        # Load active skills for display
        skills = await sync_to_async(lambda: list(
            case.active_skills.filter(status='active')
        ))()
        skill_names = [s.name for s in skills]
        
        # Step 1: Create placeholder message in chat
        placeholder_content = AgentOrchestrator._build_placeholder_content(
            agent_type=agent_type,
            params=params,
            skill_names=skill_names
        )
        
        placeholder = await ChatService.create_assistant_message(
            thread_id=thread.id,
            content=placeholder_content,
            metadata={
                'type': 'agent_placeholder',
                'agent_type': agent_type,
                'correlation_id': str(correlation_id),
                'status': 'running',
                'started_at': timezone.now().isoformat(),
                'skills_loaded': skill_names
            }
        )
        
        # Step 2: Emit workflow start event
        start_event = await sync_to_async(EventService.append)(
            event_type=EventType.AGENT_WORKFLOW_STARTED,
            payload={
                'agent_type': agent_type,
                'thread_id': str(thread.id),
                'case_id': str(case.id),
                'placeholder_message_id': str(placeholder.id),
                'params': params,
                'skills_loaded': skill_names
            },
            actor_type=ActorType.SYSTEM,
            correlation_id=correlation_id,
            thread_id=thread.id,
            case_id=case.id
        )
        
        # Step 3: Execute agent workflow via registry dispatch
        from apps.agents.registry import AgentRegistry

        registry = AgentRegistry()
        descriptor = registry.get(agent_type)

        if not descriptor:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Build task kwargs from params + standard fields
        task_kwargs = {
            'case_id': str(case.id),
            'user_id': user.id,
            'correlation_id': str(correlation_id),
            'placeholder_message_id': str(placeholder.id),
        }

        # Inject case-scoped graph context so agents are graph-aware
        from apps.chat.context_assembly import ContextAssemblyService
        assembled = await ContextAssemblyService().assemble_for_agent(thread, case)
        if assembled.retrieval_context:
            task_kwargs['graph_context'] = assembled.retrieval_context

        # Agent-specific param mapping
        if agent_type == 'research':
            task_kwargs['topic'] = params.get('topic', case.position)
        elif agent_type == 'critique':
            target_signal_id = params.get('target_signal_id')
            if not target_signal_id:
                raise ValueError("target_signal_id is required for critique agent")
            task_kwargs['target_signal_id'] = target_signal_id

        task = descriptor.entry_point.delay(**task_kwargs)

        if not task:
            raise ValueError(f"Failed to start {agent_type} agent")
        
        # Step 4: Return immediately (workflow continues in background)
        return {
            'task_id': task.id,
            'correlation_id': str(correlation_id),
            'placeholder_message_id': str(placeholder.id),
            'status': 'running',
            'agent_type': agent_type
        }
    
    @staticmethod
    def _build_placeholder_content(
        agent_type: str,
        params: Dict,
        skill_names: List[str]
    ) -> str:
        """Build content for placeholder message while agent runs"""
        
        agent_emoji = {
            'research': '🔬',
            'critique': '🎯',
            'brief': '📋'
        }
        
        agent_display = {
            'research': 'Research Agent',
            'critique': 'Critique Agent',
            'brief': 'Brief Agent'
        }
        
        content = f"{agent_emoji.get(agent_type, '🤖')} **{agent_display.get(agent_type, 'Agent')} Running**\n\n"
        
        # Add what it's working on
        if agent_type == 'research' and params.get('topic'):
            content += f"**Topic**: {params['topic']}\n\n"
        elif agent_type == 'critique' and params.get('suggested_target'):
            content += f"**Critiquing**: {params['suggested_target']}\n\n"
        
        # Add skills being used
        if skill_names:
            content += f"**Using skills**: {', '.join(skill_names)}\n\n"
        
        content += "**Status**: Initializing...\n\n"
        content += "_This message will update with results when complete._"
        
        return content
    
    @staticmethod
    async def update_progress(
        correlation_id: str,
        step: str,
        message: str,
        placeholder_message_id: Optional[str] = None
    ):
        """
        Update agent progress (called from workflows)
        
        Args:
            correlation_id: Workflow correlation ID
            step: Progress step identifier
            message: Human-readable progress message
            placeholder_message_id: Optional message ID to update
        """
        # Emit progress event
        await sync_to_async(EventService.append)(
            event_type=EventType.AGENT_PROGRESS,
            payload={
                'step': step,
                'message': message,
                'timestamp': timezone.now().isoformat()
            },
            actor_type=ActorType.SYSTEM,
            correlation_id=correlation_id
        )
        
        # Update placeholder message if provided
        if placeholder_message_id:
            try:
                placeholder = await Message.objects.aget(id=placeholder_message_id)
                
                # Update content to show progress
                lines = placeholder.content.split('\n')
                
                # Replace status line
                for i, line in enumerate(lines):
                    if line.startswith('**Status**:'):
                        lines[i] = f"**Status**: {message}"
                        break
                
                placeholder.content = '\n'.join(lines)
                await placeholder.asave()
                
            except Message.DoesNotExist:
                logger.warning(
                    "placeholder_message_not_found",
                    extra={"placeholder_message_id": placeholder_message_id},
                )

    @staticmethod
    async def complete_agent(
        correlation_id: str,
        document_id: str,
        placeholder_message_id: str,
        blocks: List[Dict],
        generation_time_ms: int
    ):
        """
        Mark agent as complete and inject results into chat

        Args:
            correlation_id: Workflow correlation ID
            document_id: ID of created WorkingDocument
            placeholder_message_id: Placeholder message to replace
            blocks: Generated content blocks
            generation_time_ms: Time taken
        """
        # Emit completion event
        await sync_to_async(EventService.append)(
            event_type=EventType.AGENT_COMPLETED,
            payload={
                'document_id': document_id,
                'blocks_count': len(blocks),
                'generation_time_ms': generation_time_ms,
                'completed_at': timezone.now().isoformat()
            },
            actor_type=ActorType.SYSTEM,
            correlation_id=correlation_id
        )

        # Replace placeholder with results
        try:
            placeholder = await Message.objects.aget(id=placeholder_message_id)

            # Build result content
            result_content = AgentOrchestrator._build_result_content(
                document_id=document_id,
                blocks=blocks,
                generation_time_ms=generation_time_ms
            )

            placeholder.content = result_content
            placeholder.metadata['status'] = 'completed'
            placeholder.metadata['completed_at'] = timezone.now().isoformat()
            placeholder.metadata['document_id'] = document_id

            await placeholder.asave()

        except Message.DoesNotExist:
            logger.warning(
                "placeholder_message_not_found_on_complete",
                extra={
                    "placeholder_message_id": placeholder_message_id,
                    "document_id": document_id,
                },
            )

    @staticmethod
    def _build_result_content(
        document_id: str,
        blocks: List[Dict],
        generation_time_ms: int
    ) -> str:
        """Build content for completed agent result"""

        content = "✓ **Agent Complete**\n\n"

        # Add summary of blocks
        headings = [b for b in blocks if b.get('type') == 'heading']
        if headings:
            content += "**Sections**:\n"
            for heading in headings[:5]:  # First 5 headings
                content += f"- {heading.get('content', '')}\n"
            if len(headings) > 5:
                content += f"- ...and {len(headings) - 5} more\n"
            content += "\n"

        # Add time
        time_seconds = generation_time_ms / 1000
        content += f"**Generated in**: {time_seconds:.1f}s\n\n"

        # Add link to document
        content += f"[View full document](/working-documents/{document_id})\n\n"

        # Add first block as preview
        if blocks:
            first_content_block = next(
                (b for b in blocks if b.get('type') == 'paragraph'),
                None
            )
            if first_content_block:
                preview = first_content_block.get('content', '')[:200]
                if len(first_content_block.get('content', '')) > 200:
                    preview += "..."
                content += f"**Preview**:\n\n{preview}\n"

        return content
