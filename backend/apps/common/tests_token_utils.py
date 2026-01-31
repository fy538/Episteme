"""
Tests for token utilities
"""
from django.test import TestCase
from apps.common.token_utils import count_tokens, chunk_by_tokens, split_text_to_fit_tokens


class TokenUtilsTest(TestCase):
    """Test token counting utilities"""
    
    def test_count_tokens_basic(self):
        """Test basic token counting"""
        text = "Hello, world!"
        tokens = count_tokens(text)
        
        # Should be 3-4 tokens
        self.assertGreater(tokens, 0)
        self.assertLess(tokens, 10)
    
    def test_count_tokens_long_text(self):
        """Test token counting on longer text"""
        text = "This is a longer sentence with more words. " * 20
        tokens = count_tokens(text)
        
        # Should be substantial
        self.assertGreater(tokens, 100)
    
    def test_chunk_by_tokens_single_chunk(self):
        """Test chunking text that fits in one chunk"""
        text = "Short text."
        chunks = chunk_by_tokens(text, max_tokens=100)
        
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0][0], text)
    
    def test_chunk_by_tokens_multiple_chunks(self):
        """Test chunking text into multiple chunks"""
        text = "Word " * 500  # ~500 tokens
        chunks = chunk_by_tokens(text, max_tokens=256, overlap_tokens=50)
        
        # Should create multiple chunks
        self.assertGreater(len(chunks), 1)
        
        # Verify each chunk is within limits
        for chunk_text, start, end in chunks:
            tokens = count_tokens(chunk_text)
            self.assertLessEqual(tokens, 260)  # Small buffer
            self.assertGreater(tokens, 50)  # Min size
    
    def test_chunk_overlap(self):
        """Test that chunks have correct overlap"""
        text = "Word " * 500
        chunks = chunk_by_tokens(text, max_tokens=256, overlap_tokens=50)
        
        if len(chunks) > 1:
            # Check overlap exists
            _, start_0, end_0 = chunks[0]
            _, start_1, end_1 = chunks[1]
            
            # Second chunk should start before first chunk ends (overlap)
            self.assertLess(start_1, end_0)
            
            # Overlap should be approximately 50 tokens
            overlap = end_0 - start_1
            self.assertGreater(overlap, 30)
            self.assertLess(overlap, 70)
    
    def test_split_text_to_fit_tokens(self):
        """Test truncating text to fit token limit"""
        text = "Word " * 500
        truncated = split_text_to_fit_tokens(text, max_tokens=100)
        
        # Verify truncated text fits
        tokens = count_tokens(truncated)
        self.assertLessEqual(tokens, 100)
        
        # Should be shorter than original
        self.assertLess(len(truncated), len(text))
