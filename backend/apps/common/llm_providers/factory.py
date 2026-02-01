"""
LLM Provider Factory
"""
from django.conf import settings

from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider


def get_llm_provider(model_key: str = None) -> LLMProvider:
    """
    Get the appropriate LLM provider based on model key
    
    Args:
        model_key: Model key from settings.AI_MODELS (e.g., 'chat', 'fast')
                   If None, uses settings.AI_MODELS['chat']
    
    Returns:
        Initialized LLM provider instance
    
    Examples:
        # Use chat model (from settings)
        provider = get_llm_provider('chat')
        
        # Stream response
        async for chunk in provider.stream_chat(messages=[...]):
            print(chunk.content)
    """
    if model_key is None:
        model_key = 'chat'
    
    # Get model identifier from settings (e.g., "anthropic:claude-haiku-4-5")
    model_identifier = settings.AI_MODELS.get(model_key, settings.AI_MODELS['fast'])
    
    # Parse provider and model
    if ':' in model_identifier:
        provider_name, model_name = model_identifier.split(':', 1)
    else:
        # Default to OpenAI if no provider specified
        provider_name = 'openai'
        model_name = model_identifier
    
    # Instantiate the appropriate provider
    if provider_name == 'anthropic':
        api_key = settings.ANTHROPIC_API_KEY
        return AnthropicProvider(api_key=api_key, model=model_name)
    elif provider_name == 'openai':
        api_key = settings.OPENAI_API_KEY
        return OpenAIProvider(api_key=api_key, model=model_name)
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
