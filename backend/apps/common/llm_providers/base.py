"""
Base LLM Provider interface
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional


@dataclass
class StreamChunk:
    """Standardized chunk format across providers"""
    content: str
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    # Default context window sizes per model family (tokens).
    # Subclasses or instances can override.
    MODEL_CONTEXT_WINDOWS: dict[str, int] = {
        "claude-haiku-4-5": 200_000,
        "claude-sonnet-4-5": 200_000,
        "claude-opus-4-6": 200_000,
        "gpt-4o-mini": 128_000,
        "gpt-4o": 128_000,
    }
    DEFAULT_CONTEXT_WINDOW = 128_000

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @property
    def context_window_tokens(self) -> int:
        """Return the context window size for this provider's model."""
        return self.MODEL_CONTEXT_WINDOWS.get(self.model, self.DEFAULT_CONTEXT_WINDOW)

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream chat completion chunks

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Yields:
            StreamChunk objects with incremental content
        """
        pass

    async def generate(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Non-streaming chat completion. Returns full response text.

        Default implementation collects stream chunks. Providers may override
        with a native non-streaming call for better performance.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific options

        Returns:
            Generated text content
        """
        chunks = []
        async for chunk in self.stream_chat(
            messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        ):
            chunks.append(chunk.content)
        return ''.join(chunks)

    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 0.2,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response using tool_use / function calling for structured output.

        Each tool dict follows the Anthropic format:
        {
            "name": "tool_name",
            "description": "...",
            "input_schema": { JSON Schema }
        }

        Returns the parsed tool input dict directly (the structured data),
        or falls back to text generation + JSON parsing.

        Returns:
            Parsed dict from tool_use, or {} if extraction failed.
        """
        # Default fallback: call generate() and parse JSON from response
        import json
        import re

        response = await self.generate(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        # Try to parse JSON from the response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        # Try code fence extraction
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        return {}
