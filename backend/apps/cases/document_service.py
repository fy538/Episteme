"""
Case document service - business logic for document operations.

Handles creation, updates, and citation management for case documents.
"""
import logging
import re

from django.db import transaction
from django.contrib.auth.models import User

from apps.cases.models import Case, WorkingDocument, DocumentType, EditFriction, DocumentCitation, CaseStatus
from apps.cases.brief_templates import BriefTemplateGenerator
from apps.cases.citation_parser import CitationParser
from apps.inquiries.models import Inquiry

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Section marker validation
# --------------------------------------------------------------------------- #

# Matches <!-- section:SECTION_ID --> where SECTION_ID is alphanumeric + dash/underscore
SECTION_MARKER_RE = re.compile(r'<!-- section:([a-zA-Z0-9_-]+) -->')


def validate_section_markers(document: WorkingDocument) -> dict:
    """
    Validate that every BriefSection's section_id has a corresponding
    ``<!-- section:ID -->`` marker in the document's content_markdown.

    Returns a dict with:
        valid (bool): True if all section IDs have markers and vice-versa.
        missing_markers (list[str]): Section IDs in DB but not in content.
        orphaned_markers (list[str]): Markers in content with no matching
            BriefSection row.
        matched (list[str]): Section IDs present in both DB and content.
    """
    from apps.cases.brief_models import BriefSection  # avoid circular import

    content = document.content_markdown or ''

    # Section IDs registered in the database
    db_section_ids = set(
        BriefSection.objects.filter(brief=document)
        .values_list('section_id', flat=True)
    )

    # Section IDs found in the markdown content
    content_section_ids = set(SECTION_MARKER_RE.findall(content))

    missing_markers = sorted(db_section_ids - content_section_ids)
    orphaned_markers = sorted(content_section_ids - db_section_ids)
    matched = sorted(db_section_ids & content_section_ids)

    return {
        'valid': len(missing_markers) == 0 and len(orphaned_markers) == 0,
        'missing_markers': missing_markers,
        'orphaned_markers': orphaned_markers,
        'matched': matched,
    }


def log_marker_integrity(document: WorkingDocument) -> None:
    """
    Run marker validation and log warnings for any mismatches.

    Non-blocking — this is informational. User edits may temporarily
    remove markers, so we log but don't raise.
    """
    result = validate_section_markers(document)
    if result['valid']:
        return

    doc_label = f'Document {document.id} ({document.title})'
    if result['missing_markers']:
        logger.warning(
            '%s: section IDs in DB but missing from content: %s',
            doc_label,
            result['missing_markers'],
        )
    if result['orphaned_markers']:
        logger.warning(
            '%s: markers in content with no matching BriefSection: %s',
            doc_label,
            result['orphaned_markers'],
        )


