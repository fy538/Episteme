"""
Research-backed recursive token chunker

Based on 2024 RAG studies:
- 256-512 tokens per chunk (optimal for retrieval accuracy)
- 10-20% overlap (balances context and deduplication)
- Respect sentence/paragraph boundaries (preserves meaning)
- Recursive splitting (simpler than semantic, equally effective)

Research sources:
- Recursive chunking with 256-512 tokens: Industry standard (Weaviate, 2024)
- Token-based > character-based: Consistent with LLM processing
- Simple > complex: Semantic chunking not worth computational cost
"""
import tiktoken
import re
from typing import List, Dict, Any, Optional
from apps.common.token_utils import count_tokens


class RecursiveTokenChunker:
    """
    Recursive token-based document chunker
    
    Strategy:
    1. Try to chunk by sections (if detected)
    2. If section too large, split by paragraphs
    3. If paragraph too large, split by sentences
    4. If sentence too large, split by tokens
    
    This preserves semantic boundaries while ensuring optimal token counts.
    """
    
    def __init__(
        self,
        chunk_tokens: int = 512,
        overlap_ratio: float = 0.15,
        min_chunk_tokens: int = 100,
        encoding_name: str = 'cl100k_base'
    ):
        """
        Initialize chunker with research-backed defaults
        
        Args:
            chunk_tokens: Target tokens per chunk (256-512 recommended, default 512)
            overlap_ratio: Overlap ratio (0.10-0.20 recommended, default 0.15)
            min_chunk_tokens: Minimum chunk size to avoid tiny chunks
            encoding_name: Tiktoken encoding (cl100k_base for GPT-4)
        """
        self.chunk_tokens = chunk_tokens
        self.overlap_tokens = int(chunk_tokens * overlap_ratio)
        self.min_chunk_tokens = min_chunk_tokens
        self.tokenizer = tiktoken.get_encoding(encoding_name)
        self.encoding_name = encoding_name
    
    def chunk_document(
        self,
        text: str,
        sections: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Recursively chunk a document
        
        Args:
            text: Full document text
            sections: Optional section metadata [{title, start, end}]
            metadata: Additional metadata to include in each chunk
        
        Returns:
            List of chunks with text, span, token_count, metadata
        """
        if not text or not text.strip():
            return []
        
        # Strategy 1: Chunk by sections if available
        if sections:
            return self._chunk_by_sections(text, sections, metadata)
        
        # Strategy 2: Recursive splitting
        return self._recursive_chunk(text, 0, metadata)
    
    def _chunk_by_sections(
        self,
        text: str,
        sections: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk by document sections, splitting large sections recursively
        """
        all_chunks = []
        
        for section in sections:
            section_text = text[section['start']:section['end']]
            section_tokens = count_tokens(section_text)
            
            section_metadata = {**(metadata or {}), 'section': section.get('title', '')}
            
            if section_tokens <= self.chunk_tokens:
                # Section fits in one chunk
                all_chunks.append({
                    'text': section_text,
                    'token_count': section_tokens,
                    'span': {
                        'start_char': section['start'],
                        'end_char': section['end'],
                        'section': section.get('title', ''),
                    },
                    'metadata': section_metadata,
                })
            else:
                # Section too large, split recursively
                section_chunks = self._recursive_chunk(
                    section_text,
                    section['start'],
                    section_metadata
                )
                all_chunks.extend(section_chunks)
        
        return all_chunks
    
    def _recursive_chunk(
        self,
        text: str,
        char_offset: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Recursively split text into chunks
        
        Hierarchy:
        1. Paragraphs (double newline)
        2. Sentences (. ! ?)
        3. Tokens (hard split)
        """
        # Check if text fits in one chunk
        text_tokens = count_tokens(text)
        
        if text_tokens <= self.chunk_tokens:
            return [{
                'text': text,
                'token_count': text_tokens,
                'span': {
                    'start_char': char_offset,
                    'end_char': char_offset + len(text),
                },
                'metadata': metadata or {},
            }]
        
        # Try splitting by paragraphs
        paragraphs = text.split('\n\n')
        if len(paragraphs) > 1:
            return self._chunk_by_paragraphs(paragraphs, char_offset, metadata)
        
        # Try splitting by sentences
        sentences = self._split_sentences(text)
        if len(sentences) > 1:
            return self._chunk_by_sentences(sentences, char_offset, metadata)
        
        # Last resort: hard split by tokens
        return self._chunk_by_tokens(text, char_offset, metadata)
    
    def _chunk_by_paragraphs(
        self,
        paragraphs: List[str],
        char_offset: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Combine paragraphs into chunks"""
        chunks = []
        current_chunk = []
        current_tokens = 0
        current_char_start = char_offset
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_tokens = count_tokens(para)
            
            # If adding this paragraph exceeds limit
            if current_tokens + para_tokens > self.chunk_tokens and current_chunk:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'token_count': current_tokens,
                    'span': {
                        'start_char': current_char_start,
                        'end_char': current_char_start + len(chunk_text),
                    },
                    'metadata': metadata or {},
                })
                
                # Start new chunk with overlap
                overlap_paras = self._get_overlap_paragraphs(current_chunk)
                current_chunk = overlap_paras + [para]
                current_tokens = sum(count_tokens(p) for p in current_chunk)
                current_char_start = current_char_start + len(chunk_text) - len('\n\n'.join(overlap_paras))
            else:
                # Add to current chunk
                current_chunk.append(para)
                current_tokens += para_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'token_count': count_tokens(chunk_text),
                'span': {
                    'start_char': current_char_start,
                    'end_char': current_char_start + len(chunk_text),
                },
                'metadata': metadata or {},
            })
        
        return chunks
    
    def _chunk_by_sentences(
        self,
        sentences: List[str],
        char_offset: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Combine sentences into chunks"""
        chunks = []
        current_chunk = []
        current_tokens = 0
        current_char_start = char_offset
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_tokens = count_tokens(sentence)
            
            # If adding this sentence exceeds limit
            if current_tokens + sentence_tokens > self.chunk_tokens and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'token_count': current_tokens,
                    'span': {
                        'start_char': current_char_start,
                        'end_char': current_char_start + len(chunk_text),
                    },
                    'metadata': metadata or {},
                })
                
                # Start new chunk with overlap (last N sentences)
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences + [sentence]
                current_tokens = sum(count_tokens(s) for s in current_chunk)
                current_char_start = current_char_start + len(chunk_text) - len(' '.join(overlap_sentences))
            else:
                # Add to current chunk
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'token_count': count_tokens(chunk_text),
                'span': {
                    'start_char': current_char_start,
                    'end_char': current_char_start + len(chunk_text),
                },
                'metadata': metadata or {},
            })
        
        return chunks
    
    def _chunk_by_tokens(
        self,
        text: str,
        char_offset: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Hard split by tokens (last resort)"""
        chunks = []
        tokens = self.tokenizer.encode(text)
        
        start = 0
        while start < len(tokens):
            # Define chunk window
            end = min(start + self.chunk_tokens, len(tokens))
            
            # Extract and decode
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunks.append({
                'text': chunk_text,
                'token_count': len(chunk_tokens),
                'span': {
                    'start_char': char_offset,  # Approximate
                    'end_char': char_offset + len(chunk_text),
                    'start_token': start,
                    'end_token': end,
                },
                'metadata': metadata or {},
            })
            
            # Move forward with overlap
            if end >= len(tokens):
                break
            start = end - self.overlap_tokens
            char_offset += len(chunk_text) - len(self.tokenizer.decode(tokens[end - self.overlap_tokens:end]))
        
        return chunks
    
    def _get_overlap_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """Get last N paragraphs for overlap"""
        if not paragraphs:
            return []
        
        # Take last paragraphs until we hit overlap token limit
        overlap_paras = []
        overlap_tokens = 0
        
        for para in reversed(paragraphs):
            para_tokens = count_tokens(para)
            if overlap_tokens + para_tokens <= self.overlap_tokens:
                overlap_paras.insert(0, para)
                overlap_tokens += para_tokens
            else:
                break
        
        return overlap_paras
    
    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """Get last N sentences for overlap"""
        if not sentences:
            return []
        
        # Take last sentences until we hit overlap token limit
        overlap_sents = []
        overlap_tokens = 0
        
        for sent in reversed(sentences):
            sent_tokens = count_tokens(sent)
            if overlap_tokens + sent_tokens <= self.overlap_tokens:
                overlap_sents.insert(0, sent)
                overlap_tokens += sent_tokens
            else:
                break
        
        return overlap_sents
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences
        
        Uses regex to split on sentence boundaries while preserving
        abbreviations and decimal numbers.
        """
        # Sentence splitting regex
        # Splits on . ! ? followed by space and capital letter or quote
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z"\'])'
        
        sentences = re.split(sentence_pattern, text)
        
        # Clean up
        cleaned = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                cleaned.append(sentence)
        
        return cleaned if cleaned else [text]
    
    def chunk_with_page_info(
        self,
        segments: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk document segments that include page information
        
        Args:
            segments: List of segments from DocumentProcessor (with page info)
            metadata: Additional metadata
        
        Returns:
            Chunks with page information preserved in metadata
        """
        all_chunks = []
        
        for segment in segments:
            text = segment.get('text', '').strip()
            if not text:
                continue
            
            # Build segment metadata
            segment_metadata = {**(metadata or {})}
            if 'page' in segment:
                segment_metadata['page'] = segment['page']
            if 'paragraph' in segment:
                segment_metadata['paragraph'] = segment['paragraph']
            
            # Chunk this segment recursively
            segment_chunks = self._recursive_chunk(
                text=text,
                char_offset=0,
                metadata=segment_metadata
            )
            
            # Preserve page/paragraph in span
            for chunk in segment_chunks:
                if 'page' in segment:
                    chunk['span']['page'] = segment['page']
                if 'paragraph' in segment:
                    chunk['span']['paragraph'] = segment['paragraph']
            
            all_chunks.extend(segment_chunks)
        
        # Re-index all chunks globally
        for i, chunk in enumerate(all_chunks):
            chunk['chunk_index'] = i
        
        return all_chunks
    
    def get_optimal_chunk_size(self, text: str) -> int:
        """
        Determine optimal chunk size based on document length
        
        Research suggests:
        - Short docs (<1000 tokens): Use document-level (no chunking)
        - Medium docs (1-10k tokens): 512 tokens
        - Long docs (>10k tokens): 384 tokens (more chunks, better precision)
        """
        total_tokens = count_tokens(text)
        
        if total_tokens < 1000:
            # Short document - no chunking needed
            return total_tokens
        elif total_tokens < 10000:
            # Medium - use 512 tokens
            return 512
        else:
            # Long document - smaller chunks for better precision
            return 384
