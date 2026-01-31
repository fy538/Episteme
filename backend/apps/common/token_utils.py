"""
Token counting utilities using tiktoken

Based on 2024 RAG research:
- Token-based chunking (256-512 tokens) outperforms character-based
- Accurate token counting essential for LLM context management
"""
import tiktoken
from typing import List, Tuple


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text using tiktoken
    
    Args:
        text: Text to count tokens in
        model: Model name (determines encoding)
            - "gpt-4", "gpt-4o", "gpt-3.5-turbo" → cl100k_base
            - "text-embedding-ada-002" → cl100k_base
    
    Returns:
        Number of tokens
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base (GPT-4 encoding)
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))


def chunk_by_tokens(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 0,
    encoding_name: str = "cl100k_base"
) -> List[Tuple[str, int, int]]:
    """
    Split text into token-based chunks with overlap
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk (256-512 recommended)
        overlap_tokens: Overlap between chunks (0.10-0.20 of max_tokens)
        encoding_name: Tiktoken encoding name
    
    Returns:
        List of (chunk_text, start_token, end_token) tuples
    """
    encoding = tiktoken.get_encoding(encoding_name)
    
    # Encode entire text
    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        # Text fits in one chunk
        return [(text, 0, len(tokens))]
    
    chunks = []
    start = 0
    
    while start < len(tokens):
        # Define chunk window
        end = min(start + max_tokens, len(tokens))
        
        # Extract tokens and decode
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        
        chunks.append((chunk_text, start, end))
        
        # Move start forward by (max_tokens - overlap_tokens)
        if end >= len(tokens):
            break
        
        start = end - overlap_tokens
    
    return chunks


def estimate_char_to_token_ratio(text: str, encoding_name: str = "cl100k_base") -> float:
    """
    Estimate character-to-token ratio for a text
    
    Useful for quick estimation without full tokenization.
    Average English text: ~4 chars per token
    
    Args:
        text: Sample text
        encoding_name: Tiktoken encoding
    
    Returns:
        Ratio of characters to tokens
    """
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)
    
    if len(tokens) == 0:
        return 4.0  # Default estimate
    
    return len(text) / len(tokens)


def split_text_to_fit_tokens(
    text: str,
    max_tokens: int,
    encoding_name: str = "cl100k_base"
) -> str:
    """
    Truncate text to fit within token limit
    
    Args:
        text: Text to truncate
        max_tokens: Maximum tokens allowed
        encoding_name: Tiktoken encoding
    
    Returns:
        Truncated text
    """
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        return text
    
    # Truncate tokens and decode
    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)
