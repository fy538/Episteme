"""
Universal Evidence Ingestion Service

Single entry point for all evidence flowing into the knowledge graph.
Every ingestion path (research loop, external paste, URL fetch, chat bridge)
routes through EvidenceIngestionService.ingest().

Pipeline stages:
  1. Ensure Document + DocumentChunk exist (create synthetic if needed)
  2. Create projects.Evidence records with provenance metadata
  3. Generate embeddings (if not pre-computed)
  4. Run auto-reasoning pipeline (find similar signals, classify, link M2M)
  5. M2M link changes trigger Mechanism A cascade automatically
     (assumption status → plan sync → brief grounding)
"""
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from asgiref.sync import async_to_sync
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.cases.constants import EVIDENCE_TEXT_MAX_LEN

logger = logging.getLogger(__name__)


@dataclass
class EvidenceInput:
    """
    Universal evidence input DTO.

    Every ingestion path constructs one or more of these and passes
    them to EvidenceIngestionService.ingest().
    """
    text: str
    evidence_type: str = 'fact'  # EvidenceType choices
    extraction_confidence: float = 0.8

    # Provenance
    source_url: str = ''
    source_title: str = ''
    source_domain: str = ''
    source_published_date: Optional[str] = None  # ISO date string
    retrieval_method: str = 'document_upload'

    # Optional: pre-existing document/chunk to link to
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None

    # Optional: cross-link to inquiries.Evidence
    inquiry_evidence_id: Optional[str] = None

    # Optional: pre-computed embedding (skip regeneration)
    embedding: Optional[List[float]] = None


@dataclass
class IngestionResult:
    """Result of ingesting one or more evidence items."""
    evidence_ids: List[str] = field(default_factory=list)
    document_id: Optional[str] = None
    links_created: int = 0
    contradictions_detected: int = 0
    cascade_triggered: bool = False
    errors: List[str] = field(default_factory=list)


class EvidenceIngestionService:
    """
    Universal evidence ingestion pipeline.

    Usage:
        result = EvidenceIngestionService.ingest(
            inputs=[EvidenceInput(text="Market is growing 20% YoY", ...)],
            case=case,
            user=user,
            source_label="Perplexity Research",
        )
    """

    @staticmethod
    def ingest(
        inputs: List[EvidenceInput],
        case,
        user,
        source_label: str = 'Ingested Evidence',
        run_auto_reasoning: bool = True,
    ) -> IngestionResult:
        """
        Ingest one or more evidence items through the full pipeline.

        This method is the single convergence point for all evidence
        entering the knowledge graph. It handles:
        - Document/Chunk scaffolding
        - Evidence record creation with provenance
        - Embedding generation
        - Auto-reasoning (signal linking via M2M, which triggers cascade)

        Args:
            inputs: List of EvidenceInput DTOs
            case: Case model instance
            user: User model instance
            source_label: Label for the synthetic document (if created)
            run_auto_reasoning: Whether to run signal linking (set False for bulk)

        Returns:
            IngestionResult with created IDs and cascade info
        """
        result = IngestionResult()

        if not inputs:
            return result

        # Stage 1+2: Create document/chunk and evidence records (atomic)
        created_evidence, doc = _create_evidence_records(
            inputs, case, user, source_label
        )
        result.document_id = str(doc.id) if doc else None
        result.evidence_ids = [str(e.id) for e in created_evidence]

        if not created_evidence:
            return result

        # Stage 3: Generate embeddings for items that don't have them
        _generate_missing_embeddings(created_evidence)

        # Stage 4: Auto-reasoning (signal linking)
        # This calls evidence.supports_signals.add(signal) which triggers
        # Mechanism A cascade via m2m_changed signal handler.
        if run_auto_reasoning:
            reasoning = _run_auto_reasoning(created_evidence)
            result.links_created = reasoning['links_created']
            result.contradictions_detected = reasoning['contradictions']
            result.cascade_triggered = reasoning['cascade_triggered']
            result.errors.extend(reasoning.get('errors', []))

        return result


