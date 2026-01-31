"""
Document signal extraction

DEPRECATED: This module is deprecated in favor of the new chunking-based approach.

The new system (apps/projects/document_processor.py + chunker.py) preserves
full document context instead of extracting lossy signals. Documents are
chunked and indexed for semantic search, then cited as evidence in inquiries.

This module is kept for backward compatibility but should not be used for
new documents. Use process_document_workflow instead of 
extract_document_signals_workflow.

Extract signals from uploaded documents (PDFs, docs, text, etc.)
"""
import logging
import warnings
from typing import List, Optional
from sentence_transformers import SentenceTransformer

# Issue deprecation warning
warnings.warn(
    "document_extractors.py is deprecated. Use apps/projects/document_processor.py "
    "and chunker.py for new document processing. See DOCUMENT_SYSTEM_IMPLEMENTATION.md",
    DeprecationWarning,
    stacklevel=2
)

from apps.projects.models import Document
from apps.signals.models import Signal, SignalType, SignalSourceType
from apps.signals.prompts import get_signal_extraction_prompt
from apps.signals.extractors import SignalExtractor
from apps.common.utils import normalize_text, generate_dedupe_key

logger = logging.getLogger(__name__)

class DocumentSignalExtractor:
    """
    Extract signals from documents
    
    Similar to chat extraction, but:
    - Works on document chunks (pages, sections)
    - No conversation context
    - Tracks document position (page, paragraph)
    """
    
    def __init__(self):
        # Reuse the same embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Reuse chat extractor's LLM logic
        self.chat_extractor = SignalExtractor()
    
    def extract_from_document(
        self,
        document: Document,
        chunk_size: int = 1000,  # Characters per chunk
    ) -> List[Signal]:
        """
        Extract signals from a document
        
        Args:
            document: Document to extract from
            chunk_size: Size of text chunks to process
        
        Returns:
            List of Signal objects (not yet saved)
        """
        if not document.content_text:
            return []
        
        # 1. Chunk the document
        chunks = self._chunk_document(document.content_text, chunk_size)
        
        # 2. Extract from each chunk
        all_signals = []
        for idx, chunk in enumerate(chunks):
            signals = self._extract_from_chunk(
                document=document,
                chunk_text=chunk['text'],
                chunk_index=idx,
                chunk_start=chunk['start'],
                chunk_end=chunk['end'],
            )
            all_signals.extend(signals)
        
        return all_signals
    
    def _chunk_document(
        self,
        text: str,
        chunk_size: int
    ) -> List[dict]:
        """
        Split document into overlapping chunks
        
        Args:
            text: Full document text
            chunk_size: Size of each chunk
        
        Returns:
            List of chunks with metadata
        """
        chunks = []
        overlap = chunk_size // 4  # 25% overlap
        
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for period, newline, or other breaks
                for break_char in ['. ', '\n', '! ', '? ']:
                    last_break = text[start:end].rfind(break_char)
                    if last_break > chunk_size // 2:  # At least halfway
                        end = start + last_break + len(break_char)
                        break
            
            chunks.append({
                'text': text[start:end],
                'start': start,
                'end': end,
            })
            
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def _extract_from_chunk(
        self,
        document: Document,
        chunk_text: str,
        chunk_index: int,
        chunk_start: int,
        chunk_end: int,
    ) -> List[Signal]:
        """
        Extract signals from a document chunk
        
        Args:
            document: Source document
            chunk_text: Text of this chunk
            chunk_index: Index of chunk (0, 1, 2...)
            chunk_start: Start position in full document
            chunk_end: End position in full document
        
        Returns:
            List of Signal objects (not saved)
        """
        # Build extraction prompt (no conversation context for documents)
        prompt = get_signal_extraction_prompt(
            user_message=chunk_text,
            conversation_context=""  # No context for documents
        )
        
        # Call LLM (reuse chat extractor's logic)
        extracted_data = self.chat_extractor._call_llm(prompt)
        
        if not extracted_data:
            return []
        
        # Create Signal objects
        signals = []
        for item in extracted_data:
            try:
                # Generate embedding
                embedding_vector = self.embedding_model.encode(
                    item['text'],
                    convert_to_numpy=True
                )
                
                # Create signal
                signal = Signal(
                    # Core fields
                    text=item['text'],
                    type=item['type'],
                    normalized_text=normalize_text(item['text']),
                    confidence=item.get('confidence', 0.8),
                    
                    # Source tracking
                    source_type=SignalSourceType.DOCUMENT,
                    document=document,
                    
                    # Positioning (chunk-based for documents)
                    sequence_index=chunk_index,
                    
                    # Embedding
                    embedding=embedding_vector.tolist(),
                    
                    # Deduplication
                    dedupe_key=generate_dedupe_key(
                        item['type'],
                        normalize_text(item['text']),
                        scope_hint=str(document.id)
                    ),
                    
                    # Relationships (set after document is linked to case/project)
                    case=document.case,
                    # thread is None for documents
                    # event will be linked in the workflow
                    
                    # Span tracking (in document coordinates)
                    span={
                        'document_id': str(document.id),
                        'chunk_index': chunk_index,
                        'chunk_start': chunk_start,
                        'chunk_end': chunk_end,
                        'local_start': item.get('span', {}).get('start', 0),
                        'local_end': item.get('span', {}).get('end', len(chunk_text)),
                    },
                )
                signals.append(signal)
                
            except Exception:
                logger.exception(
                    "document_signal_creation_failed",
                    extra={
                        "document_id": str(document.id),
                        "chunk_index": chunk_index,
                        "signal_type": item.get("type"),
                    },
                )
                continue
        
        return signals


# Singleton
_document_extractor_instance = None


def get_document_extractor() -> DocumentSignalExtractor:
    """Get or create singleton document extractor"""
    global _document_extractor_instance
    if _document_extractor_instance is None:
        _document_extractor_instance = DocumentSignalExtractor()
    return _document_extractor_instance
