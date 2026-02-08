"""
Agentic Document Tasks

Multi-step document editing with planning, execution, and self-review.
Handles complex tasks like:
- "Rewrite the risks section with our new market research"
- "Add citations to all claims from uploaded documents"
- "Restructure the brief to follow a different format"
"""
import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from asgiref.sync import async_to_sync

from apps.common.llm_providers import get_llm_provider

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskStep:
    id: str
    description: str
    status: str  # pending, in_progress, completed, failed
    action_type: str  # add, replace, delete, restructure
    target_section: Optional[str]
    original_content: Optional[str]
    new_content: Optional[str]
    error: Optional[str] = None


@dataclass
class AgenticTask:
    id: str
    task_description: str
    status: TaskStatus
    plan: List[TaskStep]
    original_content: str
    current_content: str
    final_content: Optional[str]
    review_notes: Optional[str]
    created_at: str
    completed_at: Optional[str] = None


def stream_agentic_task(
    task_description: str,
    document_content: str,
    case_context: Dict[str, Any],
):
    """
    Streaming version of execute_agentic_task that yields SSE events
    as the task progresses through planning, execution, and review.

    Yields dicts with keys: event (str), data (dict)
    """
    import json

    task_id = str(uuid.uuid4())
    provider = get_llm_provider('default')

    # Phase 1: Planning
    yield {'event': 'phase', 'data': {'phase': 'planning', 'task_id': task_id}}

    plan = _generate_plan(task_description, document_content, case_context, provider)

    if not plan:
        yield {'event': 'error', 'data': {'error': 'Failed to generate execution plan'}}
        return

    yield {
        'event': 'plan',
        'data': {
            'steps': [
                {'id': s['id'], 'description': s['description'], 'action_type': s['action_type'],
                 'target_section': s.get('target_section')}
                for s in plan
            ],
        },
    }

    # Phase 2: Execution
    yield {'event': 'phase', 'data': {'phase': 'executing'}}

    current_content = document_content
    executed_steps = []
    changes = []

    for step in plan:
        yield {'event': 'step_start', 'data': {'step_id': step['id'], 'description': step['description']}}

        try:
            result = _execute_step(step, current_content, case_context, provider)
            step['status'] = 'completed'
            step['new_content'] = result.get('new_content')

            if result.get('changed') and result.get('new_content'):
                changes.append({
                    'step_id': step['id'],
                    'type': step['action_type'],
                    'description': step['description'],
                    'before': current_content,
                    'after': result['new_content'],
                })
                current_content = result['new_content']

            executed_steps.append(step)
            yield {'event': 'step_complete', 'data': {'step_id': step['id'], 'status': 'completed'}}
        except Exception as e:
            step['status'] = 'failed'
            step['error'] = str(e)
            executed_steps.append(step)
            yield {'event': 'step_complete', 'data': {'step_id': step['id'], 'status': 'failed', 'error': str(e)}}

    # Phase 3: Review
    yield {'event': 'phase', 'data': {'phase': 'reviewing'}}

    review_result = _review_changes(
        task_description, document_content, current_content, executed_steps, provider
    )

    final_content = current_content
    if review_result.get('refinements'):
        final_content = _apply_refinements(current_content, review_result['refinements'], provider)

    yield {'event': 'review', 'data': {
        'score': review_result.get('score', 0),
        'notes': review_result.get('notes', ''),
    }}

    # Done
    yield {'event': 'done', 'data': {
        'task_id': task_id,
        'status': TaskStatus.COMPLETED.value,
        'plan': executed_steps,
        'original_content': document_content,
        'final_content': final_content,
        'diff_summary': _generate_diff_summary(document_content, final_content),
        'review_notes': review_result.get('notes', ''),
        'review_score': review_result.get('score', 0),
        'changes': changes,
    }}


