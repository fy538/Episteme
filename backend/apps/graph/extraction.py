"""
Phase A: Extract nodes and intra-document edges from a document.

Sends the full document text to the LLM to extract the argument structure:
nodes (claims, evidence, assumptions, tensions) with importance scoring and
document roles, plus intra-document edges (supports, contradicts, depends_on).

For long documents exceeding LLM context, falls back to section-based
extraction with deduplication and consolidation.

Uses the same LLM provider factory as the rest of the codebase.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import tiktoken
from asgiref.sync import async_to_sync

from apps.common.utils import parse_json_from_response

from apps.common.vector_utils import (
    generate_embedding,
    generate_embeddings_batch,
    similarity_search,
)
from apps.projects.models import Document, DocumentChunk

from .embedding_state import mark_embedding_failed, clear_embedding_failure
from .models import (
    NodeType, NodeStatus, EdgeType,
    VALID_STATUSES_BY_TYPE, DEFAULT_STATUS_BY_TYPE,
)
from .services import GraphService

logger = logging.getLogger(__name__)

# Token counting for context-window decisions
_enc = tiktoken.get_encoding('cl100k_base')

# Reserve for prompt overhead + response tokens when computing extraction limit
_EXTRACTION_OVERHEAD_TOKENS = 16_000


def _get_max_extraction_tokens() -> int:
    """Max document tokens before switching to section-based extraction.

    Dynamic based on the extraction provider's context window.
    Reserves 16K tokens for prompt overhead + response.
    """
    from apps.common.llm_providers import get_llm_provider
    provider = get_llm_provider('extraction')
    return provider.context_window_tokens - _EXTRACTION_OVERHEAD_TOKENS

# Section overlap in tokens for long-document splitting
SECTION_OVERLAP_TOKENS = 200

# Extraction targets per document (from V1 spec)
TARGET_CLAIMS = (3, 7)
TARGET_EVIDENCE = (2, 5)
TARGET_ASSUMPTIONS = (1, 3)

# Minimum content length to attempt extraction
MIN_DOCUMENT_LENGTH = 50

# Tool schema for structured extraction output (used by tool_use / function calling)
EXTRACTION_TOOL = {
    "name": "extract_argument_structure",
    "description": "Extract nodes and edges from document text as a knowledge graph",
    "input_schema": {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Temporary ID (n0, n1, ...)"},
                        "type": {"type": "string", "enum": ["claim", "evidence", "assumption", "tension"]},
                        "content": {"type": "string", "description": "Clear standalone statement"},
                        "importance": {"type": "integer", "minimum": 1, "maximum": 3},
                        "document_role": {
                            "type": "string",
                            "enum": ["thesis", "supporting_claim", "supporting_evidence",
                                     "foundational_assumption", "counterpoint", "background", "detail"],
                        },
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "source_passage": {"type": "string"},
                        "properties": {"type": "object"},
                    },
                    "required": ["id", "type", "content"],
                },
            },
            "edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_id": {"type": "string"},
                        "target_id": {"type": "string"},
                        "edge_type": {"type": "string", "enum": ["supports", "contradicts", "depends_on"]},
                    },
                    "required": ["source_id", "target_id", "edge_type"],
                },
            },
        },
        "required": ["nodes", "edges"],
    },
}

# Valid document roles
VALID_DOCUMENT_ROLES = {
    'thesis', 'supporting_claim', 'supporting_evidence',
    'foundational_assumption', 'counterpoint', 'background', 'detail',
}

# Valid intra-document edge types
VALID_EDGE_TYPES = {'supports', 'contradicts', 'depends_on'}


def extract_nodes_from_document(
    document_id,
    project_id,
    *,
    created_by=None,
) -> List:
    """
    Phase A entry point: extract nodes and intra-document edges from a document.

    Sends full document text to the LLM for argument structure extraction.
    For long documents, uses section-based extraction with deduplication.

    Returns list of created Node IDs.
    """
    from apps.projects.models import Document, Project

    document = Document.objects.get(id=document_id)
    project = Project.objects.get(id=project_id)

    # Derive case scope from document
    case = document.case if document.scope == 'case' else None

    if not document.content_text or len(document.content_text.strip()) < MIN_DOCUMENT_LENGTH:
        logger.info("Document too short for extraction: %s", document_id)
        return []

    # Extract nodes and edges from full document
    result = _extract_from_full_document(document)
    if not result or not result.get('nodes'):
        logger.info("No nodes extracted from document %s", document_id)
        return []

    # Get all chunks for provenance mapping
    chunks = list(
        DocumentChunk.objects.filter(document=document)
        .order_by('chunk_index')
    )

    # Create nodes without embeddings first, then batch-generate
    temp_id_to_node = {}
    created_node_ids = []
    created_nodes = []      # (node, item) pairs for embedding reuse
    cached_embeddings = {}  # node index -> embedding (from dedup)

    for item in result.get('nodes', []):
        try:
            # Merge importance and document_role into properties
            properties = item.get('properties', {})
            properties['importance'] = item.get('importance', 2)
            properties['document_role'] = item.get('document_role', 'detail')

            node = GraphService.create_node(
                project=project,
                node_type=item['type'],
                content=item['content'],
                source_type='document_extraction',
                status=item.get('status'),
                properties=properties,
                case=case,
                source_document=document,
                confidence=item.get('confidence', 0.8),
                created_by=created_by,
                generate_embed=False,  # Defer — batch below
            )

            # Link source chunks via text match (embedding fallback deferred)
            chunk_ids = _match_source_chunks(item, chunks)
            if chunk_ids:
                node.source_chunks.set(
                    DocumentChunk.objects.filter(id__in=chunk_ids)
                )

            temp_id = item.get('id', '')
            if temp_id:
                temp_id_to_node[temp_id] = node

            created_node_ids.append(node.id)

            # Track cached embedding from dedup (if available)
            idx = len(created_nodes)
            if item.get('_embedding'):
                cached_embeddings[idx] = item['_embedding']
            created_nodes.append(node)

        except Exception:
            logger.exception(
                "Failed to create node from extraction",
                extra={'document_id': str(document_id)},
            )

    # Overlap embedding generation with edge creation using concurrent futures
    from concurrent.futures import ThreadPoolExecutor, as_completed

    edges_created = 0

    def _generate_and_apply_embeddings():
        """Batch-generate embeddings (reuse cached from dedup when available)."""
        if not created_nodes:
            return
        try:
            from .models import Node

            needs_embedding = []
            failed_node_ids = []
            for i, node in enumerate(created_nodes):
                if i in cached_embeddings:
                    cached = cached_embeddings[i]
                    if cached is not None:
                        node.embedding = cached
                        node.properties = clear_embedding_failure(node.properties)
                    else:
                        node.embedding = None
                        node.properties = mark_embedding_failed(
                            node.properties, "cached_embedding_missing",
                        )
                        failed_node_ids.append(str(node.id))
                else:
                    needs_embedding.append(node)

            if needs_embedding:
                contents = [n.content for n in needs_embedding]
                new_embeddings = generate_embeddings_batch(contents)

                if len(new_embeddings) != len(needs_embedding):
                    logger.warning(
                        "Batch embedding result size mismatch",
                        extra={
                            'document_id': str(document_id),
                            'expected': len(needs_embedding),
                            'actual': len(new_embeddings),
                        },
                    )
                    new_embeddings = (
                        list(new_embeddings[:len(needs_embedding)])
                        + [None] * max(0, len(needs_embedding) - len(new_embeddings))
                    )

                for node, emb in zip(needs_embedding, new_embeddings):
                    if emb is not None:
                        node.embedding = emb
                        node.properties = clear_embedding_failure(node.properties)
                    else:
                        node.embedding = None
                        node.properties = mark_embedding_failed(
                            node.properties, "batch_embedding_missing",
                        )
                        failed_node_ids.append(str(node.id))

            if failed_node_ids:
                logger.warning(
                    "Some nodes were created without embeddings",
                    extra={
                        'document_id': str(document_id),
                        'failed_count': len(failed_node_ids),
                        'failed_node_ids': failed_node_ids[:10],
                    },
                )

            Node.objects.bulk_update(created_nodes, ['embedding', 'properties'])
        except Exception:
            logger.warning(
                "Batch embedding generation failed for nodes",
                exc_info=True,
                extra={'document_id': str(document_id)},
            )

    def _create_edges():
        """Create intra-document edges."""
        count = 0
        for edge_spec in result.get('edges', []):
            try:
                valid_edge = _validate_extraction_edge(edge_spec)
                if not valid_edge:
                    continue

                source_node = temp_id_to_node.get(valid_edge['source_id'])
                target_node = temp_id_to_node.get(valid_edge['target_id'])
                if source_node and target_node:
                    GraphService.create_edge(
                        source_node=source_node,
                        target_node=target_node,
                        edge_type=valid_edge['edge_type'],
                        source_type='document_extraction',
                        source_document=document,
                        provenance=valid_edge.get('provenance', ''),
                        created_by=created_by,
                    )
                    count += 1
            except Exception:
                logger.exception(
                    "Failed to create intra-document edge",
                    extra={'document_id': str(document_id)},
                )
        return count

    # Run embedding generation and edge creation in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        embed_future = executor.submit(_generate_and_apply_embeddings)
        edge_future = executor.submit(_create_edges)

        embed_future.result()  # wait for embeddings
        edges_created = edge_future.result()  # wait for edges

    logger.info(
        "extraction_phase_a_complete",
        extra={
            'document_id': str(document_id),
            'nodes_created': len(created_node_ids),
            'edges_created': edges_created,
        },
    )

    return created_node_ids


# ═══════════════════════════════════════════════════════════════════
# Full-document extraction
# ═══════════════════════════════════════════════════════════════════

def _extract_from_full_document(document: Document) -> Dict[str, Any]:
    """
    Extract nodes and edges from a document.

    Short documents: single LLM call with full text.
    Long documents (exceeding provider context): section-based extraction + deduplication.

    Returns:
        {'nodes': [...], 'edges': [...]}
    """
    text = document.content_text
    token_count = len(_enc.encode(text))
    max_tokens = _get_max_extraction_tokens()

    if token_count <= max_tokens:
        return _call_extraction_llm(document.title, text)
    else:
        logger.info(
            "Document exceeds single-call limit, using section-based extraction",
            extra={
                'document_id': str(document.id),
                'token_count': token_count,
            },
        )
        return _extract_long_document(document, token_count)


def _call_extraction_llm(document_title: str, document_text: str) -> Dict[str, Any]:
    """
    Single LLM call to extract argument structure from document text.

    Uses tool_use / function calling for schema-enforced structured output.
    Falls back to text + JSON parsing for providers that don't support tools.

    Returns:
        {'nodes': [...], 'edges': [...]}
    """
    prompt = _build_extraction_prompt(document_title, document_text)

    from apps.common.llm_providers import get_llm_provider
    provider = get_llm_provider('extraction')

    async def _call():
        return await provider.generate_with_tools(
            messages=[{"role": "user", "content": prompt}],
            tools=[EXTRACTION_TOOL],
            system_prompt=_EXTRACTION_SYSTEM_PROMPT,
            max_tokens=8192,
            temperature=0.2,
        )

    parsed = async_to_sync(_call)()

    if not parsed:
        return {'nodes': [], 'edges': []}

    return _normalize_extraction_result(parsed)


def _normalize_extraction_result(parsed: Any) -> Dict[str, Any]:
    """Normalize parsed LLM output into {'nodes': [...], 'edges': [...]} format."""
    nodes_raw = []
    edges_raw = []

    if isinstance(parsed, dict):
        nodes_raw = parsed.get('nodes', parsed.get('extractions', []))
        edges_raw = parsed.get('edges', [])
    elif isinstance(parsed, list):
        nodes_raw = parsed

    if not isinstance(nodes_raw, list):
        logger.warning("Unexpected extraction format: %s", type(nodes_raw))
        return {'nodes': [], 'edges': []}

    if not isinstance(edges_raw, list):
        edges_raw = []

    # Validate nodes
    validated_nodes = []
    for item in nodes_raw:
        valid = _validate_extraction_item(item)
        if valid:
            validated_nodes.append(valid)

    return {'nodes': validated_nodes, 'edges': edges_raw}


# ═══════════════════════════════════════════════════════════════════
# Long-document extraction (two-pass)
# ═══════════════════════════════════════════════════════════════════

def _extract_long_document(
    document: Document,
    token_count: int,
) -> Dict[str, Any]:
    """
    Two-pass extraction for documents exceeding provider context window.

    Pass 1: Generate document summary, then extract all sections in parallel.
    Pass 2: Deduplicate nodes across sections via embedding similarity,
            then consolidate with a final LLM call.
    """
    import asyncio

    async def _run():
        text = document.content_text
        max_tokens = _get_max_extraction_tokens()

        # Run summary generation and section splitting in parallel
        # (summary is async LLM call, splitting is CPU — no dependency)
        import asyncio as _aio

        summary_task = _aio.create_task(_generate_summary_async(document.title, text))
        sections = _split_into_sections(text, max_tokens)
        summary = await summary_task

        # Pass 1: Extract from ALL sections in parallel
        tasks = [
            _extract_section_async(
                document_title=document.title,
                section_text=section_text,
                section_index=i,
                total_sections=len(sections),
                document_summary=summary,
            )
            for i, section_text in enumerate(sections)
        ]
        section_results = await asyncio.gather(*tasks, return_exceptions=True)

        all_nodes = []
        all_edges = []

        for i, result in enumerate(section_results):
            if isinstance(result, Exception):
                logger.exception(
                    "Parallel section extraction failed",
                    exc_info=result,
                    extra={'section_index': i},
                )
                continue

            # Tag nodes with section index for edge resolution
            for node in result.get('nodes', []):
                node['_section'] = i
                if node.get('id'):
                    node['id'] = f"s{i}_{node['id']}"

            for edge in result.get('edges', []):
                if edge.get('source_id'):
                    edge['source_id'] = f"s{i}_{edge['source_id']}"
                if edge.get('target_id'):
                    edge['target_id'] = f"s{i}_{edge['target_id']}"

            all_nodes.extend(result.get('nodes', []))
            all_edges.extend(result.get('edges', []))

        if not all_nodes:
            return {'nodes': [], 'edges': []}

        # Pass 2: Deduplicate
        deduped_nodes, id_remap = _deduplicate_nodes(all_nodes)

        # Remap edge IDs after deduplication
        remapped_edges = []
        for edge in all_edges:
            src = id_remap.get(edge.get('source_id', ''), edge.get('source_id', ''))
            tgt = id_remap.get(edge.get('target_id', ''), edge.get('target_id', ''))
            remapped_edges.append({**edge, 'source_id': src, 'target_id': tgt})

        # Consolidation pass (only if >2 sections)
        if len(sections) > 2:
            return _consolidate_sections(
                document.title, deduped_nodes, remapped_edges, summary,
            )

        return {'nodes': deduped_nodes, 'edges': remapped_edges}

    return async_to_sync(_run)()


async def _generate_summary_async(title: str, text: str) -> str:
    """Generate a brief document summary via Haiku for section extraction context."""
    from apps.common.llm_providers import get_llm_provider
    provider = get_llm_provider('fast')

    truncated = text[:32000]

    try:
        return await provider.generate(
            messages=[{"role": "user", "content": (
                f'Summarize the document "{title}" in 3-4 sentences. '
                f'Focus on the main thesis, key arguments, and conclusions.\n\n'
                f'DOCUMENT TEXT:\n{truncated}'
            )}],
            system_prompt="You are a document summarizer. Be concise and specific.",
            max_tokens=256,
            temperature=0.2,
        )
    except Exception:
        logger.warning("Failed to generate document summary", exc_info=True)
        return ""


def _split_into_sections(text: str, max_tokens: int) -> List[str]:
    """
    Split document text into sections that fit within max_tokens.

    Strategy: split on double-newlines (paragraph boundaries) first,
    then fall back to token-window splitting with overlap.
    """
    tokens = _enc.encode(text)
    if len(tokens) <= max_tokens:
        return [text]

    # Try splitting on headings/double-newlines
    paragraphs = re.split(r'\n\n+', text)
    sections = []
    current_section = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = len(_enc.encode(para))
        if current_tokens + para_tokens > max_tokens and current_section:
            sections.append('\n\n'.join(current_section))
            current_section = []
            current_tokens = 0
        current_section.append(para)
        current_tokens += para_tokens

    if current_section:
        sections.append('\n\n'.join(current_section))

    return sections if sections else [text]


async def _extract_section_async(
    document_title: str,
    section_text: str,
    section_index: int,
    total_sections: int,
    document_summary: str,
) -> Dict[str, Any]:
    """Extract nodes and edges from a single section (natively async for parallel use)."""
    from apps.common.llm_providers import get_llm_provider
    provider = get_llm_provider('extraction')

    prompt = (
        f'You are extracting from SECTION {section_index + 1} of {total_sections} '
        f'of the document "{document_title}".\n\n'
        f'DOCUMENT SUMMARY (for context):\n{document_summary}\n\n'
        f'SECTION TEXT:\n{section_text}\n\n'
        f'Extract the argument structure of THIS SECTION following the instructions '
        f'in the system prompt.'
    )

    try:
        parsed = await provider.generate_with_tools(
            messages=[{"role": "user", "content": prompt}],
            tools=[EXTRACTION_TOOL],
            system_prompt=_EXTRACTION_SYSTEM_PROMPT,
            max_tokens=8192,
            temperature=0.2,
        )
        if parsed:
            return _normalize_extraction_result(parsed)
    except Exception:
        logger.exception(
            "Section extraction failed",
            extra={'section_index': section_index},
        )

    return {'nodes': [], 'edges': []}


def _deduplicate_nodes(
    nodes: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Deduplicate nodes across sections using embedding similarity.

    Nodes with content cosine similarity > 0.90 are considered duplicates.
    Keeps the node with higher importance, or longer content as tiebreaker.

    Returns:
        (deduplicated_nodes, id_remap) where id_remap maps removed IDs to surviving IDs.
    """
    if len(nodes) <= 1:
        return nodes, {}

    # Generate embeddings for all node contents
    contents = [n['content'] for n in nodes]
    try:
        embeddings = generate_embeddings_batch(contents)
    except Exception:
        logger.warning("Failed to generate embeddings for dedup, skipping", exc_info=True)
        return nodes, {}

    if any(emb is None for emb in embeddings):
        logger.warning(
            "Dedup embeddings incomplete, skipping dedup",
            extra={'missing_embeddings': sum(1 for emb in embeddings if emb is None)},
        )
        return nodes, {}

    import numpy as np
    emb_array = np.array(embeddings)

    # Compute pairwise cosine similarities
    norms = np.linalg.norm(emb_array, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normalized = emb_array / norms
    sim_matrix = normalized @ normalized.T

    # Find duplicate pairs (similarity > 0.90)
    merged_into = {}  # index -> surviving index
    for i in range(len(nodes)):
        if i in merged_into:
            continue
        for j in range(i + 1, len(nodes)):
            if j in merged_into:
                continue
            if sim_matrix[i][j] > 0.90:
                # Keep the one with higher importance, then longer content
                imp_i = nodes[i].get('importance', 2)
                imp_j = nodes[j].get('importance', 2)
                if imp_j > imp_i or (imp_j == imp_i and len(nodes[j]['content']) > len(nodes[i]['content'])):
                    merged_into[i] = j
                    break
                else:
                    merged_into[j] = i

    # Build deduplicated list and remap, caching embeddings on survivors
    id_remap = {}
    deduped = []
    for i, node in enumerate(nodes):
        if i in merged_into:
            surviving_idx = merged_into[i]
            removed_id = node.get('id', '')
            surviving_id = nodes[surviving_idx].get('id', '')
            if removed_id and surviving_id:
                id_remap[removed_id] = surviving_id
        else:
            # Cache embedding so extract_nodes_from_document can reuse it
            node['_embedding'] = embeddings[i]
            deduped.append(node)

    if merged_into:
        logger.info(
            "Deduplicated %d nodes (removed %d duplicates)",
            len(nodes), len(merged_into),
        )

    return deduped, id_remap


def _consolidate_sections(
    document_title: str,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    summary: str,
) -> Dict[str, Any]:
    """
    Consolidation pass for multi-section extraction.

    Receives all deduplicated nodes and asks the LLM to:
    1. Assign a document-wide thesis (importance=3)
    2. Create cross-section edges
    3. Detect cross-section tensions
    """
    from apps.common.llm_providers import get_llm_provider
    provider = get_llm_provider('extraction')

    # Compact node list for context
    node_list = "\n".join(
        f"[{n.get('id', '?')}] ({n.get('type', '?')}) imp={n.get('importance', 2)} "
        f"role={n.get('document_role', 'detail')}: {n['content']}"
        for n in nodes
    )

    prompt = f"""You are consolidating the extraction of a multi-section document.

DOCUMENT: "{document_title}"
SUMMARY: {summary}

EXTRACTED NODES:
{node_list}

EXISTING EDGES:
{json.dumps(edges, default=str)[:2000]}

Your tasks:
1. Identify which node best represents the document's THESIS. Set its importance to 3 and document_role to "thesis". Maximum 1-2 thesis nodes.
2. Create any CROSS-SECTION edges that the per-section extraction missed (e.g., evidence from section 1 supporting a claim in section 3).
3. Detect any CROSS-SECTION tensions (contradictions between different sections).

Output JSON:
{{
  "importance_updates": [{{"id": "node_id", "importance": 3, "document_role": "thesis"}}],
  "new_edges": [{{"source_id": "...", "target_id": "...", "edge_type": "supports|contradicts|depends_on"}}],
  "new_tension_nodes": [{{"content": "...", "between_ids": ["id1", "id2"]}}]
}}"""

    async def _call():
        response = await provider.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a document analysis expert. Output valid JSON only.",
            max_tokens=4096,
            temperature=0.2,
        )
        return response

    try:
        response_text = async_to_sync(_call)()
        parsed = parse_json_from_response(response_text)
        if parsed and isinstance(parsed, dict):
            # Apply importance updates
            updates_by_id = {
                u['id']: u for u in parsed.get('importance_updates', [])
                if isinstance(u, dict) and 'id' in u
            }
            for node in nodes:
                node_id = node.get('id', '')
                if node_id in updates_by_id:
                    update = updates_by_id[node_id]
                    node['importance'] = update.get('importance', node.get('importance', 2))
                    node['document_role'] = update.get('document_role', node.get('document_role', 'detail'))

            # Add new edges
            new_edges = parsed.get('new_edges', [])
            if isinstance(new_edges, list):
                edges.extend(new_edges)

            # Add tension nodes
            for tension in parsed.get('new_tension_nodes', []):
                if isinstance(tension, dict) and tension.get('content'):
                    nodes.append({
                        'id': f"consolidation_t{len(nodes)}",
                        'type': 'tension',
                        'content': tension['content'],
                        'importance': 2,
                        'document_role': 'counterpoint',
                        'confidence': 0.7,
                        'source_passage': '',
                        'properties': {
                            'tension_type': 'cross_section',
                            'between_nodes': tension.get('between_ids', []),
                        },
                    })

    except Exception:
        logger.warning("Consolidation pass failed, using section results", exc_info=True)

    return {'nodes': nodes, 'edges': edges}


