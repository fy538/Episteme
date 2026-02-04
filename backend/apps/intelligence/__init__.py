"""
Intelligence module - Unified analysis engine for chat, reflection, and signal extraction

Consolidates 4-5 separate LLM calls into a single unified call with sectioned streaming:
- <response> → Streams to Chat UI
- <reflection> → Streams to Companion UI
- <signals> → Buffered JSON, parsed and saved to DB
"""

from .engine import UnifiedAnalysisEngine
from .parser import SectionedStreamParser

__all__ = ['UnifiedAnalysisEngine', 'SectionedStreamParser']
