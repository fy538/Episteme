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
        use_prompt_caching: bool = True,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream chat completion from Anthropic with optional prompt caching.
        
        Prompt caching can reduce TTFT by 75-85% and costs by 90% for repeated contexts.
        Cache reads cost only 10% of base input token price.
        """
        
        # Anthropic requires at least one message
        if not messages:
            raise ValueError("At least one message is required for Anthropic API")
        
        # Anthropic uses separate system parameter
        max_tokens = kwargs.pop('max_tokens', 4096)
        
        # Enable prompt caching for system prompts (ephemeral cache, 5 min TTL)
        # Reduces TTFT by 75-85% for repeated contexts!
        # Only use caching if we have a substantial system prompt (>100 chars)
        if use_prompt_caching and system_prompt and len(system_prompt) > 100:
            system_param = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        else:
            # Use string format for short prompts or when caching disabled
            system_param = system_prompt or ""
        
        # Stream from Anthropic
        async with self.client.messages.stream(
            model=self.model,
            messages=messages,
            system=system_param,
            max_tokens=max_tokens,
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(content=text)

    async def generate(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        use_prompt_caching: bool = True,
        **kwargs
    ) -> str:
        """
        Non-streaming chat completion from Anthropic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            model: Optional model override
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            use_prompt_caching: Enable ephemeral prompt caching (default True).
                Cache reads cost 10% of base input price; writes cost 1.25x.

        Returns:
            Generated text content
        """
        if not messages:
            raise ValueError("At least one message is required")

        use_model = model or self.model

        # Enable prompt caching for system prompts (ephemeral cache, 5 min TTL)
        # Matches stream_chat() caching pattern — reduces cost by ~90% on cache hits.
        if use_prompt_caching and system_prompt and len(system_prompt) > 100:
            system_param = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            system_param = system_prompt or ""

        response = await self.client.messages.create(
            model=use_model,
            messages=messages,
            system=system_param,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        # Extract text from response
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return ""
