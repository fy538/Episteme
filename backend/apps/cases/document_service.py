"""
Case document service - business logic for document operations.

Handles creation, updates, and citation management for case documents.
"""
from django.db import transaction
from django.contrib.auth.models import User

from apps.cases.models import Case, CaseDocument, DocumentType, EditFriction, DocumentCitation, CaseStatus
from apps.cases.brief_templates import BriefTemplateGenerator
from apps.cases.citation_parser import CitationParser
from apps.inquiries.models import Inquiry


class CaseDocumentService:
    """Service for case document operations"""
    
    @staticmethod
    @transaction.atomic
    def create_case_with_brief(
        user: User,
        title: str,
        project_id: str = None,
        content_markdown: str = None,
        **case_kwargs
    ) -> tuple[Case, CaseDocument]:
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
        case_brief = CaseDocument.objects.create(
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
    ) -> tuple[Inquiry, CaseDocument]:
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
        # Calculate sequence index
        last_inquiry = case.inquiries.order_by('-sequence_index').first()
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
        inquiry_brief = CaseDocument.objects.create(
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
        document: CaseDocument,
        new_content: str,
        user: User
    ) -> CaseDocument:
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
    ) -> CaseDocument:
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
        research_doc = CaseDocument.objects.create(
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
    
    @staticmethod
    def create_debate_document(
        case: Case,
        inquiry: Inquiry,
        title: str,
        content: str,
        ai_structure: dict,
        user: User
    ) -> CaseDocument:
        """Create AI-generated debate document"""
        return CaseDocument.objects.create(
            case=case,
            inquiry=inquiry,
            document_type=DocumentType.DEBATE,
            title=title,
            content_markdown=content,
            edit_friction=EditFriction.HIGH,
            ai_structure=ai_structure,
            generated_by_ai=True,
            agent_type='debate',
            created_by=user
        )
    
    @staticmethod
    def create_critique_document(
        case: Case,
        inquiry: Inquiry,
        title: str,
        content: str,
        ai_structure: dict,
        user: User
    ) -> CaseDocument:
        """Create AI-generated critique document"""
        return CaseDocument.objects.create(
            case=case,
            inquiry=inquiry,
            document_type=DocumentType.CRITIQUE,
            title=title,
            content_markdown=content,
            edit_friction=EditFriction.HIGH,
            ai_structure=ai_structure,
            generated_by_ai=True,
            agent_type='critique',
            created_by=user
        )
    
    @staticmethod
    def get_case_document_hierarchy(case: Case) -> dict:
        """
        Get structured view of all documents in a case.
        
        Args:
            case: Case to get hierarchy for
        
        Returns:
            Dictionary with organized document structure
        """
        from apps.cases.models import CaseDocument
        
        # Get all documents
        docs = CaseDocument.objects.filter(case=case).select_related('inquiry')
        
        # Organize by type
        hierarchy = {
            'case_brief': None,
            'inquiry_briefs': [],
            'research_docs': [],
            'debate_docs': [],
            'critique_docs': [],
            'source_docs': [],
            'notes': []
        }
        
        for doc in docs:
            if doc.document_type == DocumentType.CASE_BRIEF:
                hierarchy['case_brief'] = doc
            elif doc.document_type == DocumentType.INQUIRY_BRIEF:
                hierarchy['inquiry_briefs'].append(doc)
            elif doc.document_type == DocumentType.RESEARCH:
                hierarchy['research_docs'].append(doc)
            elif doc.document_type == DocumentType.DEBATE:
                hierarchy['debate_docs'].append(doc)
            elif doc.document_type == DocumentType.CRITIQUE:
                hierarchy['critique_docs'].append(doc)
            elif doc.document_type == DocumentType.SOURCE:
                hierarchy['source_docs'].append(doc)
            elif doc.document_type == DocumentType.NOTES:
                hierarchy['notes'].append(doc)
        
        return hierarchy