@transaction.atomic
def _create_evidence_records(
    inputs: List[EvidenceInput],
    case,
    user,
    source_label: str,
):
    """
    Create Document (if needed), DocumentChunk, and Evidence records.

    Returns (created_evidence_list, document).
    """
    from apps.projects.models import (
        Document,
        DocumentChunk,
        Evidence as ProjectEvidence,
    )

    # Determine if we need a synthetic document
    # If all inputs reference an existing document, use it directly
    first_with_doc = next((i for i in inputs if i.document_id), None)

    if first_with_doc and all(i.document_id for i in inputs):
        try:
            doc = Document.objects.get(id=first_with_doc.document_id)
            chunk = doc.chunks.first()
        except Document.DoesNotExist:
            doc, chunk = _create_synthetic_document(case, user, source_label, inputs)
    else:
        doc, chunk = _create_synthetic_document(case, user, source_label, inputs)

    created_evidence = []
    for ev_input in inputs:
        text = ev_input.text[:EVIDENCE_TEXT_MAX_LEN]
        if not text.strip():
            continue

        # Parse source_domain from URL if not provided
        source_domain = ev_input.source_domain
        if not source_domain and ev_input.source_url:
            try:
                source_domain = urlparse(ev_input.source_url).netloc
            except Exception:
                source_domain = ''

        # Parse published_date
        pub_date = None
        if ev_input.source_published_date:
            from django.utils.dateparse import parse_date
            pub_date = parse_date(ev_input.source_published_date)

        # Resolve document/chunk for this specific input
        target_doc = doc
        target_chunk = chunk
        if ev_input.document_id:
            try:
                target_doc = Document.objects.get(id=ev_input.document_id)
                if ev_input.chunk_id:
                    target_chunk = DocumentChunk.objects.get(id=ev_input.chunk_id)
                else:
                    target_chunk = target_doc.chunks.first() or chunk
            except (Document.DoesNotExist, DocumentChunk.DoesNotExist):
                pass  # Fall back to synthetic

        evidence = ProjectEvidence(
            text=text,
            type=ev_input.evidence_type,
            chunk=target_chunk,
            document=target_doc,
            extraction_confidence=ev_input.extraction_confidence,
            embedding=ev_input.embedding,
            source_url=ev_input.source_url[:2000] if ev_input.source_url else '',
            source_title=ev_input.source_title[:500] if ev_input.source_title else '',
            source_domain=source_domain[:255] if source_domain else '',
            source_published_date=pub_date,
            retrieval_method=ev_input.retrieval_method,
        )
        if ev_input.inquiry_evidence_id:
            evidence.inquiry_evidence_id = ev_input.inquiry_evidence_id

        created_evidence.append(evidence)

    # Bulk create for efficiency
    if created_evidence:
        ProjectEvidence.objects.bulk_create(created_evidence)

        # Update document evidence count atomically (avoids race condition)
        from apps.projects.models import Document
        Document.objects.filter(id=doc.id).update(
            evidence_count=F('evidence_count') + len(created_evidence)
        )

    return created_evidence, doc


def _create_synthetic_document(case, user, source_label, inputs):
    """Create a lightweight Document + single DocumentChunk as FK target."""
    from apps.projects.models import Document, DocumentChunk

    retrieval_method = inputs[0].retrieval_method if inputs else 'external_paste'

    doc = Document.objects.create(
        title=f"{source_label} ({timezone.now().strftime('%Y-%m-%d %H:%M')})",
        source_type='text',
        content_text=f'Evidence ingested via {retrieval_method}.',
        file_type='ingested',
        project=case.project,
        case=case,
        user=user,
        processing_status='indexed',
        indexed_at=timezone.now(),
    )

    chunk = DocumentChunk.objects.create(
        document=doc,
        chunk_index=0,
        chunk_text=doc.content_text,
        token_count=0,
    )

    return doc, chunk


def _generate_missing_embeddings(evidence_list):
    """Generate embeddings for evidence items that lack them."""
    from apps.common.embeddings import generate_embedding, generate_embeddings_batch
    from apps.projects.models import Evidence as ProjectEvidence

    # Collect items that need embeddings
    needs_embedding = [e for e in evidence_list if not e.embedding]
    if not needs_embedding:
        return

    # Use batch generation for efficiency
    texts = [e.text for e in needs_embedding]
    try:
        embeddings = generate_embeddings_batch(texts)
        for evidence, emb in zip(needs_embedding, embeddings):
            if emb:
                evidence.embedding = emb
    except Exception as e:
        logger.warning(
            "batch_embedding_failed, falling back to individual",
            extra={"error": str(e)},
        )
        for evidence in needs_embedding:
            try:
                emb = generate_embedding(evidence.text)
                if emb:
                    evidence.embedding = emb
            except Exception as e2:
                logger.error(
                    "embedding_generation_failed",
                    extra={"evidence_id": str(evidence.id), "error": str(e2)},
                )

    # Batch save all embeddings at once
    updated = [e for e in needs_embedding if e.embedding]
    if updated:
        ProjectEvidence.objects.bulk_update(updated, ['embedding'], batch_size=100)


def _run_auto_reasoning(evidence_list) -> Dict[str, Any]:
    """
    Run auto-reasoning pipeline on new evidence items.

    This calls AutoReasoningPipeline.process_new_evidence() which
    may call evidence.supports_signals.add(signal), triggering
    Mechanism A cascade (assumption recomputation → plan sync → brief grounding).

    Uses async_to_sync to safely call the async pipeline from both
    Django request context and Celery worker context.
    """
    from apps.reasoning.auto_reasoning import get_auto_reasoning_pipeline

    pipeline = get_auto_reasoning_pipeline()
    _process_sync = async_to_sync(pipeline.process_new_evidence)

    total_links = 0
    total_contradictions = 0
    cascade_triggered = False
    errors = []

    for evidence in evidence_list:
        if not evidence.embedding:
            continue  # Can't do similarity search without embedding
        try:
            results = _process_sync(evidence)
            links = len(results.get('links_created', []))
            contradictions = len(results.get('contradictions_detected', []))
            total_links += links
            total_contradictions += contradictions
            if links or contradictions:
                cascade_triggered = True
        except Exception as e:
            logger.error(
                "auto_reasoning_failed_for_evidence",
                extra={"evidence_id": str(evidence.id), "error": str(e)},
            )
            errors.append(f"Evidence {evidence.id}: {str(e)}")

    return {
        'links_created': total_links,
        'contradictions': total_contradictions,
        'cascade_triggered': cascade_triggered,
        'errors': errors,
    }
