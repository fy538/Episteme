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
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
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
