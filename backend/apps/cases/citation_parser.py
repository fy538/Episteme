"""
Citation parser - extract and link citations from markdown.

Parses [[document-title#section]] patterns and creates DocumentCitation objects.
"""
import re
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.cases.models import WorkingDocument


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
    def create_citation_links(document: 'WorkingDocument') -> int:
        """
        Parse document content and create DocumentCitation objects.
        
        This is called automatically when a document is saved.
        Clears existing citations and recreates from current content.
        
        Args:
            document: WorkingDocument to parse
        
        Returns:
            Number of citations created
        """
        from apps.cases.models import WorkingDocument, DocumentCitation
        
        # Clear existing outgoing citations
        document.outgoing_citations.all().delete()
        
        # Extract citations from markdown
        citations = CitationParser.extract_citations(document.content_markdown)
        
        if not citations:
            return 0
        
        # Create citation objects
        created_count = 0
        cited_doc_ids = set()

        for citation_data in citations:
            # Find target document by title in same case
            # Use icontains for flexible matching
            target_doc = WorkingDocument.objects.filter(
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
                cited_doc_ids.add(target_doc.id)

        # Batch-update citation counts for all affected documents
        for target_doc in WorkingDocument.objects.filter(id__in=cited_doc_ids):
            target_doc.times_cited = target_doc.incoming_citations.count()
            target_doc.save(update_fields=['times_cited'])

        return created_count
    