# ═══════════════════════════════════════════════════════════════════
# Prompt construction
# ═══════════════════════════════════════════════════════════════════

def _build_extraction_prompt(document_title: str, document_text: str) -> str:
    """Build the user prompt for full-document extraction."""
    return f"""Analyze the document "{document_title}" and extract its argument structure as a knowledge graph.

DOCUMENT TEXT:
{document_text}

## Step 1: Identify the argument structure
What is the document's main thesis? What claims support it? What evidence is cited? What is assumed without proof?

## Step 2: Extract nodes
For each node provide:
- `id`: temporary identifier (n0, n1, n2...)
- `type`: one of "claim", "evidence", "assumption"
- `content`: clear, standalone statement (1-2 sentences)
- `importance`: 3 (core thesis, max 1-2 per doc), 2 (supporting), or 1 (peripheral detail)
- `document_role`: one of "thesis", "supporting_claim", "supporting_evidence", "foundational_assumption", "counterpoint", "background", "detail"
- `confidence`: 0.0-1.0 confidence in this extraction
- `source_passage`: exact quote from the document for provenance
- `properties`: type-specific metadata object

Properties by type:
- Claims: {{"source_context": "brief context", "specificity": "high"|"medium"|"low"}}
- Evidence: {{"credibility": "high"|"medium"|"low", "evidence_type": "metric"|"observation"|"quote"|"benchmark"}}
- Assumptions: {{"load_bearing": true|false, "implicit": true|false, "scope": "narrow"|"broad"}}

## Step 3: Identify intra-document relationships
Create edges between nodes:
- evidence --supports--> claim
- claim --depends_on--> assumption
- subclaim --supports--> thesis
- If the document contradicts itself, use --contradicts-->

For each edge provide:
- `source_id`: the node id of the source (e.g., "n0")
- `target_id`: the node id of the target (e.g., "n1")
- `edge_type`: one of "supports", "contradicts", "depends_on"

## Step 4: Flag intra-document tensions
If the document contradicts itself (e.g., inconsistent numbers, claims unsupported by its own evidence), create a tension node with type "tension" and edges linking the contradicting nodes.

Output a JSON object: {{"nodes": [...], "edges": [...]}}"""