def execute_agentic_task(
    task_description: str,
    document_content: str,
    case_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute a complex document editing task using an agentic approach.

    Steps:
    1. Plan: Break down the task into concrete steps
    2. Execute: Apply each step to the document
    3. Review: Self-critique and refine the result

    Returns:
    {
        task_id: str,
        status: str,
        plan: [{id, description, status, ...}],
        original_content: str,
        final_content: str,
        diff_summary: str,
        review_notes: str,
        changes: [{type, location, before, after}]
    }
    """
    task_id = str(uuid.uuid4())
    provider = get_llm_provider('default')  # Use stronger model for agentic tasks

    # Phase 1: Planning
    plan = _generate_plan(task_description, document_content, case_context, provider)

    if not plan:
        return {
            'task_id': task_id,
            'status': TaskStatus.FAILED.value,
            'error': 'Failed to generate execution plan',
            'original_content': document_content,
            'final_content': document_content,
        }

    # Phase 2: Execution
    current_content = document_content
    executed_steps = []
    changes = []

    for step in plan:
        try:
            result = _execute_step(step, current_content, case_context, provider)
            step['status'] = 'completed'
            step['new_content'] = result.get('new_content')

            if result.get('changed') and result.get('new_content'):
                changes.append({
                    'step_id': step['id'],
                    'type': step['action_type'],
                    'description': step['description'],
                    'before': current_content,
                    'after': result['new_content'],
                })
                current_content = result['new_content']

            executed_steps.append(step)
        except Exception as e:
            step['status'] = 'failed'
            step['error'] = str(e)
            executed_steps.append(step)
            # Continue with remaining steps even if one fails

    # Phase 3: Review
    review_result = _review_changes(
        task_description,
        document_content,
        current_content,
        executed_steps,
        provider
    )

    # Apply review refinements if any
    final_content = current_content
    if review_result.get('refinements'):
        final_content = _apply_refinements(
            current_content,
            review_result['refinements'],
            provider
        )

    return {
        'task_id': task_id,
        'status': TaskStatus.COMPLETED.value,
        'plan': executed_steps,
        'original_content': document_content,
        'final_content': final_content,
        'diff_summary': _generate_diff_summary(document_content, final_content),
        'review_notes': review_result.get('notes', ''),
        'review_score': review_result.get('score', 0),
        'changes': changes,
    }


def _generate_plan(
    task_description: str,
    content: str,
    context: Dict[str, Any],
    provider
) -> List[Dict[str, Any]]:
    """Generate an execution plan for the task."""

    prompt = f"""You are planning how to edit a document. Break down the task into concrete, executable steps.

## Task
{task_description}

## Current Document
{content[:3000]}{'...(truncated)' if len(content) > 3000 else ''}

## Available Context
- Decision question: {context.get('decision_question', 'Not specified')}
- Number of signals: {len(context.get('signals', []))}
- Number of inquiries: {len(context.get('inquiries', []))}

## Instructions
Create a plan with 2-6 concrete steps. Each step should be:
- Specific and actionable
- Independent enough to execute separately
- Clear about what section/content it affects

Return JSON array:
[
  {{
    "id": "step_1",
    "description": "Add risk assessment section after the analysis",
    "action_type": "add",  // add, replace, delete, restructure
    "target_section": "After Analysis section",
    "rationale": "The document lacks risk discussion"
  }}
]

Return ONLY the JSON array."""

    async def generate():
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You break down document editing tasks into clear, executable steps."
        ):
            full_response += chunk.content

        try:
            response_text = full_response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            steps = json.loads(response_text)
            for step in steps:
                step['status'] = 'pending'
                step['original_content'] = None
                step['new_content'] = None
            return steps
        except Exception as e:
            logger.warning(f"Failed to parse plan: {e}")
            return []

    return async_to_sync(generate)()


def _execute_step(
    step: Dict[str, Any],
    content: str,
    context: Dict[str, Any],
    provider
) -> Dict[str, Any]:
    """Execute a single step of the plan."""

    signals_context = ""
    if context.get('signals'):
        signals_context = "\n".join([
            f"- [{s.get('signal_type')}] {s.get('content', '')[:100]}"
            for s in context.get('signals', [])[:10]
        ])

    prompt = f"""Execute this document editing step.

## Step to Execute
Description: {step['description']}
Action type: {step['action_type']}
Target: {step.get('target_section', 'Not specified')}

## Current Document
{content}

## Available Evidence/Signals
{signals_context or 'No signals available'}

## Instructions
Execute the step by providing the COMPLETE updated document.
- For "add": Insert new content at the appropriate location
- For "replace": Find and replace the relevant content
- For "delete": Remove the specified content
- For "restructure": Reorganize as needed

Return JSON:
{{
  "changed": true,
  "new_content": "The complete updated document content...",
  "explanation": "What was changed and why"
}}

Return ONLY the JSON object."""

    async def execute():
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You execute document editing steps precisely and completely."
        ):
            full_response += chunk.content

        try:
            response_text = full_response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            return json.loads(response_text)
        except Exception as e:
            logger.warning(f"Failed to execute step: {e}")
            return {'changed': False, 'new_content': content, 'error': str(e)}

    return async_to_sync(execute)()


def _review_changes(
    task_description: str,
    original: str,
    modified: str,
    steps: List[Dict[str, Any]],
    provider
) -> Dict[str, Any]:
    """Self-review the changes made."""

    steps_summary = "\n".join([
        f"- {s['description']} ({s['status']})"
        for s in steps
    ])

    prompt = f"""Review the document changes made for this task.

## Original Task
{task_description}

## Steps Executed
{steps_summary}

## Original Document (first 1500 chars)
{original[:1500]}

## Modified Document (first 1500 chars)
{modified[:1500]}

## Review Criteria
1. Did the changes accomplish the task?
2. Is the modified document coherent and well-structured?
3. Are there any issues introduced by the changes?
4. What refinements would improve the result?

Return JSON:
{{
  "score": 85,  // 0-100, how well the task was accomplished
  "notes": "Summary of what was done well and what could be improved",
  "issues": ["List of any issues found"],
  "refinements": [
    {{
      "type": "fix" | "improve",
      "description": "What to refine",
      "suggested_change": "Specific change to make"
    }}
  ]
}}

Return ONLY the JSON object."""

    async def review():
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You critically review document changes and identify improvements."
        ):
            full_response += chunk.content

        try:
            response_text = full_response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            return json.loads(response_text)
        except Exception as e:
            logger.warning(f"Failed to parse review: {e}")
            return {'score': 70, 'notes': 'Review completed', 'refinements': []}

    return async_to_sync(review)()


def _apply_refinements(
    content: str,
    refinements: List[Dict[str, Any]],
    provider
) -> str:
    """Apply review refinements to the content."""
    if not refinements:
        return content

    # Only apply critical refinements (fixes)
    fixes = [r for r in refinements if r.get('type') == 'fix']
    if not fixes:
        return content

    refinements_text = "\n".join([
        f"- {r['description']}: {r.get('suggested_change', '')}"
        for r in fixes
    ])

    prompt = f"""Apply these refinements to the document.

## Refinements to Apply
{refinements_text}

## Current Document
{content}

Return the COMPLETE refined document content.
Return ONLY the document content, no JSON or explanation."""

    async def refine():
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You apply document refinements precisely."
        ):
            full_response += chunk.content

        return full_response.strip()

    return async_to_sync(refine)()


def _generate_diff_summary(original: str, modified: str) -> str:
    """Generate a human-readable summary of changes."""
    original_lines = original.split('\n')
    modified_lines = modified.split('\n')

    added = len(modified_lines) - len(original_lines)
    char_diff = len(modified) - len(original)

    if added > 0:
        lines_msg = f"{added} lines added"
    elif added < 0:
        lines_msg = f"{abs(added)} lines removed"
    else:
        lines_msg = "same line count"

    if char_diff > 0:
        chars_msg = f"{char_diff} characters added"
    elif char_diff < 0:
        chars_msg = f"{abs(char_diff)} characters removed"
    else:
        chars_msg = "same length"

    return f"{lines_msg}, {chars_msg}"
