"""
AI Document Generator - Orchestrates AI document creation.

Coordinates research, debates, and critiques with document persistence.
"""
from apps.agents.research_agent import ResearchAgent
from apps.agents.debate_agent import DebateAgent
from apps.agents.critique_agent import CritiqueAgent
from apps.cases.document_service import CaseDocumentService


class AIDocumentGenerator:
    """
    Orchestrates AI document generation.
    
    Coordinates research agents, debate simulations, and critiques
    with the document storage system.
    """
    
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.debate_agent = DebateAgent()
        self.critique_agent = CritiqueAgent()
    
    def generate_research_for_inquiry(self, inquiry, user):
        """
        Generate comprehensive research for an inquiry.
        
        Args:
            inquiry: Inquiry object
            user: User requesting research
        
        Returns:
            Created CaseDocument (type=research)
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
        research_doc = CaseDocumentService.create_research_document(
            case=inquiry.case,
            inquiry=inquiry,
            title=f"Research: {inquiry.title}",
            content=result['content'],
            ai_structure=result['structure'],
            user=user,
            generation_prompt=f"Research topic: {inquiry.title}"
        )
        
        return research_doc
    
    def generate_debate_for_inquiry(self, inquiry, personas, user):
        """
        Generate debate between personas for an inquiry.
        
        Args:
            inquiry: Inquiry object
            personas: List of personas like [{"name": "Tech Lead", "role": "..."}]
            user: User requesting debate
        
        Returns:
            Created CaseDocument (type=debate)
        """
        case_context = f"{inquiry.case.title}: {inquiry.case.position}"
        
        # Generate debate using agent
        result = self.debate_agent.generate_debate(
            topic=inquiry.title,
            personas=personas,
            case_context=case_context
        )
        
        # Create debate document
        debate_doc = CaseDocumentService.create_debate_document(
            case=inquiry.case,
            inquiry=inquiry,
            title=f"Debate: {inquiry.title}",
            content=result['content'],
            ai_structure=result['structure'],
            user=user
        )
        
        return debate_doc
    
    def generate_critique_for_inquiry(self, inquiry, user):
        """
        Generate critique of inquiry position.
        
        Args:
            inquiry: Inquiry object
            user: User requesting critique
        
        Returns:
            Created CaseDocument (type=critique)
        """
        # Get position to critique from inquiry brief or description
        if inquiry.brief and inquiry.brief.content_markdown:
            target_position = inquiry.brief.content_markdown
        elif inquiry.description:
            target_position = inquiry.description
        else:
            target_position = f"Position: {inquiry.title}"
        
        # Generate critique using agent
        result = self.critique_agent.generate_critique(
            target_position=target_position,
            inquiry_context=inquiry.title,
            case_context=inquiry.case.title
        )
        
        # Create critique document
        critique_doc = CaseDocumentService.create_critique_document(
            case=inquiry.case,
            inquiry=inquiry,
            title=f"Critique: {inquiry.title}",
            content=result['content'],
            ai_structure=result['structure'],
            user=user
        )
        
        return critique_doc
    
    def _get_existing_sources(self, case):
        """
        Get list of existing documents to reference in research.
        
        Args:
            case: Case object
        
        Returns:
            List of source dictionaries
        """
        from apps.cases.models import CaseDocument
        
        docs = CaseDocument.objects.filter(case=case)
        return [
            {
                "title": doc.title,
                "type": doc.document_type,
                "generated_by_ai": doc.generated_by_ai
            }
            for doc in docs
            if doc.document_type != 'case_brief'  # Don't include brief in sources
        ]