class WorkingDocumentService:
    """Service for case document operations"""
    
    @staticmethod
    @transaction.atomic
    def create_case_with_brief(
        user: User,
        title: str,
        project_id: str = None,
        content_markdown: str = None,
        **case_kwargs
    ) -> tuple[Case, WorkingDocument]:
        """
        Create case and auto-generate main brief with AI outline.

        Args:
            user: User creating the case
            title: Case title
            project_id: Optional project ID
            content_markdown: Optional pre-built markdown content
                (used by CaseScaffoldService to pass scaffolded content
                instead of using BriefTemplateGenerator)
            **case_kwargs: Additional case fields

        Returns:
            Tuple of (case, case_brief)
        """
        # Create case
        case = Case.objects.create(
            user=user,
            title=title,
            project_id=project_id,
            status=CaseStatus.DRAFT,
            **case_kwargs
        )

        # Use provided content or generate default outline
        if content_markdown is not None:
            outline = content_markdown
        else:
            outline = BriefTemplateGenerator.generate_case_brief_outline(case)

        # Create case brief document
        case_brief = WorkingDocument.objects.create(
            case=case,
            document_type=DocumentType.CASE_BRIEF,
            title=f"{title} - Brief",
            content_markdown=outline,
            edit_friction=EditFriction.LOW,
            generated_by_ai=False,  # Outline is AI-assisted, but user owns it
            created_by=user
        )

        # Link as main brief
        case.main_brief = case_brief
        case.save(update_fields=['main_brief'])

        return case, case_brief
    
    @staticmethod
    @transaction.atomic
    def create_inquiry_with_brief(
        case: Case,
        title: str,
        user: User,
        elevation_reason: str = 'user_created'
    ) -> tuple[Inquiry, WorkingDocument]:
        """
        Create inquiry and auto-generate inquiry brief with AI outline.
        
        Args:
            case: Case this inquiry belongs to
            title: Inquiry title
            user: User creating the inquiry
            elevation_reason: Why this inquiry was created
        
        Returns:
            Tuple of (inquiry, inquiry_brief)
        """
        # Calculate sequence index (select_for_update prevents concurrent duplicates)
        last_inquiry = (
            case.inquiries.select_for_update()
            .order_by('-sequence_index')
            .first()
        )
        sequence_index = (last_inquiry.sequence_index + 1) if last_inquiry else 0
        
        # Create inquiry
        inquiry = Inquiry.objects.create(
            case=case,
            title=title,
            elevation_reason=elevation_reason,
            sequence_index=sequence_index
        )
        
        # Generate brief outline using AI
        outline = BriefTemplateGenerator.generate_inquiry_brief_outline(inquiry)
        
        # Create inquiry brief document
        inquiry_brief = WorkingDocument.objects.create(
            case=case,
            inquiry=inquiry,
            document_type=DocumentType.INQUIRY_BRIEF,
            title=f"{title} - Brief",
            content_markdown=outline,
            edit_friction=EditFriction.LOW,
            generated_by_ai=False,
            created_by=user
        )
        
        # Link brief to inquiry
        inquiry.brief = inquiry_brief
        inquiry.save(update_fields=['brief'])
        
        return inquiry, inquiry_brief
    
    @staticmethod
    @transaction.atomic
    def update_document_content(
        document: WorkingDocument,
        new_content: str,
        user: User
    ) -> WorkingDocument:
        """
        Update document content and reparse citations.
        
        Enforces edit friction rules:
        - LOW: Anyone can edit
        - HIGH: Only creator can edit (annotations for others)
        - READONLY: No one can edit (annotations only)
        
        Args:
            document: Document to update
            new_content: New markdown content
            user: User making the update
        
        Returns:
            Updated document
        
        Raises:
            PermissionError: If user doesn't have edit permission
        """
        # Check edit permissions
        if document.edit_friction == EditFriction.READONLY:
            raise PermissionError("Document is read-only. Use annotations instead.")
        
        if document.edit_friction == EditFriction.HIGH:
            if document.created_by != user:
                raise PermissionError("Document has high edit friction. Only creator can edit. Use annotations instead.")
        
        # Update content
        document.content_markdown = new_content
        document.save(update_fields=['content_markdown', 'updated_at'])

        # Reparse citations
        CitationParser.create_citation_links(document)

        # Log section marker integrity (non-blocking)
        if document.brief_sections.exists():
            log_marker_integrity(document)

        return document
    
    @staticmethod
    def create_research_document(
        case: Case,
        inquiry: Inquiry,
        title: str,
        content: str,
        ai_structure: dict,
        user: User,
        generation_prompt: str = ''
    ) -> WorkingDocument:
        """
        Create AI-generated research document.
        
        Args:
            case: Case this research belongs to
            inquiry: Inquiry this research is for (optional)
            title: Research title
            content: Markdown content (AI-generated)
            ai_structure: Extracted findings/structure
            user: User who requested the research
            generation_prompt: Prompt used to generate
        
        Returns:
            Created research document
        """
        research_doc = WorkingDocument.objects.create(
            case=case,
            inquiry=inquiry,
            document_type=DocumentType.RESEARCH,
            title=title,
            content_markdown=content,
            edit_friction=EditFriction.HIGH,  # AI docs are high friction
            ai_structure=ai_structure,
            generated_by_ai=True,
            agent_type='research',
            generation_prompt=generation_prompt,
            created_by=user
        )
        
        return research_doc
    
