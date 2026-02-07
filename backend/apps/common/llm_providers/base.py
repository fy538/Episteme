"""
Base LLM Provider interface
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional


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
        content = ""
        async for chunk in self.stream_chat(
            messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        ):
            content += chunk.content
        return content
