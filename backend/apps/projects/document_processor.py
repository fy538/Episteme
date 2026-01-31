"""
Document processor - extract text from various file formats.

Handles PDF, DOCX, and text files.
"""
import mimetypes
from typing import List, Dict, Any
from pathlib import Path

from PyPDF2 import PdfReader
from docx import Document as DocxDocument


class DocumentProcessor:
    """
    Process uploaded documents and extract text.
    
    Supports:
    - PDF files
    - DOCX files
    - Plain text files (txt, md, etc.)
    """
    
    @staticmethod
    def extract_text(file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from various file types.
        
        Args:
            file_path: Path to file
        
        Returns:
            List of text segments with location metadata
        
        Raises:
            ValueError: If file type is not supported
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if mime_type == 'application/pdf':
            return DocumentProcessor._extract_pdf(file_path)
        elif mime_type in [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword'
        ]:
            return DocumentProcessor._extract_docx(file_path)
        elif mime_type and mime_type.startswith('text/'):
            return DocumentProcessor._extract_text_file(file_path)
        else:
            # Try to guess from extension
            ext = Path(file_path).suffix.lower()
            if ext == '.pdf':
                return DocumentProcessor._extract_pdf(file_path)
            elif ext in ['.docx', '.doc']:
                return DocumentProcessor._extract_docx(file_path)
            elif ext in ['.txt', '.md', '.markdown', '.rst']:
                return DocumentProcessor._extract_text_file(file_path)
            else:
                raise ValueError(f"Unsupported file type: {mime_type or ext}")
    
    @staticmethod
    def _extract_pdf(file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF file.
        
        Returns list of pages with text and metadata.
        """
        try:
            reader = PdfReader(file_path)
            pages = []
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text.strip():  # Only include non-empty pages
                    pages.append({
                        'page': page_num,
                        'text': page_text,
                        'type': 'page'
                    })
            
            return pages
        except Exception as e:
            raise ValueError(f"Error extracting PDF: {str(e)}")
    
    @staticmethod
    def _extract_docx(file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from DOCX file.
        
        Returns list of paragraphs with metadata.
        """
        try:
            doc = DocxDocument(file_path)
            paragraphs = []
            
            for i, para in enumerate(doc.paragraphs, 1):
                para_text = para.text.strip()
                if para_text:  # Only include non-empty paragraphs
                    paragraphs.append({
                        'paragraph': i,
                        'text': para_text,
                        'type': 'paragraph'
                    })
            
            return paragraphs
        except Exception as e:
            raise ValueError(f"Error extracting DOCX: {str(e)}")
    
    @staticmethod
    def _extract_text_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from plain text file.
        
        Returns full text as single segment.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if content.strip():
                return [{
                    'text': content,
                    'type': 'text'
                }]
            return []
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                if content.strip():
                    return [{
                        'text': content,
                        'type': 'text'
                    }]
                return []
            except Exception as e:
                raise ValueError(f"Error reading text file: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error extracting text file: {str(e)}")
    
    @staticmethod
    def format_extracted_text(segments: List[Dict[str, Any]]) -> str:
        """
        Format extracted text segments into single string.
        
        Args:
            segments: List of text segments from extraction
        
        Returns:
            Formatted full text
        """
        formatted_parts = []
        
        for segment in segments:
            text = segment.get('text', '').strip()
            if not text:
                continue
            
            # Add context markers for structured documents
            if segment.get('type') == 'page':
                formatted_parts.append(f"\n--- Page {segment['page']} ---\n{text}")
            elif segment.get('type') == 'paragraph':
                formatted_parts.append(text)
            else:
                formatted_parts.append(text)
        
        return '\n\n'.join(formatted_parts)
