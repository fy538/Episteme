"""
AI Document Generator - Orchestrates AI document creation.

Coordinates research with document persistence.
"""
from apps.agents.research_agent import ResearchAgent
from apps.cases.document_service import WorkingDocumentService


class AIDocumentGenerator:
    """
    Orchestrates AI document generation.
    
    Coordinates research agents with the document storage system.
    """
    
    def __init__(self):
        self.research_agent = ResearchAgent()
    
    def generate_research_for_inquiry(self, inquiry, user):
        """
        Generate comprehensive research for an inquiry.
        
        Args:
            inquiry: Inquiry object
            user: User requesting research
        
        Returns:
            Created WorkingDocument (type=research)
        """
        # Get context
        case_context = f"{inquiry.case.title}"
        if inquiry.case.position:
            case_context += f": {inquiry.case.position}"
        
        inquiry_context = inquiry.title
        if inquiry.description:
            inquiry_context += f"\n{inquiry.description}"
        
        # Collect existing sources
        sources = self._get_existing_sources(inquiry.case)
        
        # Generate research using agent
        result = self.research_agent.generate_research(
            topic=inquiry.title,
            case_context=case_context,
            inquiry_context=inquiry_context,
            sources=sources
        )
        
        # Create research document
        research_doc = WorkingDocumentService.create_research_document(
            case=inquiry.case,
            inquiry=inquiry,
            title=f"Research: {inquiry.title}",
            content=result['content'],
            ai_structure=result['structure'],
            user=user,
            generation_prompt=f"Research topic: {inquiry.title}"
        )
        
        return research_doc
    

    def _get_existing_sources(self, case):
        """
        Get list of existing documents to reference in research.
        
        Args:
            case: Case object
        
        Returns:
            List of source dictionaries
        """
        from apps.cases.models import WorkingDocument
        
        docs = WorkingDocument.objects.filter(case=case)
        return [
            {
                "title": doc.title,
                "type": doc.document_type,
                "generated_by_ai": doc.generated_by_ai
            }
            for doc in docs
            if doc.document_type != 'case_brief'  # Don't include brief in sources
        ]
