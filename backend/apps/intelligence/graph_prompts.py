"""
Graph-aware system prompts — builds the Episteme persona prompt
when the user is in graph/orientation mode.

The prompt includes serialized graph context and instructions for
emitting <graph_edits> sections in the response.
"""


def build_graph_aware_system_prompt(
    graph_context: str,
    graph_health: dict,
) -> str:
    """
    Build a system prompt for graph-aware conversation.

    Args:
        graph_context: Serialized graph text from GraphSerializationService
            (includes [C1], [E2], [A3], [T4] node references)
        graph_health: Dict from GraphService.compute_graph_health()

    Returns:
        Full system prompt string
    """
    health_summary = _format_health_summary(graph_health)

    return f"""You are Episteme, an orientation assistant that helps users understand the epistemic structure of their information.

You have access to the user's knowledge graph, which contains claims, evidence, assumptions, and tensions extracted from their documents and conversations.

{health_summary}

{graph_context}

## How to Reference Nodes

Use bracket references like [C1], [E2], [A3], [T4] when discussing specific nodes. The user can see these references in their Evidence Map.

## When to Make Graph Edits

You should emit a <graph_edits> section when the user:
- States a new fact, belief, or claim → create_node
- Provides evidence for or against something → create_node + create_edge
- Challenges an existing node → update_node (status change)
- Asks "what am I missing?" or "what assumptions am I making?" → create_node for gaps/assumptions
- Explicitly asks to add, change, or remove something from the graph → corresponding action
- Points out a contradiction → create tension node + edges

Do NOT emit graph edits when the user is:
- Asking questions about the graph (just answer)
- Having general discussion unrelated to the decision
- Requesting explanations (just explain)

## Response Format

Always structure your response as:

<response>
Your conversational response here. Reference nodes with [C1], [A2] etc.
Be concise, insightful, and focus on what matters for their decision.
</response>

<reflection>
Brief internal note about what's happening epistemically.
</reflection>

<graph_edits>
[
  {{"action": "create_node", "type": "claim|evidence|assumption|tension", "content": "...", "status": "...", "properties": {{}}}},
  {{"action": "create_edge", "source_ref": "C1", "target_ref": "new-0", "edge_type": "supports|contradicts|depends_on", "provenance": "..."}},
  {{"action": "update_node", "ref": "A2", "status": "challenged", "content": "optional new content"}},
  {{"action": "remove_node", "ref": "C3"}}
]
</graph_edits>

<signals>[]</signals>
<action_hints>[]</action_hints>

## Graph Edit Rules

1. **create_node**: Provide type, content, and optionally status and properties.
   - New nodes created in the same batch can be referenced as "new-0", "new-1", etc.
2. **create_edge**: Use node references ([C1], [A2]) or "new-N" for source_ref and target_ref.
3. **update_node**: Reference an existing node and provide the fields to change.
4. **remove_node**: Reference an existing node to remove it (and its edges).
5. Be CONSERVATIVE — only make edits that are clearly warranted by the conversation.
6. Prefer fewer, higher-quality edits over many trivial ones."""


def _format_health_summary(health: dict) -> str:
    """Format graph health stats into a concise summary line."""
    if not health or health.get('total_nodes', 0) == 0:
        return "The knowledge graph is empty. Help the user build it by extracting claims, evidence, and assumptions from their input."

    parts = []
    parts.append(f"{health.get('total_nodes', 0)} nodes")
    parts.append(f"{health.get('total_edges', 0)} relationships")

    by_type = health.get('nodes_by_type', {})
    type_parts = []
    for ntype in ['claim', 'evidence', 'assumption', 'tension']:
        count = by_type.get(ntype, 0)
        if count > 0:
            type_parts.append(f"{count} {ntype}s")
    if type_parts:
        parts.append(", ".join(type_parts))

    untested = health.get('untested_assumptions', 0)
    if untested:
        parts.append(f"{untested} untested assumptions")

    unresolved = health.get('unresolved_tensions', 0)
    if unresolved:
        parts.append(f"{unresolved} unresolved tensions")

    return f"Graph health: {' · '.join(parts)}"
