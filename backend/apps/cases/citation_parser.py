"""
Citation parser - extract and link citations from markdown.

Parses [[document-title#section]] patterns and creates DocumentCitation objects.
"""
import re
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.cases.models import CaseDocument


class CitationParser:
    """
    Parse citations from markdown content.
    
    Recognizes patterns:
    - [[document-title]]
    - [[document-title#section]]
    - [[Research: PostgreSQL Performance#findings]]
    - [[Inquiry Brief: Performance#conclusion]]
    
    Creates bidirectional DocumentCitation links automatically.
    """
    
    # Regex to match [[anything]]
    CITATION_PATTERN = r'\[\[([^\]]+)\]\]'
    
    @staticmethod
    def extract_citations(markdown_text: str) -> List[Dict]:
        """
        Extract all citations from markdown text.
        
        Args:
            markdown_text: Markdown content to parse
        
        Returns:
            List of citation dictionaries with:
            - text: Full [[...]] text
            - target_doc_title: Document title to link to
            - section: Section anchor (if specified)
            - line_number: Line number where citation appears
        """
        citations = []
        lines = markdown_text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Find all [[...]] patterns in this line
            matches = re.finditer(CitationParser.CITATION_PATTERN, line)
            
            for match in matches:
                citation_content = match.group(1)
                
                # Parse target#section
                if '#' in citation_content:
                    target, section = citation_content.split('#', 1)
                else:
                    target = citation_content
                    section = ''
                
                citations.append({
                    'text': f'[[{citation_content}]]',
                    'target_doc_title': target.strip(),
                    'section': section.strip(),
                    'line_number': line_num
                })
        
        return citations
    
    @staticmethod
    def create_citation_links(document: 'CaseDocument') -> int:
        """
        Parse document content and create DocumentCitation objects.
        
        This is called automatically when a document is saved.
        Clears existing citations and recreates from current content.
        
        Args:
            document: CaseDocument to parse
        
        Returns:
            Number of citations created
        """
        from apps.cases.models import CaseDocument, DocumentCitation
        
        # Clear existing outgoing citations
        document.outgoing_citations.all().delete()
        
        # Extract citations from markdown
        citations = CitationParser.extract_citations(document.content_markdown)
        
        if not citations:
            return 0
        
        # Create citation objects
        created_count = 0
        
        for citation_data in citations:
            # Find target document by title in same case
            # Use icontains for flexible matching
            target_doc = CaseDocument.objects.filter(
                case=document.case,
                title__icontains=citation_data['target_doc_title']
            ).first()
            
            if target_doc:
                DocumentCitation.objects.create(
                    from_document=document,
                    to_document=target_doc,
                    citation_text=citation_data['text'],
                    cited_section=citation_data['section'],
                    line_number=citation_data['line_number']
                )
                created_count += 1
                
                # Update citation count on target
                target_doc.times_cited = target_doc.incoming_citations.count()
                target_doc.save(update_fields=['times_cited'])
        
        return created_count
    
    @staticmethod
    def get_citation_suggestions(document: 'CaseDocument', case_documents: List['CaseDocument']) -> List[Dict]:
        """
        Suggest potential citations based on content analysis.
        
        Args:
            document: Document being edited
            case_documents: Other documents in the case to suggest
        
        Returns:
            List of suggested citations with relevance scores
        """
        suggestions = []
        
        # Simple keyword matching for now
        # (Can be enhanced with semantic similarity later)
        doc_text_lower = document.content_markdown.lower()
        
        for target_doc in case_documents:
            if target_doc.id == document.id:
                continue  # Don't suggest self-citation
            
            # Check if document title appears in content
            title_lower = target_doc.title.lower()
            
            # Remove common prefixes for matching
            title_clean = title_lower.replace('research:', '').replace('brief:', '').strip()
            
            if title_clean in doc_text_lower:
                suggestions.append({
                    'target_doc_id': str(target_doc.id),
                    'target_doc_title': target_doc.title,
                    'suggested_link': f'[[{target_doc.title}]]',
                    'relevance': 0.8,  # High relevance if title mentioned
                    'reason': f'Document mentions "{title_clean}"'
                })
        
        return suggestions
