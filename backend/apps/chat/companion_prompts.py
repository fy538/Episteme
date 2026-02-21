"""
Prompts for the organic companion — structure generation and update.
"""
import json
from typing import Optional


STRUCTURE_TYPE_DESCRIPTIONS = {
    'assumption_surface': 'Extracting beliefs and assumptions embedded in what was said — things being treated as given without evidence',
    'angle_map': 'Mapping the angles/dimensions being explored in the conversation, including gaps not yet discussed',
    'decision_tree': 'Comparing options or making a choice between alternatives',
    'checklist': 'A list of things to do, verify, or check off',
    'comparison': 'Evaluating alternatives side by side on multiple criteria',
    'exploration_map': 'Exploring a broad topic area with multiple sub-areas (richer than angle_map — use when areas have depth)',
    'flow': 'Understanding a process, sequence, or pipeline',
    'constraint_list': 'Accumulating constraints, requirements, and limitations',
    'pros_cons': 'Weighing advantages vs disadvantages of a specific option',
    'concept_map': 'Understanding how concepts relate to each other',
}


STRUCTURE_SCHEMAS = {
    'assumption_surface': {
        'context': 'What the user is reasoning about',
        'assumptions': [{
            'text': 'The assumption being made',
            'source': 'stated | inferred | implicit',
            'risk': 'high | medium | low',
        }],
    },
    'angle_map': {
        'topic': 'What the conversation is about',
        'angles': [{
            'label': 'Angle or dimension name',
            'status': 'opened | touched | not_yet_discussed',
            'source': 'Brief note on where this came from or why it matters',
        }],
    },
    'decision_tree': {
        'question': 'The main decision question',
        'branches': [{
            'label': 'Option name',
            'detail': 'Explanation',
            'status': 'viable | eliminated | preferred | exploring',
            'reason': 'Why this status',
            'children': 'Optional sub-branches (same shape)',
        }],
    },
    'checklist': {
        'title': 'Checklist title',
        'items': [{
            'text': 'Item description',
            'status': 'pending | done | blocked | not_applicable',
            'detail': 'Additional detail',
        }],
    },
    'comparison': {
        'comparing': 'What we are comparing',
        'options': ['Option A', 'Option B'],
        'criteria': [{
            'criterion': 'Criterion name',
            'values': {'Option A': 'assessment', 'Option B': 'assessment'},
            'winner': 'Option name or null',
        }],
    },
    'exploration_map': {
        'center': 'Main topic',
        'areas': [{
            'label': 'Area name',
            'summary': 'What we know',
            'status': 'explored | partially_explored | unexplored',
            'open_questions': ['Question 1'],
        }],
    },
    'flow': {
        'title': 'Process name',
        'steps': [{
            'label': 'Step name',
            'detail': 'What happens',
            'status': 'understood | unclear | blocked',
        }],
    },
    'constraint_list': {
        'topic': 'What is being constrained',
        'constraints': [{
            'text': 'Constraint description',
            'source': 'Where this came from',
            'impact': 'How it affects the decision',
        }],
    },
    'pros_cons': {
        'subject': 'What is being evaluated',
        'pros': [{'point': 'Advantage', 'weight': 'high | medium | low'}],
        'cons': [{'point': 'Disadvantage', 'weight': 'high | medium | low'}],
    },
    'concept_map': {
        'title': 'Map title',
        'nodes': [{'label': 'Concept', 'description': 'Brief explanation'}],
        'connections': [{'from': 'Concept A', 'to': 'Concept B', 'relation': 'How they relate'}],
    },
}


