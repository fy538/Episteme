"""
OpenAI LLM Provider
"""
import json
from typing import Any, AsyncIterator, Dict, List, Optional
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
        Structured output via OpenAI function calling.

        Converts Anthropic-style tool schema to OpenAI function format,
        forces the function call, then extracts parsed arguments.
        """
        if not messages:
            raise ValueError("At least one message is required")
        if not tools:
            return await super().generate_with_tools(
                messages, tools, system_prompt, max_tokens, temperature, **kwargs
            )

        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        openai_messages.extend(messages)

        # Convert Anthropic tool format → OpenAI function format
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            }
            for t in tools
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=openai_tools,
            tool_choice={"type": "function", "function": {"name": tools[0]["name"]}},
            **kwargs,
        )

        # Extract function call arguments
        choice = response.choices[0] if response.choices else None
        if choice and choice.message.tool_calls:
            call = choice.message.tool_calls[0]
            try:
                return json.loads(call.function.arguments)
            except json.JSONDecodeError:
                pass

        return {}
