"""
Anthropic (Claude) LLM Provider
"""
from typing import AsyncIterator, Optional
from anthropic import AsyncAnthropic

from .base import LLMProvider, StreamChunk


class AnthropicProvider(LLMProvider):
    """Anthropic Claude implementation of LLM provider"""
    
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5"):
        super().__init__(api_key, model)
        self.client = AsyncAnthropic(api_key=api_key)
    
    async def stream_chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """Stream chat completion from Anthropic"""
        
        # Anthropic uses separate system parameter
        max_tokens = kwargs.pop('max_tokens', 4096)
        
        # Stream from Anthropic
        async with self.client.messages.stream(
            model=self.model,
            messages=messages,
            system=system_prompt or "",
            max_tokens=max_tokens,
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(content=text)