def build_structure_update_prompt(
    messages: list[dict],
    current_structure: Optional[dict] = None,
    project_context: Optional[str] = None,
    user_context: Optional[dict] = None,
) -> str:
    """
    Build the prompt for structure generation/update.

    When creating (no current_structure), uses the full conversation.
    When updating, uses only the current structure + recent messages to save tokens.

    Args:
        messages: List of {role, content} dicts
                  - Full conversation on first creation
                  - Only recent messages (last ~6) on update
        current_structure: Current structure dict if updating, None if creating
        project_context: Optional project summary for grounding
        user_context: Optional dict with user stats for first-session awareness
    """
    conversation_text = "\n\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in messages
    ])

    type_list = "\n".join([
        f"  - {t}: {desc}"
        for t, desc in STRUCTURE_TYPE_DESCRIPTIONS.items()
    ])

    schema_text = json.dumps(STRUCTURE_SCHEMAS, indent=2)

    current_structure_section = ""
    if current_structure:
        current_structure_section = f"""
CURRENT STRUCTURE (your starting point — update based on the RECENT MESSAGES below):
{json.dumps(current_structure, indent=2)}
"""

    project_section = ""
    if project_context:
        project_section = f"""
PROJECT CONTEXT (the conversation is happening within this project):
{project_context}
"""

    user_context_section = ""
    if user_context:
        is_first = user_context.get('is_first_thread', False)
        user_context_section = f"""
USER CONTEXT:
First-time user: {'Yes' if is_first else 'No'}
Thread count: {user_context.get('thread_count', 0)}
Projects: {user_context.get('project_count', 0)}
Documents: {user_context.get('document_count', 0)}
Cases: {user_context.get('case_count', 0)}
"""

    if current_structure:
        # Update mode: structure exists, only recent messages provided
        return f"""Update this conversation structure based on the recent messages.

The current structure already captures the conversation's accumulated state.
Focus only on what the RECENT MESSAGES change — new facts, resolved questions,
newly eliminated options, or a shift in structure type.

RECENT MESSAGES:
{conversation_text}
{project_section}{current_structure_section}{user_context_section}
YOUR TASK:
1. Read the recent messages and understand what changed.
2. Decide if the structure type should change (rare) or stay the same (common):
{type_list}
3. Update the structure content. Preserve what hasn't changed.
4. Update the three tracking lists:
   - established: Add new confirmed facts. Keep existing unless explicitly contradicted.
   - open_questions: Add new questions. Move answered ones to established. Remove resolved ones.
   - eliminated: Add newly ruled-out options with reasons. Keep existing.
5. Rewrite context_summary: A compact (~150-200 token) text capturing what the AI needs to know
   to stay on track. Focus on: current direction, key constraints, and what NOT to repeat.
6. Assess topic_continuity — how the recent messages relate to the previous topic:
   - "continuous": Same topic, natural progression (most common — default to this if unsure)
   - "partial_shift": Related but meaningfully different angle or sub-topic
   - "discontinuous": Entirely new topic, unrelated to previous discussion
7. If topic shifted (partial_shift or discontinuous), provide a topic_label: a brief 3-5 word
   label for the NEW topic being discussed.

ANNOTATION TYPES NOTE:
assumption_surface and angle_map are ANNOTATION types — they extract structure from what was
ALREADY SAID in the conversation. They do NOT generate new ideas. The only generative element
allowed is noting gaps (angles marked 'not_yet_discussed' or implicit assumptions). Everything
else must trace back to the conversation.

FIRST-SESSION NOTE:
If USER CONTEXT shows a first-time user, keep the context_summary oriented toward helping
them understand how the companion tracks and structures their reasoning. Mention unused
capabilities (projects for document analysis, cases for rigorous decisions) when naturally
relevant to the conversation. Once the user has multiple threads, drop this onboarding framing.

STRUCTURE SCHEMAS (use the schema for your chosen type):
{schema_text}

Return ONLY valid JSON in this exact format:
{{
  "structure_type": "one of the types listed above",
  "content": {{ ... structure matching the chosen type's schema ... }},
  "established": ["fact 1", "fact 2"],
  "open_questions": ["question 1", "question 2"],
  "eliminated": ["option X (reason)", "option Y (reason)"],
  "context_summary": "Compact summary for chat context injection...",
  "topic_continuity": "continuous | partial_shift | discontinuous",
  "topic_label": "Brief topic label (3-5 words)"
}}"""
    else:
        # Creation mode: no existing structure, full conversation provided
        return f"""Analyze this conversation and produce an organic structure that captures its shape.

CONVERSATION:
{conversation_text}
{project_section}{user_context_section}
YOUR TASK:
1. Read the conversation and understand the topic being explored.
2. Choose the structure type that BEST fits what's being discussed:
{type_list}
3. Generate the structure content as JSON matching that type's schema.
4. Extract three tracking lists:
   - established: Confirmed facts, constraints, or decisions from the conversation
   - open_questions: Unresolved questions (both explicitly asked and implicitly raised)
   - eliminated: Options or approaches that have been ruled out (include brief reason)
5. Write a context_summary: A compact (~150-200 token) text capturing what the AI needs to know
   to stay on track in subsequent responses. Focus on: current exploration direction,
   key constraints, and what NOT to repeat.
6. Provide a topic_label: a brief 3-5 word label for the main topic of this conversation.

SHORT CONVERSATION NOTE:
If the conversation is very short (only 1-2 exchanges), produce a LIGHTWEIGHT structure:
- Prefer 'assumption_surface' when the user makes claims or states a direction (extract what they're taking as given)
- Prefer 'angle_map' when the user asks an open question or explores a topic (map the dimensions in play)
- Keep established facts minimal (only what's truly confirmed)
- Focus open_questions on what the user might want to explore next
- The context_summary should capture the user's apparent intent and direction
- It's fine to have sparse content — the structure will evolve as conversation continues

IMPORTANT: assumption_surface and angle_map are ANNOTATION types — they extract structure from
what was ALREADY SAID in the conversation (by both user and assistant). They do NOT generate
new ideas. The only generative element allowed is noting gaps: angles marked 'not_yet_discussed'
or implicit assumptions the user hasn't articulated. Everything else must trace back to the conversation.

FIRST-SESSION GUIDANCE:
If USER CONTEXT shows a first-time user (first thread, no projects/documents/cases):
- Your context_summary should briefly orient the user to how Episteme helps structure thinking
- In open_questions, include suggestive questions about what they might explore next
  (e.g., "Would a project workspace help organize research around this?")
- Frame the structure to teach by example — show how the companion tracks reasoning
- Mention unused capabilities (projects for document analysis, cases for rigorous decisions)
  when naturally relevant to what they're discussing
- Keep nudges subtle — this is a companion, not a tutorial
If the user has projects but no cases, mention cases when a decision emerges.
If the user has documents, note that the AI can reference their uploaded research.

STRUCTURE SCHEMAS (use the schema for your chosen type):
{schema_text}

This is a new structure — create from scratch based on the conversation so far.

Return ONLY valid JSON in this exact format:
{{
  "structure_type": "one of the types listed above",
  "content": {{ ... structure matching the chosen type's schema ... }},
  "established": ["fact 1", "fact 2"],
  "open_questions": ["question 1", "question 2"],
  "eliminated": ["option X (reason)", "option Y (reason)"],
  "context_summary": "Compact summary for chat context injection...",
  "topic_continuity": "initial",
  "topic_label": "Brief topic label (3-5 words)"
}}"""


