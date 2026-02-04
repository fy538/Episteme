"""
Signal Extraction Rules Engine

Determines when to include signal extraction in unified analysis.
Uses heuristics to avoid over-extraction while ensuring important signals aren't missed.
"""

import re
from dataclasses import dataclass
from typing import Optional
from django.utils import timezone


@dataclass
class SignalExtractionRules:
    """Rules for signal extraction"""
    should_extract: bool
    reason: str
    include_types: list  # Which signal types to extract


class ExtractionRulesEngine:
    """
    Determines when to extract signals from conversation.

    Balances:
    - Not extracting too frequently (cost/noise)
    - Not missing important signals
    - Respecting user intent signals
    """

    # Minimum turns between extractions
    MIN_TURNS_BETWEEN = 2

    # Minimum characters since last extraction
    MIN_CHARS_BETWEEN = 200

    # Maximum turns without any extraction
    MAX_TURNS_WITHOUT = 5

    # Phrases that indicate high-value content
    TRIGGER_PHRASES = [
        # Assumptions
        "i assume", "i'm assuming", "assuming that", "i believe",
        "i think", "my assumption", "we assume",

        # Questions/Uncertainty
        "i'm not sure", "not sure if", "what if", "should we",
        "how do we", "is it possible", "could we",

        # Decisions
        "we decided", "decision is", "let's go with", "we'll use",
        "i've decided", "the plan is",

        # Constraints
        "must be", "can't be", "has to", "needs to", "requirement",
        "deadline", "budget", "limit",

        # Goals
        "goal is", "objective", "target", "aiming for",
        "want to achieve", "success means",

        # Claims
        "fact is", "the truth is", "actually", "in fact",
        "evidence shows", "data suggests", "according to",
    ]

    # Patterns for explicit signal markers
    EXPLICIT_SIGNAL_PATTERNS = [
        r'\b(assume|assumption)\b',
        r'\b(constraint|requirement|must|cannot)\b',
        r'\b(goal|objective|target)\b',
        r'\b(decide|decision|chose|choosing)\b',
        r'\b(question|uncertain|unsure)\b',
    ]

    @classmethod
    def should_extract(
        cls,
        thread,
        message_content: str,
        message_count: int,
        last_extraction_turn: Optional[int] = None,
        last_extraction_chars: Optional[int] = None,
        total_chars_since: int = 0
    ) -> SignalExtractionRules:
        """
        Determine if signals should be extracted for this message.

        Args:
            thread: ChatThread object
            message_content: Content of current user message
            message_count: Current message count in thread
            last_extraction_turn: Turn number of last extraction (0-indexed)
            last_extraction_chars: Character position of last extraction
            total_chars_since: Total characters since last extraction

        Returns:
            SignalExtractionRules with decision and reason
        """
        content_lower = message_content.lower()

        # Check for trigger phrases (high-value content)
        has_trigger = any(phrase in content_lower for phrase in cls.TRIGGER_PHRASES)

        # Check for explicit signal patterns
        has_explicit = any(
            re.search(pattern, content_lower)
            for pattern in cls.EXPLICIT_SIGNAL_PATTERNS
        )

        # Calculate turns since last extraction
        turns_since = message_count - (last_extraction_turn or 0)

        # Decision logic

        # 1. First message always extracts
        if message_count == 0 or last_extraction_turn is None:
            return SignalExtractionRules(
                should_extract=True,
                reason="first_message",
                include_types=cls._get_types_for_content(content_lower)
            )

        # 2. Too soon since last extraction (unless high-value)
        if turns_since < cls.MIN_TURNS_BETWEEN and not has_trigger:
            return SignalExtractionRules(
                should_extract=False,
                reason=f"too_soon ({turns_since} turns < {cls.MIN_TURNS_BETWEEN})",
                include_types=[]
            )

        # 3. Not enough content since last extraction
        if total_chars_since < cls.MIN_CHARS_BETWEEN and not has_trigger:
            return SignalExtractionRules(
                should_extract=False,
                reason=f"insufficient_content ({total_chars_since} chars < {cls.MIN_CHARS_BETWEEN})",
                include_types=[]
            )

        # 4. Max turns without extraction - force it
        if turns_since >= cls.MAX_TURNS_WITHOUT:
            return SignalExtractionRules(
                should_extract=True,
                reason=f"max_turns_reached ({turns_since} >= {cls.MAX_TURNS_WITHOUT})",
                include_types=cls._get_types_for_content(content_lower)
            )

        # 5. Trigger phrase detected
        if has_trigger:
            return SignalExtractionRules(
                should_extract=True,
                reason="trigger_phrase_detected",
                include_types=cls._get_types_for_content(content_lower)
            )

        # 6. Explicit signal pattern detected
        if has_explicit:
            return SignalExtractionRules(
                should_extract=True,
                reason="explicit_signal_pattern",
                include_types=cls._get_types_for_content(content_lower)
            )

        # 7. Enough turns/content accumulated
        if turns_since >= cls.MIN_TURNS_BETWEEN and total_chars_since >= cls.MIN_CHARS_BETWEEN:
            return SignalExtractionRules(
                should_extract=True,
                reason="accumulation_threshold",
                include_types=cls._get_types_for_content(content_lower)
            )

        # Default: don't extract
        return SignalExtractionRules(
            should_extract=False,
            reason="no_criteria_met",
            include_types=[]
        )

    @classmethod
    def _get_types_for_content(cls, content_lower: str) -> list:
        """
        Determine which signal types to extract based on content.
        Returns list of signal type names.
        """
        types = []

        # Check for assumption indicators
        if any(phrase in content_lower for phrase in ["assume", "assuming", "believe", "think"]):
            types.append("Assumption")

        # Check for question indicators
        if "?" in content_lower or any(phrase in content_lower for phrase in ["not sure", "uncertain"]):
            types.append("Question")

        # Check for constraint indicators
        if any(phrase in content_lower for phrase in ["must", "cannot", "can't", "requirement", "deadline", "budget"]):
            types.append("Constraint")

        # Check for goal indicators
        if any(phrase in content_lower for phrase in ["goal", "objective", "target", "want to"]):
            types.append("Goal")

        # Check for decision indicators
        if any(phrase in content_lower for phrase in ["decide", "decision", "chose", "choosing", "let's go"]):
            types.append("DecisionIntent")

        # Check for claim/evidence indicators
        if any(phrase in content_lower for phrase in ["fact", "evidence", "data", "according"]):
            types.append("Claim")

        # If no specific types detected, extract all common types
        if not types:
            types = ["Assumption", "Question", "Constraint", "Goal", "Claim"]

        return types

    @classmethod
    def get_thread_extraction_state(cls, thread) -> dict:
        """
        Get extraction state for a thread from metadata.

        Args:
            thread: ChatThread object

        Returns:
            Dict with last_extraction_turn, last_extraction_chars, total_chars_since
        """
        metadata = thread.metadata or {}
        extraction_state = metadata.get('extraction_state', {})

        return {
            'last_extraction_turn': extraction_state.get('last_turn'),
            'last_extraction_chars': extraction_state.get('last_chars'),
            'total_chars_since': extraction_state.get('chars_since', 0)
        }

    @classmethod
    def update_thread_extraction_state(
        cls,
        thread,
        current_turn: int,
        current_chars: int,
        extracted: bool
    ):
        """
        Update extraction state in thread metadata.

        Args:
            thread: ChatThread object
            current_turn: Current turn number
            current_chars: Total characters in thread
            extracted: Whether extraction was performed
        """
        metadata = thread.metadata or {}
        extraction_state = metadata.get('extraction_state', {})

        if extracted:
            extraction_state['last_turn'] = current_turn
            extraction_state['last_chars'] = current_chars
            extraction_state['chars_since'] = 0
        else:
            chars_since = extraction_state.get('chars_since', 0)
            last_chars = extraction_state.get('last_chars', 0)
            extraction_state['chars_since'] = chars_since + (current_chars - last_chars)

        metadata['extraction_state'] = extraction_state
        thread.metadata = metadata
        thread.save(update_fields=['metadata'])
