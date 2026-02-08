"""
Celery tasks for universal evidence ingestion.

These tasks wrap EvidenceIngestionService methods for async execution.
Use these when ingestion is triggered from API endpoints or Django signal
handlers where blocking is undesirable.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    autoretry_for=(ConnectionError, TimeoutError),
)
def ingest_evidence_async(
    self,
    inputs_data: list,
    case_id: str,
    user_id: int,
    source_label: str = 'Ingested Evidence',
    run_auto_reasoning: bool = True,
):
    """
    Async wrapper for EvidenceIngestionService.ingest().

    Args:
        inputs_data: List of dicts (serialized EvidenceInput — Celery
                     can't serialize dataclasses natively)
        case_id: UUID string of the target Case
        user_id: Integer ID of the User
        source_label: Label for the synthetic document
        run_auto_reasoning: Whether to run signal linking
    """
    from django.contrib.auth import get_user_model
    from apps.cases.models import Case
    from apps.projects.ingestion_service import (
        EvidenceIngestionService,
        EvidenceInput,
    )

    User = get_user_model()
    try:
        case = Case.objects.get(id=case_id)
        user = User.objects.get(id=user_id)
    except (Case.DoesNotExist, User.DoesNotExist) as e:
        logger.error(
            "ingestion_task_data_missing",
            extra={'case_id': case_id, 'user_id': user_id, 'error': str(e)},
        )
        return {'status': 'failed', 'error': f'Missing data: {e}'}

    # Reconstruct EvidenceInput objects from dicts
    inputs = [EvidenceInput(**d) for d in inputs_data]

    result = EvidenceIngestionService.ingest(
        inputs=inputs,
        case=case,
        user=user,
        source_label=source_label,
        run_auto_reasoning=run_auto_reasoning,
    )

    # Emit event for provenance tracking
    try:
        from apps.events.services import EventService
        from apps.events.models import EventType, ActorType

        EventService.append(
            event_type=EventType.EVIDENCE_ADDED,
            payload={
                'evidence_count': len(result.evidence_ids),
                'document_id': result.document_id,
                'links_created': result.links_created,
                'contradictions_detected': result.contradictions_detected,
                'retrieval_method': inputs[0].retrieval_method if inputs else '',
                'source_label': source_label,
            },
            actor_type=ActorType.SYSTEM,
            case_id=case_id,
        )
    except Exception as e:
        logger.warning(f"Failed to emit EVIDENCE_ADDED event: {e}")

    logger.info(
        "evidence_ingestion_complete",
        extra={
            'case_id': case_id,
            'evidence_count': len(result.evidence_ids),
            'links_created': result.links_created,
            'contradictions': result.contradictions_detected,
            'source_label': source_label,
        },
    )

    return {
        'status': 'completed',
        'evidence_ids': result.evidence_ids,
        'links_created': result.links_created,
        'contradictions_detected': result.contradictions_detected,
    }


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def fetch_url_and_ingest(
    self,
    url: str,
    case_id: str,
    user_id: int,
):
    """
    Fetch a URL, extract text content, and process as a document.

    Uses the existing document processing pipeline (Path B) which
    already handles: chunk → embed → extract evidence → auto-reasoning.

    Args:
        url: URL to fetch
        case_id: UUID string of the target Case
        user_id: Integer ID of the User
    """
    from django.contrib.auth import get_user_model
    from apps.cases.models import Case
    from apps.projects.models import Document
    from apps.projects.url_fetcher import fetch_url_content

    User = get_user_model()
    try:
        case = Case.objects.get(id=case_id)
        user = User.objects.get(id=user_id)
    except (Case.DoesNotExist, User.DoesNotExist) as e:
        logger.error(
            "url_fetch_task_data_missing",
            extra={'url': url, 'case_id': case_id, 'user_id': user_id, 'error': str(e)},
        )
        return {'status': 'failed', 'error': f'Missing data: {e}'}

    # Fetch URL content
    fetched = fetch_url_content(url)
    if fetched.error or not fetched.text:
        logger.warning(
            "url_fetch_failed",
            extra={'url': url, 'error': fetched.error or 'No content'},
        )
        return {'status': 'failed', 'error': fetched.error or 'No content'}

    # Create a Document for the fetched content
    doc = Document.objects.create(
        title=fetched.title or url,
        source_type='url',
        content_text=fetched.text,
        file_url=url,
        file_type='html',
        project=case.project,
        case=case,
        user=user,
        author=fetched.author or '',
        published_date=fetched.published_date,
        processing_status='pending',
    )

    # Delegate to existing document processing pipeline (Path B)
    # This handles: chunk → embed → extract evidence → auto-reasoning → cascade
    from tasks.workflows import process_document_workflow
    process_document_workflow.delay(str(doc.id))

    logger.info(
        "url_fetched_and_queued",
        extra={
            'url': url,
            'case_id': case_id,
            'document_id': str(doc.id),
            'title': fetched.title,
            'text_length': len(fetched.text),
        },
    )

    return {
        'status': 'accepted',
        'document_id': str(doc.id),
        'title': fetched.title,
        'text_length': len(fetched.text),
    }