_EXTRACTION_SYSTEM_PROMPT = """You are an epistemic analyst extracting the argument structure of documents as knowledge graphs.

Rules:
1. Extract SUBSTANTIVE nodes only — skip boilerplate, generic statements, and obvious facts.
2. Each claim must be a specific, falsifiable assertion. SPECIFICITY IS MANDATORY.
   BAD:  "The market is growing"
   GOOD: "Document claims TAM will reach $4.2B by 2027 citing Gartner research"
3. Each evidence item must be a concrete, verifiable fact that could support or contradict claims.
4. Each assumption must be a belief the document takes for granted without defending.
5. Make content STANDALONE — a reader should understand the node without seeing the source.
6. Be CONSERVATIVE — quality over quantity. Fewer, better nodes.

Importance rules:
- importance=3: The document's CORE THESIS or central argument. Maximum 1-2 per document.
- importance=2: Claims, evidence, or assumptions that directly support/underpin the core argument.
- importance=1: Background context, minor details, tangential observations.

Document role describes the FUNCTION of the node within the document's argument:
- thesis: The document's central argument or conclusion
- supporting_claim: A claim that supports the thesis
- supporting_evidence: Evidence cited to back up claims
- foundational_assumption: An assumption the argument depends on
- counterpoint: A counter-argument or qualification acknowledged by the document
- background: Context or background information
- detail: Minor or peripheral detail

Edge rules for argument structure:
- Evidence SUPPORTS claims it backs up
- Claims DEPEND ON assumptions they require
- Sub-claims SUPPORT the thesis they contribute to
- Mark genuine contradictions within the document (not just different emphasis)

Respond ONLY with a valid JSON object: {"nodes": [...], "edges": [...]}"""


