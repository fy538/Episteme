"""
Evidence extraction from document chunks

Extract factual evidence (metrics, benchmarks, claims) from documents.
This is DIFFERENT from signal extraction:

- Signals = User's thoughts (from chat)
- Evidence = External facts (from documents)

Evidence provides "receipts" that support or contradict user signals.
"""
from typing import List
from sentence_transformers import SentenceTransformer

from apps.projects.models import Evidence, DocumentChunk, EvidenceType
from apps.signals.prompts import get_evidence_extraction_prompt
from apps.signals.extractors import SignalExtractor  # Reuse LLM calling logic


class EvidenceExtractor:
    """
    Extract evidence from document chunks.
    
    Design principles:
    - Lighter than signal extraction (facts only, not thoughts)
    - Annotates chunks (doesn't replace them)
    - Only for user-uploaded documents (not AI-generated)
    """
    
    def __init__(self):
        # Reuse same embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Reuse signal extractor's LLM calling logic
        self.signal_extractor = SignalExtractor()
    
    def extract_from_chunk(self, chunk: DocumentChunk) -> List[Evidence]:
        """
        Extract evidence from a single document chunk
        
        Args:
            chunk: DocumentChunk to extract from
        
        Returns:
            List of Evidence objects (not yet saved)
        """
        
        # Check if we should extract from this chunk
        if not self.should_extract(chunk):
            return []
        
        # Build prompt
        prompt = get_evidence_extraction_prompt(
            chunk_text=chunk.chunk_text,
            document_title=chunk.document.title
        )
        
        # Call LLM (reuse signal extractor's logic)
        extracted_data = self.signal_extractor._call_llm(prompt)
        
        if not extracted_data:
            return []
        
        # Create Evidence objects
        evidence_list = []
        
        for item in extracted_data:
            try:
                # Generate embedding
                embedding_vector = self.embedding_model.encode(
                    item['text'],
                    convert_to_numpy=True
                ).tolist()
                
                # Validate type
                if item['type'] not in [choice[0] for choice in EvidenceType.choices]:
                    # Skip invalid types
                    continue
                
                # Create evidence object
                evidence = Evidence(
                    text=item['text'],
                    type=item['type'],
                    chunk=chunk,
                    document=chunk.document,
                    extraction_confidence=item.get('confidence', 0.8),
                    embedding=embedding_vector,
                )
                
                evidence_list.append(evidence)
                
            except Exception as e:
                print(f"Failed to create evidence from {item}: {e}")
                continue
        
        return evidence_list
    
    def should_extract(self, chunk: DocumentChunk) -> bool:
        """
        Decide if we should extract evidence from this chunk.
        
        Skip:
        - Very short chunks (likely headers/formatting)
        - Chunks from AI-generated artifacts (they cite sources, don't create evidence)
        - Non-substantive content
        
        Args:
            chunk: Chunk to evaluate
        
        Returns:
            True if extraction should proceed
        """
        # Skip very short chunks
        if chunk.token_count < 100:
            return False
        
        # Skip if chunk is mostly whitespace
        if len(chunk.chunk_text.strip()) < 50:
            return False
        
        # TODO Phase 2.4: Skip if document is an AI-generated artifact
        # if chunk.document.document_type in ['ai_research', 'ai_brief']:
        #     return False
        
        return True
    
    def extract_from_document(self, document) -> int:
        """
        Extract evidence from all chunks in a document.
        
        Args:
            document: Document to process
        
        Returns:
            Number of evidence items extracted
        """
        from apps.projects.models import Document
        
        total_evidence = 0
        
        # Get all chunks for this document
        chunks = document.chunks.order_by('chunk_index')
        
        for chunk in chunks:
            # Extract evidence from chunk
            evidence_list = self.extract_from_chunk(chunk)
            
            # Bulk create evidence
            if evidence_list:
                Evidence.objects.bulk_create(evidence_list)
                total_evidence += len(evidence_list)
        
        return total_evidence


# Singleton
_evidence_extractor_instance = None


def get_evidence_extractor() -> EvidenceExtractor:
    """Get or create singleton evidence extractor"""
    global _evidence_extractor_instance
    if _evidence_extractor_instance is None:
        _evidence_extractor_instance = EvidenceExtractor()
    return _evidence_extractor_instance
