"""
Embedding-based Intent Router

Classifies user messages into intent categories using local embedding
similarity (~10-50ms, no API call). Used by ContextAssemblyService to
adjust token budgets per intent.

Architecture:
  - Lazy-loads + caches exemplar embeddings on first call
  - Per-category: max cosine similarity of query vs all exemplars
  - Highest-scoring category wins
  - No external API — uses the local all-MiniLM-L12-v2 model
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intent categories
# ---------------------------------------------------------------------------

class IntentCategory(str, Enum):
    """Categories of user intent for routing."""
    RETRIEVAL_FACTUAL = "retrieval_factual"
    RETRIEVAL_ANALYTICAL = "retrieval_analytical"
    CONVERSATIONAL = "conversational"
    META_PROCESS = "meta_process"
    GRAPH_FOCUSED = "graph_focused"
    CROSS_REFERENCE = "cross_reference"


# ---------------------------------------------------------------------------
# Exemplar utterances per category (~8-12 each)
# ---------------------------------------------------------------------------

INTENT_EXAMPLES: Dict[IntentCategory, List[str]] = {
    IntentCategory.RETRIEVAL_FACTUAL: [
        "What does the report say about market size?",
        "Find the section about regulatory requirements",
        "What data do we have on customer churn?",
        "Show me the revenue figures from the analysis",
        "What did the study conclude about efficacy?",
        "Look up the definition of the term in our documents",
        "What are the key findings from the research paper?",
        "Find the statistics on user adoption rates",
        "What does the contract say about termination?",
        "What percentage of respondents agreed?",
    ],
    IntentCategory.RETRIEVAL_ANALYTICAL: [
        "What are the implications of the data we collected?",
        "How does this compare to industry benchmarks?",
        "What patterns do you see in these findings?",
        "Analyze the strengths and weaknesses of this approach",
        "What conclusions can we draw from the evidence?",
        "How does the data support or contradict our hypothesis?",
        "Synthesize the key insights across all our documents",
        "What are the risks associated with these findings?",
        "Evaluate the quality of evidence for this claim",
    ],
    IntentCategory.CONVERSATIONAL: [
        "I'm not sure about this decision",
        "Tell me more about that",
        "Can you explain that differently?",
        "That's interesting, but what about alternatives?",
        "I think we should consider another approach",
        "Let me think about this for a moment",
        "What do you think is the best option?",
        "I'm leaning towards option A, what do you think?",
        "Can you clarify what you mean?",
        "OK let's move on to the next topic",
    ],
    IntentCategory.META_PROCESS: [
        "What should I do next?",
        "Am I ready to make a decision?",
        "What questions haven't we explored yet?",
        "Where are the gaps in our analysis?",
        "What's the current state of our investigation?",
        "Do we have enough evidence to proceed?",
        "Help me create a plan for this investigation",
        "What assumptions haven't we validated?",
        "How confident should I be in this conclusion?",
        "Summarize our progress so far",
    ],
    IntentCategory.GRAPH_FOCUSED: [
        "What claims have the most evidence?",
        "Show me the tensions in our knowledge graph",
        "What assumptions are we making?",
        "Which evidence supports this claim?",
        "What are the weakest links in our reasoning?",
        "Are there any contradictions in what we know?",
        "What signals have we extracted so far?",
        "How well supported is this position?",
        "What evidence do we still need?",
        "Map out the argument structure",
    ],
    IntentCategory.CROSS_REFERENCE: [
        "How does this relate to what we discussed earlier?",
        "Does this connect to the other case?",
        "Have we seen this pattern before?",
        "What's the relationship between these two findings?",
        "Compare this to what we learned last week",
        "Is this consistent with our earlier analysis?",
        "Link this back to the original hypothesis",
        "How does this finding relate to the other documents?",
        "Connect the dots between these data points",
    ],
}


# ---------------------------------------------------------------------------
# Budget adjustments per intent (applied on top of mode budgets)
# ---------------------------------------------------------------------------

INTENT_BUDGET_ADJUSTMENTS: Dict[IntentCategory, Dict[str, int]] = {
    IntentCategory.RETRIEVAL_FACTUAL: {
        'retrieval': 1000,       # More retrieval budget
        'conversation': -500,    # Less conversation needed
    },
    IntentCategory.RETRIEVAL_ANALYTICAL: {
        'retrieval': 500,
        'system_prompt': 500,    # More room for analytical framing
        'conversation': -500,
    },
    IntentCategory.CONVERSATIONAL: {
        'conversation': 500,     # More conversation context
        'retrieval': -500,       # Less retrieval needed
    },
    IntentCategory.META_PROCESS: {
        'companion': 500,        # More companion state
        'system_prompt': 500,
        'retrieval': -500,
    },
    IntentCategory.GRAPH_FOCUSED: {
        'system_prompt': 1000,   # Graph serialization needs room
        'retrieval': -500,
    },
    IntentCategory.CROSS_REFERENCE: {
        'conversation': 500,     # Need more conversation history
        'retrieval': 500,        # Also more retrieval
        'companion': -500,
    },
}


# ---------------------------------------------------------------------------
# Classification result
# ---------------------------------------------------------------------------

@dataclass
class IntentResult:
    """Result of intent classification."""
    category: IntentCategory
    confidence: float
    runner_up: Optional[IntentCategory] = None
    runner_up_confidence: float = 0.0


# ---------------------------------------------------------------------------
# Router (singleton, lazy-loaded)
# ---------------------------------------------------------------------------

class IntentRouter:
    """
    Classifies user messages into intent categories using embedding similarity.

    Singleton: exemplar embeddings are computed once and cached for the
    lifetime of the process.

    Usage:
        result = IntentRouter().classify("What does the report say?")
        # result.category == IntentCategory.RETRIEVAL_FACTUAL
        # result.confidence == 0.73
    """

    _instance: Optional[IntentRouter] = None
    _exemplar_embeddings: Optional[Dict[IntentCategory, list]] = None

    def __new__(cls) -> IntentRouter:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def classify(self, message: str) -> IntentResult:
        """
        Classify a user message into an intent category.

        Args:
            message: The user's message text

        Returns:
            IntentResult with category, confidence, and runner-up
        """
        if not message or len(message.strip()) < 5:
            return IntentResult(
                category=IntentCategory.CONVERSATIONAL,
                confidence=0.0,
            )

        self._ensure_exemplars_loaded()

        try:
            from apps.common.embeddings import generate_embedding
            from apps.common.vector_utils import batch_cosine_similarity

            # Embed the query
            query_embedding = generate_embedding(message)
            if not query_embedding:
                return IntentResult(
                    category=IntentCategory.CONVERSATIONAL,
                    confidence=0.0,
                )

            # Score against each category's exemplars
            scores: Dict[IntentCategory, float] = {}
            for category, embeddings in self._exemplar_embeddings.items():
                if not embeddings:
                    scores[category] = 0.0
                    continue
                similarities = batch_cosine_similarity(query_embedding, embeddings)
                # Use max similarity as the category score
                scores[category] = float(similarities.max())

            # Sort by score descending
            ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            best_category, best_score = ranked[0]
            runner_up_category, runner_up_score = ranked[1] if len(ranked) > 1 else (None, 0.0)

            return IntentResult(
                category=best_category,
                confidence=round(best_score, 3),
                runner_up=runner_up_category,
                runner_up_confidence=round(runner_up_score, 3),
            )

        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return IntentResult(
                category=IntentCategory.CONVERSATIONAL,
                confidence=0.0,
            )

    def _ensure_exemplars_loaded(self) -> None:
        """Lazy-load and cache exemplar embeddings."""
        if self._exemplar_embeddings is not None:
            return

        try:
            from apps.common.embeddings import generate_embeddings_batch

            self.__class__._exemplar_embeddings = {}

            for category, examples in INTENT_EXAMPLES.items():
                embeddings = generate_embeddings_batch(examples)
                # Filter out None values (invalid texts)
                valid_embeddings = [e for e in embeddings if e is not None]
                self.__class__._exemplar_embeddings[category] = valid_embeddings

            total = sum(
                len(v) for v in self._exemplar_embeddings.values()
            )
            logger.info(
                f"Intent router loaded {total} exemplar embeddings "
                f"across {len(self._exemplar_embeddings)} categories"
            )
        except Exception as e:
            logger.warning(f"Failed to load intent exemplar embeddings: {e}")
            # Fallback: empty embeddings so classification returns low confidence
            self.__class__._exemplar_embeddings = {
                cat: [] for cat in IntentCategory
            }