# ═══════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════

def _validate_extraction_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate and normalize a single extracted node."""
    if not isinstance(item, dict):
        return None

    node_type = item.get('type', '').lower()
    if node_type not in [nt.value for nt in NodeType]:
        return None

    content = item.get('content', '').strip()
    if not content or len(content) < 10:
        return None

    # Validate/default status
    status = item.get('status')
    valid_statuses = VALID_STATUSES_BY_TYPE.get(node_type, set())
    if status and status not in valid_statuses:
        status = None
    if not status:
        status = DEFAULT_STATUS_BY_TYPE.get(node_type, 'unsubstantiated')

    # Validate confidence
    confidence = item.get('confidence', 0.8)
    if not isinstance(confidence, (int, float)):
        confidence = 0.8
    confidence = max(0.0, min(1.0, float(confidence)))

    # Validate importance (integer 1-3, default 2)
    importance = item.get('importance', 2)
    if not isinstance(importance, int):
        try:
            importance = int(importance)
        except (TypeError, ValueError):
            importance = 2
    importance = max(1, min(3, importance))

    # Validate document_role
    document_role = item.get('document_role', 'detail')
    if document_role not in VALID_DOCUMENT_ROLES:
        document_role = 'detail'

    # Preserve temp id for edge resolution
    temp_id = item.get('id', '')

    return {
        'id': temp_id,
        'type': node_type,
        'content': content,
        'status': status,
        'confidence': confidence,
        'importance': importance,
        'document_role': document_role,
        'source_passage': item.get('source_passage', ''),
        'properties': item.get('properties', {}),
    }


def _validate_extraction_edge(edge: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate a single extracted edge."""
    if not isinstance(edge, dict):
        return None

    source_id = edge.get('source_id', '')
    target_id = edge.get('target_id', '')
    edge_type = edge.get('edge_type', '').lower()

    if not source_id or not target_id:
        return None

    if edge_type not in VALID_EDGE_TYPES:
        return None

    return {
        'source_id': source_id,
        'target_id': target_id,
        'edge_type': edge_type,
        'provenance': edge.get('provenance', ''),
    }


