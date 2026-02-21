"""
Extraction prompts for case-level, objective-driven extraction.

Key difference from project-level extraction (graph/extraction.py):
The decision question is front and center — every node is extracted
through the lens of the specific decision being investigated.
"""
from typing import Optional


def build_case_extraction_system_prompt(case) -> str:
    """Build the system prompt for case-level extraction.

    Includes the decision question, position, and constraints as
    context so the LLM focuses extraction on what matters for the decision.
    """
    constraints_text = ""
    if case.constraints:
        constraints_text = "\n".join(
            f"- {c.get('description', c) if isinstance(c, dict) else c}"
            for c in case.constraints
        )

    position_text = case.position or "(No position established yet)"

    return f"""You are an expert analyst extracting structured reasoning from source documents to help make a specific decision.

DECISION CONTEXT:
Decision question: {case.decision_question or '(Not specified)'}

Current position: {position_text}

Known constraints:
{constraints_text or '(None specified)'}

YOUR TASK:
Extract Claims, Evidence, Assumptions, and Tensions from the source material that are RELEVANT to this decision. Do not extract everything — only what helps reason about the decision.

NODE TYPES:
- CLAIM: An assertion relevant to the decision. Must be specific and falsifiable.
  Example: "Schema-per-tenant provides stronger data isolation"
- EVIDENCE: A fact, data point, or observation that supports or contradicts claims.
  Example: "PostgreSQL RLS adds ~3ms overhead per query (benchmarked on 10K rows)"
- ASSUMPTION: Something being taken as true but not verified. CRITICAL for decisions.
  Example: "We assume query volume will stay under 1000/minute"
- TENSION: A contradiction or conflict between sources relevant to the decision.
  Example: "Source A recommends RLS for simplicity, but Source B warns about RLS performance at scale"

EDGES:
- SUPPORTS: Evidence/reasoning that favors the target node
- CONTRADICTS: Evidence/reasoning that opposes the target node
- DEPENDS_ON: Source node requires target node to hold true

EXTRACTION FOCUS:
- Extract nodes that MATTER for the decision — skip background/boilerplate
- Prioritize TENSIONS between sources — these are decision-critical
- Identify ASSUMPTIONS that could change the decision if wrong
- Flag EVIDENCE that constrains the answer
- Claims should be scoped to the decision, not general statements

QUALITY REQUIREMENTS:
1. Each node's content must be STANDALONE — readable without the source
2. Content must be SUBSTANTIVE — no vague statements
3. SPECIFICITY IS MANDATORY — claims must be falsifiable
4. importance=3: Directly addresses the decision question (max 2-3)
5. importance=2: Supports or constrains the decision
6. importance=1: Background context relevant to the decision
7. Include source_passage for provenance tracking
8. Be CONSERVATIVE — quality over quantity. Fewer, better nodes.

Document role describes the FUNCTION within the decision's reasoning:
- thesis: A central argument about the decision
- supporting_claim: A claim that supports or opposes the decision
- supporting_evidence: Evidence cited for or against
- foundational_assumption: An assumption the decision depends on
- counterpoint: A counter-argument relevant to the decision
- background: Context for understanding the decision space
- detail: Minor but relevant detail"""


def build_case_extraction_user_prompt(
    case,
    chunks_by_doc: dict,
    companion_state: Optional[dict] = None,
) -> str:
    """Build the user prompt with formatted chunks and companion context.

    Args:
        case: Case instance
        chunks_by_doc: Dict mapping document title to list of chunk dicts
            Each chunk dict has: chunk_text, chunk_index, document_title
        companion_state: Optional companion-originated context with
            established facts, open questions, etc.
    """
    # Format chunks grouped by document
    source_parts = []
    for doc_title, chunks in chunks_by_doc.items():
        source_parts.append(f"### Source: {doc_title}")
        for chunk in chunks:
            source_parts.append(f"[Chunk {chunk['chunk_index']}]")
            source_parts.append(chunk['chunk_text'])
            source_parts.append("")

    formatted_chunks = "\n".join(source_parts)

    # Format companion context if available
    companion_text = ""
    if companion_state:
        companion_parts = []
        if companion_state.get('established'):
            companion_parts.append("ESTABLISHED FACTS (from prior conversation):")
            for fact in companion_state['established']:
                companion_parts.append(f"- {fact}")
        if companion_state.get('open_questions'):
            companion_parts.append("\nOPEN QUESTIONS:")
            for q in companion_state['open_questions']:
                companion_parts.append(f"- {q}")
        if companion_state.get('eliminated'):
            companion_parts.append("\nELIMINATED OPTIONS:")
            for e in companion_state['eliminated']:
                companion_parts.append(f"- {e}")
        companion_text = "\n".join(companion_parts)

    prompt = f"""SOURCE MATERIAL:

{formatted_chunks}
"""

    if companion_text:
        prompt += f"""
PRIOR CONVERSATION CONTEXT:
{companion_text}

"""

    prompt += f"""Extract the reasoning structure from these sources relevant to the decision:
"{case.decision_question}"

Return nodes and edges using the extraction tool."""

    return prompt


def build_incremental_extraction_system_prompt(case, existing_node_summaries: str) -> str:
    """Build system prompt for incremental extraction (Phase 6).

    Includes existing node summaries so the LLM avoids duplicating
    already-extracted nodes and instead focuses on new information
    and connections to existing nodes.
    """
    base_prompt = build_case_extraction_system_prompt(case)

    return base_prompt + f"""

INCREMENTAL EXTRACTION:
The case already has extracted nodes. Do NOT duplicate existing nodes.
Instead:
1. Extract NEW nodes from the new source material only
2. Create edges between new nodes AND between new and existing nodes
3. If new evidence supports/contradicts an existing node, create an edge

EXISTING NODES IN THE CASE:
{existing_node_summaries}

Use the existing node IDs (e.g., "existing-<uuid>") as edge source/targets
when creating edges to existing nodes. For new nodes, use temporary IDs
(n0, n1, ...)."""
