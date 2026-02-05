"""
Auto-reasoning pipeline - Automatically build knowledge graph from evidence
"""
import logging
import uuid
from typing import Dict, List, Tuple, Optional
import numpy as np

from apps.projects.models import Evidence
from apps.signals.models import Signal
from apps.inquiries.models import Inquiry, Objection
from apps.common.llm_providers.factory import get_llm_provider

logger = logging.getLogger(__name__)


class AutoReasoningPipeline:
    """
    Automatically build reasoning graph from new content.
    
    When evidence is extracted from documents:
    1. Find semantically similar signals/evidence/inquiries
    2. Use LLM to classify relationships (supports/contradicts/refines)
    3. Auto-create graph edges
    4. Detect contradictions and create objections
    5. Update inquiry confidence scores
    """
    
    def __init__(self):
        self.llm = get_llm_provider('fast')  # Use Haiku for efficiency
        self.similarity_threshold = 0.82  # High threshold for auto-linking
    
    async def process_new_evidence(self, evidence: Evidence) -> Dict:
        """
        Process newly extracted evidence and build graph connections.
        
        Args:
            evidence: Evidence item that was just extracted
        
        Returns:
            Dict with: links_created, contradictions_detected, confidence_changes
        """
        results = {
            'links_created': [],
            'contradictions_detected': [],
            'confidence_changes': [],
            'similar_nodes_found': 0
        }
        
        try:
            # 1. Find semantically similar nodes
            similar_nodes = await self._find_similar_nodes(evidence)
            results['similar_nodes_found'] = len(similar_nodes)
            
            if not similar_nodes:
                return results
            
            # 2. Classify relationships and create links
            for node in similar_nodes[:5]:  # Limit to top 5 to avoid spam
                relationship = await self._classify_relationship(evidence, node)
                
                if relationship['confidence'] < 0.70:
                    # Low confidence - skip
                    continue
                
                if relationship['type'] == 'SUPPORTS':
                    # Auto-link as supporting evidence
                    await self._create_support_link(evidence, node, relationship)
                    results['links_created'].append({
                        'from': str(evidence.id),
                        'to': str(node['id']),
                        'type': 'supports',
                        'confidence': relationship['confidence']
                    })
                
                elif relationship['type'] == 'CONTRADICTS':
                    # Flag contradiction
                    contradiction = await self._handle_contradiction(evidence, node, relationship)
                    results['contradictions_detected'].append(contradiction)
            
            # 3. Update inquiry confidence if evidence was linked
            if results['links_created']:
                confidence_changes = await self._update_inquiry_confidence(evidence)
                results['confidence_changes'] = confidence_changes
            
            logger.info(
                f"Auto-reasoning complete for evidence {evidence.id}",
                extra={
                    'evidence_id': str(evidence.id),
                    'links_created': len(results['links_created']),
                    'contradictions': len(results['contradictions_detected'])
                }
            )
            
        except Exception:
            logger.exception(
                "auto_reasoning_failed",
                extra={'evidence_id': str(evidence.id)}
            )
        
        return results
    
    async def _find_similar_nodes(
        self, 
        evidence: Evidence
    ) -> List[Dict]:
        """
        Find semantically similar signals using embedding similarity.
        
        Args:
            evidence: Evidence to find matches for
        
        Returns:
            List of similar nodes with similarity scores
        """
        if not evidence.embedding:
            return []
        
        similar_nodes = []
        evidence_embedding = np.array(evidence.embedding)
        
        # Search for similar signals in same case
        if evidence.document.case:
            signals = Signal.objects.filter(
                case=evidence.document.case,
                dismissed_at__isnull=True,
                embedding__isnull=False
            ).exclude(
                type='EvidenceMention'  # Skip evidence mentions
            )
            
            for signal in signals:
                signal_embedding = np.array(signal.embedding)
                similarity = self._cosine_similarity(evidence_embedding, signal_embedding)
                
                if similarity >= self.similarity_threshold:
                    similar_nodes.append({
                        'id': signal.id,
                        'type': 'signal',
                        'text': signal.text,
                        'signal_type': signal.type,
                        'similarity': similarity,
                        'object': signal
                    })
        
        # Sort by similarity
        similar_nodes.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similar_nodes
    
    async def _classify_relationship(
        self,
        evidence: Evidence,
        node: Dict
    ) -> Dict:
        """
        Use LLM to classify relationship between evidence and node.
        
        Args:
            evidence: Evidence item
            node: Similar node (signal/evidence/inquiry)
        
        Returns:
            Dict with type, confidence, reasoning
        """
        prompt = f"""Analyze the relationship between these two statements:

Statement A (evidence from document):
"{evidence.text}"
Source: {evidence.document.title}
Type: {evidence.type}

Statement B (existing {node['type']}):
"{node['text']}"

Determine the relationship:
1. SUPPORTS - A provides evidence that backs up B
2. CONTRADICTS - A conflicts with or disproves B  
3. REFINES - A is a more specific version of B
4. NEUTRAL - Related but neither supports nor contradicts

Respond in JSON format:
{{"type": "SUPPORTS|CONTRADICTS|REFINES|NEUTRAL", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

        # Call LLM
        full_response = ""
        async for chunk in self.llm.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are an expert at analyzing logical relationships between statements.",
            temperature=0.3,  # Low temperature for consistency
            max_tokens=150
        ):
            full_response += chunk.content
        
        # Parse JSON response
        import json
        try:
            # Extract JSON from response (might have markdown formatting)
            json_start = full_response.find('{')
            json_end = full_response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(full_response[json_start:json_end])
                return result
            else:
                # Fallback
                return {'type': 'NEUTRAL', 'confidence': 0.5, 'reasoning': 'Parse error'}
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse relationship analysis: {e}")
            return {'type': 'NEUTRAL', 'confidence': 0.5, 'reasoning': 'Parse error'}
    
    async def _create_support_link(
        self,
        evidence: Evidence,
        node: Dict,
        relationship: Dict
    ):
        """Create supporting relationship between evidence and signal."""
        if node['type'] == 'signal':
            signal = node['object']
            # Add to ManyToMany relationship
            from asgiref.sync import sync_to_async
            await sync_to_async(evidence.supports_signals.add)(signal)
            
            logger.info(
                f"Auto-linked evidence to signal (supports)",
                extra={
                    'evidence_id': str(evidence.id),
                    'signal_id': str(signal.id),
                    'confidence': relationship['confidence']
                }
            )
    
    async def _handle_contradiction(
        self,
        evidence: Evidence,
        node: Dict,
        relationship: Dict
    ) -> Dict:
        """
        Handle detected contradiction.
        
        Creates contradiction edge and potentially an objection.
        """
        contradiction = {
            'evidence_id': str(evidence.id),
            'evidence_text': evidence.text,
            'contradicts_type': node['type'],
            'contradicts_id': str(node['id']),
            'contradicts_text': node['text'],
            'confidence': relationship['confidence'],
            'reasoning': relationship['reasoning']
        }
        
        # Create contradiction link
        if node['type'] == 'signal':
            signal = node['object']
            from asgiref.sync import sync_to_async
            await sync_to_async(evidence.contradicts_signals.add)(signal)
            
            # If signal is linked to an inquiry, create objection
            if signal.inquiry:
                objection = await sync_to_async(Objection.objects.create)(
                    inquiry=signal.inquiry,
                    objection_text=f"New evidence contradicts assumption: {evidence.text}",
                    objection_type='counter_evidence',
                    source='system',
                    source_document=evidence.document,
                    created_by=evidence.document.user
                )
                
                # Link evidence chunk
                await sync_to_async(objection.source_chunks.add)(evidence.chunk)
                
                contradiction['objection_created'] = str(objection.id)
        
        logger.info(
            f"Contradiction detected and handled",
            extra={
                'evidence_id': str(evidence.id),
                'contradicts_id': str(node['id']),
                'confidence': relationship['confidence']
            }
        )
        
        return contradiction
    
    async def _update_inquiry_confidence(
        self,
        evidence: Evidence
    ) -> List[Dict]:
        """
        Update inquiry confidence based on new evidence.
        
        Simple heuristic: 
        - Supporting evidence increases confidence
        - Contradicting evidence decreases confidence
        """
        from asgiref.sync import sync_to_async
        
        confidence_changes = []
        
        # Get inquiries affected by this evidence
        # (inquiries linked to signals that this evidence supports/contradicts)
        supporting_signals = await sync_to_async(list)(evidence.supports_signals.all())
        contradicting_signals = await sync_to_async(list)(evidence.contradicts_signals.all())
        
        affected_inquiries = set()
        for signal in supporting_signals + contradicting_signals:
            if signal.inquiry:
                affected_inquiries.add(signal.inquiry)
        
        for inquiry in affected_inquiries:
            old_confidence = inquiry.conclusion_confidence or 0.5
            
            # Calculate new confidence (simple heuristic)
            # More sophisticated logic can be added later
            supporting_count = len([s for s in supporting_signals if s.inquiry == inquiry])
            contradicting_count = len([s for s in contradicting_signals if s.inquiry == inquiry])
            
            if contradicting_count > 0:
                # Decrease confidence
                new_confidence = max(0.1, old_confidence - 0.10)
            elif supporting_count > 0:
                # Increase confidence  
                new_confidence = min(0.95, old_confidence + 0.05)
            else:
                new_confidence = old_confidence
            
            if abs(new_confidence - old_confidence) > 0.01:
                inquiry.conclusion_confidence = new_confidence
                await sync_to_async(inquiry.save)()
                
                confidence_changes.append({
                    'inquiry_id': str(inquiry.id),
                    'title': inquiry.title,
                    'old': round(old_confidence, 2),
                    'new': round(new_confidence, 2),
                    'reason': f"New evidence: {evidence.text[:50]}..."
                })
        
        return confidence_changes
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))


# Singleton instance
_auto_reasoning_pipeline = None


def get_auto_reasoning_pipeline() -> AutoReasoningPipeline:
    """Get or create singleton auto-reasoning pipeline."""
    global _auto_reasoning_pipeline
    if _auto_reasoning_pipeline is None:
        _auto_reasoning_pipeline = AutoReasoningPipeline()
    return _auto_reasoning_pipeline
