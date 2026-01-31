"""
Model resolution logic for PydanticAI.
Handles switching between different providers (OpenAI, DeepSeek, Groq, Anthropic).
"""
import os
from django.conf import settings
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.anthropic import AnthropicModel


def get_model(model_str: str):
    """
    Resolve a model string (e.g. 'deepseek:deepseek-chat') to a PydanticAI model instance.
    """
    provider, _, model_name = model_str.partition(':')
    if not model_name:
        # Fallback to provider as model name if no colon
        model_name = provider
        provider = 'openai' # Default to openai

    if provider == 'openai':
        return OpenAIModel(model_name, api_key=settings.OPENAI_API_KEY)
    
    elif provider == 'deepseek':
        return OpenAIModel(
            model_name, 
            base_url='https://api.deepseek.com', 
            api_key=settings.DEEPSEEK_API_KEY
        )
    
    elif provider == 'groq':
        return OpenAIModel(
            model_name, 
            base_url='https://api.groq.com/openai/v1', 
            api_key=settings.GROQ_API_KEY
        )
    
    elif provider == 'google' or provider == 'gemini':
        return GeminiModel(model_name, api_key=settings.GOOGLE_API_KEY)
    
    elif provider == 'anthropic':
        return AnthropicModel(model_name, api_key=settings.ANTHROPIC_API_KEY)
    
    # Default fallback
    return model_str