# ═══════════════════════════════════════════════════════════════════
# Chunk provenance matching
# ═══════════════════════════════════════════════════════════════════

def _match_source_chunks(
    item: Dict[str, Any],
    chunks: List[DocumentChunk],
) -> List:
    """
    Match an extracted node to its source chunks.

    Strategy:
    1. Text match: find chunks containing the source_passage
    2. Embedding fallback: find most similar chunk via embedding cosine
    3. Last resort: no assignment (rather than wrong provenance)
    """
    if not chunks:
        return []

    source_passage = item.get('source_passage', '')
    if not source_passage:
        return []

    # Strategy 1: text match
    matched_ids = []
    passage_lower = source_passage.lower()

    for chunk in chunks:
        if passage_lower in chunk.chunk_text.lower():
            matched_ids.append(chunk.id)

    if matched_ids:
        return matched_ids

    # Strategy 2: substring match (first 80 chars)
    prefix = passage_lower[:80]
    if len(prefix) >= 30:
        for chunk in chunks:
            if prefix in chunk.chunk_text.lower():
                matched_ids.append(chunk.id)
        if matched_ids:
            return matched_ids

    # Strategy 3: embedding similarity fallback
    try:
        passage_embedding = generate_embedding(source_passage)
        chunk_qs = DocumentChunk.objects.filter(
            id__in=[c.id for c in chunks]
        )
        similar = list(
            similarity_search(
                chunk_qs,
                'embedding',
                passage_embedding,
                threshold=0.75,
                top_k=2,
            )
        )
        if similar:
            return [c.id for c in similar]
    except Exception:
        logger.debug("Embedding fallback failed for chunk matching", exc_info=True)

    return []
