"""
OpenAI LLM Provider
"""
from typing import AsyncIterator, Optional
from openai import AsyncOpenAI

from .base import LLMProvider, StreamChunk


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        super().__init__(api_key, model)
        self.client = AsyncOpenAI(api_key=api_key)

    async def stream_chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """Stream chat completion from OpenAI"""

        # Prepare messages with system prompt
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        openai_messages.extend(messages)

        # Stream from OpenAI
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            stream=True,
            **kwargs
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield StreamChunk(
                    content=chunk.choices[0].delta.content,
                    finish_reason=chunk.choices[0].finish_reason
                )

    async def generate(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Non-streaming chat completion from OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            model: Optional model override
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text content
        """
        if not messages:
            raise ValueError("At least one message is required")

        use_model = model or self.model

        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        openai_messages.extend(messages)

        response = await self.client.chat.completions.create(
            model=use_model,
            messages=openai_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        return ""
