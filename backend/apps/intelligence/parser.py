"""
Sectioned Stream Parser - Handles XML-style markers in streaming LLM output

Detects markers like <response>, </response>, etc. and routes content appropriately.
Handles markers split across token boundaries.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class Section(Enum):
    """Possible sections in the unified response"""
    NONE = "none"
    RESPONSE = "response"
    REFLECTION = "reflection"
    SIGNALS = "signals"
    ACTION_HINTS = "action_hints"


@dataclass
class ParsedChunk:
    """Result of parsing a chunk"""
    section: Section
    content: str
    is_complete: bool = False  # True when closing tag detected


class SectionedStreamParser:
    """
    Parser for sectioned streaming output.

    Handles the unified response format:
    <response>...</response>
    <reflection>...</reflection>
    <signals>[...]</signals>

    Features:
    - Detects XML-style markers even when split across chunks
    - Routes streaming sections immediately
    - Buffers JSON sections until complete
    """

    # Markers to detect
    MARKERS = [
        '<response>', '</response>',
        '<reflection>', '</reflection>',
        '<signals>', '</signals>',
        '<action_hints>', '</action_hints>'
    ]

    # Maximum marker length for buffer safety
    MAX_MARKER_LEN = max(len(m) for m in MARKERS)

    def __init__(self):
        self.current_section = Section.NONE
        self.buffer = ""
        self.signals_buffer = ""
        self.action_hints_buffer = ""

    def parse(self, chunk: str) -> List[ParsedChunk]:
        """
        Parse a chunk and return list of parsed chunks with section info.

        Args:
            chunk: Raw text chunk from LLM

        Returns:
            List of ParsedChunk objects with section and content
        """
        results = []

        # Add to buffer
        self.buffer += chunk

        while True:
            # Try to find any marker in buffer
            marker_match = self._find_next_marker()

            if marker_match is None:
                # No complete marker found
                # Emit content up to potential partial marker
                safe_content = self._get_safe_content()
                if safe_content:
                    results.append(self._create_chunk(safe_content))
                break

            marker, start, end = marker_match

            # Emit content before marker
            if start > 0:
                content_before = self.buffer[:start]
                if content_before:
                    results.append(self._create_chunk(content_before))

            # Process the marker
            if marker.startswith('</'):
                # Closing tag
                section_name = marker[2:-1]  # Extract section name
                section = self._get_section(section_name)

                if section == self.current_section:
                    # Emit completion marker
                    results.append(ParsedChunk(
                        section=section,
                        content="",
                        is_complete=True
                    ))
                    self.current_section = Section.NONE
            else:
                # Opening tag
                section_name = marker[1:-1]
                self.current_section = self._get_section(section_name)

                # Reset buffers on new JSON sections
                if self.current_section == Section.SIGNALS:
                    self.signals_buffer = ""
                elif self.current_section == Section.ACTION_HINTS:
                    self.action_hints_buffer = ""

            # Remove processed portion from buffer
            self.buffer = self.buffer[end:]

        return results

    def _find_next_marker(self) -> Optional[tuple]:
        """
        Find the next complete marker in buffer.

        Returns:
            Tuple of (marker, start_index, end_index) or None
        """
        best_match = None

        for marker in self.MARKERS:
            idx = self.buffer.find(marker)
            if idx >= 0:
                if best_match is None or idx < best_match[1]:
                    best_match = (marker, idx, idx + len(marker))

        return best_match

    def _get_safe_content(self) -> str:
        """
        Get content that's safe to emit (not potentially part of a marker).

        Returns:
            Safe content string, updating buffer
        """
        if len(self.buffer) <= self.MAX_MARKER_LEN:
            # Buffer is too short, might contain partial marker
            # Check if it starts with '<' which could be a partial marker
            if '<' in self.buffer:
                # Only emit content before the '<'
                idx = self.buffer.find('<')
                if idx > 0:
                    content = self.buffer[:idx]
                    self.buffer = self.buffer[idx:]
                    return content
                return ""
            else:
                # No '<' means safe to emit
                content = self.buffer
                self.buffer = ""
                return content
        else:
            # Buffer is long enough - keep only potential marker portion
            content = self.buffer[:-self.MAX_MARKER_LEN]
            self.buffer = self.buffer[-self.MAX_MARKER_LEN:]

            # But if there's a '<' in what we're emitting, only emit up to it
            if '<' in content:
                idx = content.rfind('<')
                # Check if this '<' could be start of a marker
                remaining = content[idx:] + self.buffer
                could_be_marker = any(remaining.startswith(m[:len(remaining)]) for m in self.MARKERS if m.startswith('<'))
                if could_be_marker:
                    self.buffer = content[idx:] + self.buffer
                    content = content[:idx]

            return content

    def _get_section(self, name: str) -> Section:
        """Convert section name to Section enum"""
        name = name.lower()
        if name == 'response':
            return Section.RESPONSE
        elif name == 'reflection':
            return Section.REFLECTION
        elif name == 'signals':
            return Section.SIGNALS
        elif name == 'action_hints':
            return Section.ACTION_HINTS
        return Section.NONE

    def _create_chunk(self, content: str) -> ParsedChunk:
        """Create a ParsedChunk for current section"""
        # For JSON sections, accumulate in buffer
        if self.current_section == Section.SIGNALS:
            self.signals_buffer += content
        elif self.current_section == Section.ACTION_HINTS:
            self.action_hints_buffer += content

        return ParsedChunk(
            section=self.current_section,
            content=content,
            is_complete=False
        )

    def get_signals_buffer(self) -> str:
        """Get accumulated signals content for JSON parsing"""
        return self.signals_buffer

    def get_action_hints_buffer(self) -> str:
        """Get accumulated action hints content for JSON parsing"""
        return self.action_hints_buffer

    def flush(self) -> List[ParsedChunk]:
        """
        Flush any remaining content in buffer.
        Call when stream ends.
        """
        results = []
        if self.buffer:
            # Use _create_chunk to properly update signals_buffer if in SIGNALS section
            results.append(self._create_chunk(self.buffer))
            self.buffer = ""
        return results