def build_case_detection_prompt(
    structure_content: dict,
    structure_type: str,
    established: list,
    open_questions: list,
    eliminated: list,
) -> str:
    """
    Build prompt to detect whether the conversation has reached a 'decision shape'.
    """
    return f"""Analyze this conversation structure and determine if it has reached a point
where the user should consider opening a formal decision case.

STRUCTURE TYPE: {structure_type}
CONTENT: {json.dumps(structure_content, indent=2)}

ESTABLISHED FACTS: {json.dumps(established)}
OPEN QUESTIONS: {json.dumps(open_questions)}
ELIMINATED OPTIONS: {json.dumps(eliminated)}

A conversation is ready for a case when:
- There's a clear decision question emerging (not just exploration)
- Multiple viable options exist (at least 2)
- There are enough constraints to scope the decision
- There are open questions that need structured investigation

Determine:
1. Should we suggest opening a case? (true/false)
2. If yes, what's the decision question? (concise, under 60 chars)
3. What title would the case have? (concise, under 50 chars)
4. Why should the user structure this as a case? (1 sentence)

Return ONLY valid JSON:
{{
  "should_suggest": true/false,
  "decision_question": "...",
  "title": "...",
  "reason": "..."
}}"""


def build_research_detection_prompt(open_questions: list) -> str:
    """
    Classify which open questions are factual and researchable vs. opinion/decision questions.
    """
    questions_text = "\n".join([f"- {q}" for q in open_questions])

    return f"""Classify these open questions from a conversation:

{questions_text}

For each question, determine:
1. Is it RESEARCHABLE? (factual question that can be answered by searching documentation, articles, or data)
   - YES: "Does Sigma support RLS?", "What is the PostgreSQL max connections default?"
   - NO: "Should we use write-back?", "Is our performance acceptable?", "Which approach is better for our team?"
2. If researchable, what search query would find the answer?
3. Priority: high (blocking the conversation) | medium (useful context) | low (nice to know)

Return ONLY valid JSON:
{{
  "researchable": [
    {{"question": "...", "search_query": "...", "priority": "high|medium|low"}}
  ],
  "not_researchable": ["question 1", "question 2"]
}}"""
