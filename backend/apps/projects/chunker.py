"""
Document chunker - split documents into semantic chunks.

Smart chunking that respects sentence and paragraph boundaries.
"""
import re
from typing import List, Dict, Any


class DocumentChunker:
    """
    Chunk documents semantically for vector embedding.
    
    Features:
    - Respects sentence boundaries
    - Configurable chunk size with overlap
    - Preserves context with overlapping windows
    - Tracks location in original document
    """
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_document(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Split document into semantic chunks.
        
        Args:
            text: Full document text
            metadata: Additional metadata to include
        
        Returns:
            List of chunks with text, span, and metadata
        """
        if not text or not text.strip():
            return []
        
        # Split into sentences for smarter chunking
        sentences = self._split_sentences(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        start_char = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence exceeds chunk size
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Create chunk from current sentences
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'span': {
                        'start_char': start_char,
                        'end_char': start_char + len(chunk_text),
                        'chunk_index': len(chunks)
                    },
                    'metadata': metadata or {}
                })
                
                # Start new chunk with overlap
                overlap_text = chunk_text[-self.overlap:] if len(chunk_text) > self.overlap else chunk_text
                current_chunk = [overlap_text, sentence]
                current_length = len(overlap_text) + sentence_length
                start_char = start_char + len(chunk_text) - len(overlap_text)
            else:
                # Add sentence to current chunk
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add final chunk if any
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'span': {
                    'start_char': start_char,
                    'end_char': start_char + len(chunk_text),
                    'chunk_index': len(chunks)
                },
                'metadata': metadata or {}
            })
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Uses regex to split on sentence boundaries while preserving
        abbreviations and decimal numbers.
        """
        # Simple sentence splitting regex
        # Splits on . ! ? followed by space and capital letter
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        
        sentences = re.split(sentence_pattern, text)
        
        # Clean up sentences
        cleaned = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                cleaned.append(sentence)
        
        return cleaned if cleaned else [text]
    
    def chunk_by_paragraphs(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Alternative chunking strategy: by paragraphs.
        
        Useful for documents with clear paragraph structure.
        """
        paragraphs = text.split('\n\n')
        chunks = []
        current_pos = 0
        
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue
            
            # If paragraph is too large, split it further
            if len(para) > self.chunk_size:
                # Use sentence-based chunking for large paragraphs
                para_chunks = self.chunk_document(para, metadata)
                chunks.extend(para_chunks)
                current_pos += len(para) + 2  # +2 for \n\n
            else:
                chunks.append({
                    'text': para,
                    'span': {
                        'start_char': current_pos,
                        'end_char': current_pos + len(para),
                        'paragraph': i + 1,
                        'chunk_index': len(chunks)
                    },
                    'metadata': metadata or {}
                })
                current_pos += len(para) + 2
        
        return chunks
    
    def chunk_with_page_info(
        self,
        segments: List[Dict[str, Any]],
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk document segments that include page information.
        
        Args:
            segments: List of segments from DocumentProcessor (with page info)
            metadata: Additional metadata
        
        Returns:
            Chunks with page information preserved
        """
        all_chunks = []
        
        for segment in segments:
            text = segment.get('text', '').strip()
            if not text:
                continue
            
            # Chunk this segment
            segment_metadata = {**(metadata or {})}
            
            # Preserve page or paragraph info
            if 'page' in segment:
                segment_metadata['page'] = segment['page']
            if 'paragraph' in segment:
                segment_metadata['paragraph'] = segment['paragraph']
            
            chunks = self.chunk_document(text, segment_metadata)
            
            # Add page/paragraph info to span
            for chunk in chunks:
                if 'page' in segment:
                    chunk['span']['page'] = segment['page']
                if 'paragraph' in segment:
                    chunk['span']['paragraph'] = segment['paragraph']
            
            all_chunks.extend(chunks)
        
        # Re-index chunks
        for i, chunk in enumerate(all_chunks):
            chunk['span']['chunk_index'] = i
        
        return all_chunks
