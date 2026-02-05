"""
Smart readiness checklist generation service.

Generates context-aware checklist items based on case analysis.
"""
import logging
import json
from typing import List, Dict, Any

from apps.common.llm_providers import get_llm_provider
from apps.signals.models import Signal
from apps.inquiries.models import Inquiry
from .models import DEFAULT_READINESS_CHECKLIST

logger = logging.getLogger(__name__)


async def generate_smart_checklist(case) -> List[Dict[str, Any]]:
    """
    Generate AI-powered checklist based on case context.

    Analyzes:
    - Assumptions (untested → validation items)
    - Open inquiries (→ resolution items)
    - Decision question clarity
    - Alternatives mentioned
    - Decision criteria defined

    Returns:
        List of checklist item data dicts with fields:
        - description: str
        - is_required: bool
        - why_important: str
        - linked_inquiry_id: str | None
    """
    from asgiref.sync import sync_to_async

    try:
        provider = get_llm_provider('fast')

        # Gather case context (using sync_to_async for DB queries)
        @sync_to_async
        def get_assumptions():
            return list(Signal.objects.filter(
                case=case,
                type='assumption'
            ).values_list('text', flat=True)[:10])

        @sync_to_async
        def get_inquiries():
            return list(case.inquiries.all().values('id', 'title', 'status'))

        assumptions = await get_assumptions()
        inquiries = await get_inquiries()

        # Build prompt for hierarchical generation
        prompt = f"""You are analyzing a high-stakes decision and creating a hierarchical readiness checklist.

**DECISION CONTEXT:**
Case: {case.title}
Question: {case.decision_question or 'Not yet defined'}
Position: {case.position or 'Not yet defined'}

Detected Assumptions ({len(assumptions)}):
{chr(10).join(f'- {a}' for a in assumptions) if assumptions else '(None)'}

Open Inquiries ({len(inquiries)}):
{chr(10).join(f'- {i["title"]}' for i in inquiries) if inquiries else '(None)'}

**YOUR TASK:**
Create a hierarchical checklist with 3-4 PARENT categories, each containing 2-3 CHILD items.

**CRITICAL RULES:**
1. PARENT items have "parent_description": null
2. CHILD items have "parent_description": "<exact parent description>"
3. Parent descriptions in children MUST match parent descriptions EXACTLY
4. Return parents first, then their children grouped together

**EXAMPLE FORMAT (FOLLOW THIS EXACTLY):**
[
  {{"description": "Validate Critical Assumptions", "is_required": true, "why_important": "Assumptions drive the decision", "item_type": "validation", "parent_description": null, "linked_inquiry_title": null}},
  {{"description": "Test cost assumption with real data", "is_required": true, "why_important": "Cost drives feasibility", "item_type": "validation", "parent_description": "Validate Critical Assumptions", "linked_inquiry_title": "{inquiries[0]['title'] if inquiries else 'null'}"}},
  {{"description": "Validate timeline assumptions", "is_required": true, "why_important": "Timeline affects planning", "item_type": "validation", "parent_description": "Validate Critical Assumptions", "linked_inquiry_title": null}},

  {{"description": "Complete Key Investigations", "is_required": true, "why_important": "Research informs the decision", "item_type": "investigation", "parent_description": null, "linked_inquiry_title": null}},
  {{"description": "Analyze technical feasibility", "is_required": true, "why_important": "Technical limits constrain options", "item_type": "investigation", "parent_description": "Complete Key Investigations", "linked_inquiry_title": null}}
]

**ITEM TYPES:**
- validation: Test an assumption
- investigation: Research/inquiry
- analysis: Calculate/analyze
- stakeholder: Get input/alignment
- alternative: Evaluate options
- criteria: Define success metrics

**GUIDELINES:**
- Keep parent descriptions SHORT (under 50 chars) for exact matching
- Each parent should have 2-3 children minimum
- Link children to inquiries when relevant (use exact inquiry title from list above)
- All items is_required: true
- Be specific to THIS case

NOW GENERATE THE CHECKLIST. Return ONLY valid JSON array, no markdown, no explanation."""

        # Call LLM
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You help people identify what they need to complete before making high-stakes decisions. Be specific and actionable."
        ):
            full_response += chunk.content

        # Parse JSON response
        items_data = _parse_json_response(full_response)

        # Debug: Log what we got
        logger.info(f"Parsed {len(items_data)} items from LLM")
        parents_in_response = sum(1 for item in items_data if not item.get('parent_description'))
        logger.info(f"Items with parent_description=null: {parents_in_response}")

        # Link to actual inquiries by matching titles
        for item in items_data:
            if item.get('linked_inquiry_title'):
                # Find inquiry with matching title (fuzzy match)
                inquiry_title = item['linked_inquiry_title']
                matching_inquiry = next(
                    (inq for inq in inquiries if inquiry_title.lower() in inq['title'].lower()),
                    None
                )
                item['linked_inquiry_id'] = str(matching_inquiry['id']) if matching_inquiry else None
            else:
                item['linked_inquiry_id'] = None

        # Build hierarchy (link children to parents)
        items_with_hierarchy = _build_hierarchy(items_data)

        logger.info(f"Generated {len(items_with_hierarchy)} smart checklist items for case {case.id}")
        return items_with_hierarchy

    except Exception as e:
        logger.error(f"Failed to generate smart checklist for case {case.id}: {e}")
        # Fallback to defaults
        return DEFAULT_READINESS_CHECKLIST


def _build_hierarchy(items_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build parent-child relationships from flat list.

    Items with parent_description get linked to their parent.
    If no hierarchy exists, intelligently groups items into parent categories.

    Returns the same list with parent_description_matched added to children.
    """
    # Create a map of description -> item (for parents)
    parent_map = {}
    for item in items_data:
        if not item.get('parent_description'):
            parent_map[item['description']] = item

    # Link children to parents
    children_count = 0
    for item in items_data:
        parent_desc = item.get('parent_description')
        if parent_desc and parent_desc in parent_map:
            # Mark this item as having a parent (parent_id will be set in view after creation)
            item['parent_description_matched'] = parent_desc
            children_count += 1
            logger.debug(f"Matched child '{item['description'][:40]}' to parent '{parent_desc[:40]}'")
        else:
            item['parent_description_matched'] = None
            if parent_desc:
                logger.warning(f"Could not find parent '{parent_desc}' for child '{item['description'][:40]}'. Available parents: {list(parent_map.keys())}")

    logger.info(f"Hierarchy: {len(parent_map)} parents, {children_count} children")

    # If no hierarchy was created, apply intelligent grouping
    if children_count == 0 and len(items_data) > 4:
        logger.info("No hierarchy in AI response, applying intelligent grouping")
        return _create_smart_hierarchy(items_data)

    return items_data


def _create_smart_hierarchy(items_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Intelligently group flat items into parent-child hierarchy.

    Groups by item_type to create meaningful categories.
    """
    # Group items by type
    by_type = {}
    for item in items_data:
        item_type = item.get('item_type', 'custom')
        if item_type not in by_type:
            by_type[item_type] = []
        by_type[item_type].append(item)

    # Create hierarchy
    hierarchical_items = []

    # Type to parent description mapping
    type_labels = {
        'validation': 'Validate Key Assumptions',
        'investigation': 'Complete Critical Research',
        'analysis': 'Perform Required Analysis',
        'stakeholder': 'Secure Stakeholder Alignment',
        'alternative': 'Evaluate Alternatives',
        'criteria': 'Define Decision Criteria',
        'custom': 'Other Readiness Items',
    }

    # Create parent + children for each type that has items
    for item_type, type_items in by_type.items():
        if len(type_items) == 0:
            continue

        # Skip if only 1-2 items of this type - keep them flat
        if len(type_items) <= 2:
            for item in type_items:
                item['parent_description_matched'] = None
                hierarchical_items.append(item)
            continue

        # Create parent
        parent_desc = type_labels.get(item_type, f'{item_type.title()} Items')
        parent = {
            'description': parent_desc,
            'is_required': True,
            'why_important': f"Completing {item_type} items ensures decision readiness",
            'item_type': item_type,
            'parent_description': None,
            'parent_description_matched': None,
            'linked_inquiry_title': None,
            'linked_inquiry_id': None,
        }
        hierarchical_items.append(parent)

        # Add children under this parent
        for item in type_items:
            item['parent_description_matched'] = parent_desc
            hierarchical_items.append(item)

    logger.info(f"Created smart hierarchy: {len(by_type)} parents, {len(items_data)} total items")
    return hierarchical_items


def _parse_json_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Parse LLM JSON response, handling markdown code blocks.

    Returns:
        List of checklist item dicts
    """
    try:
        # Clean up markdown code blocks
        text = response_text.strip()
        if text.startswith("```"):
            # Extract content between code fences
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
                # Remove language identifier (e.g., "json")
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

        # Parse JSON
        items = json.loads(text)

        # Validate structure
        if not isinstance(items, list):
            raise ValueError("Response is not a JSON array")

        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Item is not a JSON object")
            if 'description' not in item:
                raise ValueError("Item missing 'description' field")

        return items

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse JSON response: {e}. Using defaults.")
        return DEFAULT_READINESS_CHECKLIST
