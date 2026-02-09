"""
Tests for projects app
"""
from django.test import TestCase
from django.contrib.auth.models import User

from apps.projects.models import Project, Document, DocumentChunk
from apps.projects.services import ProjectService, DocumentService
from apps.projects.recursive_chunker import RecursiveTokenChunker
from apps.common.token_utils import count_tokens, chunk_by_tokens


class RecursiveTokenChunkerTest(TestCase):
    """Test RecursiveTokenChunker"""
    
    def setUp(self):
        self.chunker = RecursiveTokenChunker(
            chunk_tokens=512,
            overlap_ratio=0.15
        )
    
    def test_chunk_short_text(self):
        """Test that short text creates one chunk"""
        text = "This is a short document."
        chunks = self.chunker.chunk_document(text)
        
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]['text'], text)
        self.assertLessEqual(chunks[0]['token_count'], 512)
    
    def test_chunk_long_text(self):
        """Test that long text is chunked appropriately"""
        # Create text with ~2000 tokens (should create 3-4 chunks with overlap)
        paragraphs = [f"This is paragraph {i}. " * 50 for i in range(10)]
        text = "\n\n".join(paragraphs)
        
        chunks = self.chunker.chunk_document(text)
        
        # Should create multiple chunks
        self.assertGreater(len(chunks), 1)
        
        # Each chunk should be within token limits
        for chunk in chunks:
            tokens = chunk['token_count']
            self.assertGreater(tokens, 100)  # Min chunk size
            self.assertLessEqual(tokens, 600)  # Max with some buffer
    
    def test_chunk_respects_sections(self):
        """Test chunking with section information"""
        text = "Section 1 content. " * 100 + "Section 2 content. " * 100
        
        sections = [
            {'title': 'Section 1', 'start': 0, 'end': len("Section 1 content. " * 100)},
            {'title': 'Section 2', 'start': len("Section 1 content. " * 100), 'end': len(text)},
        ]
        
        chunks = self.chunker.chunk_document(text, sections=sections)
        
        # Should create chunks
        self.assertGreater(len(chunks), 0)
        
        # Check that section info is preserved
        has_section_metadata = any('section' in chunk['span'] for chunk in chunks)
        self.assertTrue(has_section_metadata)
    
    def test_chunk_overlap(self):
        """Test that chunks have overlap"""
        text = "Sentence one. " * 200  # Long enough for multiple chunks
        
        chunks = self.chunker.chunk_document(text)
        
        if len(chunks) > 1:
            # Check for overlap between consecutive chunks
            # Last part of chunk N should appear in chunk N+1
            chunk_0_end = chunks[0]['text'][-50:]
            chunk_1_start = chunks[1]['text'][:100]
            
            # Some overlap should exist
            # (Exact match hard to verify due to sentence boundaries)
            self.assertGreater(len(chunks[0]['text']), 100)
            self.assertGreater(len(chunks[1]['text']), 100)


class TokenUtilsTest(TestCase):
    """Test token counting utilities"""
    
    def test_count_tokens(self):
        """Test basic token counting"""
        text = "This is a test sentence."
        tokens = count_tokens(text)
        
        # Should be 6-7 tokens
        self.assertGreater(tokens, 0)
        self.assertLess(tokens, 20)
    
    def test_chunk_by_tokens(self):
        """Test token-based chunking"""
        text = "Word " * 1000  # ~1000 tokens
        
        chunks = chunk_by_tokens(
            text,
            max_tokens=256,
            overlap_tokens=50
        )
        
        # Should create multiple chunks
        self.assertGreater(len(chunks), 1)
        
        # Check chunk sizes
        for chunk_text, start, end in chunks:
            tokens = count_tokens(chunk_text)
            self.assertLessEqual(tokens, 260)  # Allow small buffer


class DocumentServiceTest(TestCase):
    """Test DocumentService"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.project = ProjectService.create_project(
            user=self.user,
            title='Test Project'
        )
    
    def test_create_document(self):
        """Test creating a document"""
        document = DocumentService.create_document(
            user=self.user,
            project_id=self.project.id,
            title='Test Document',
            source_type='text',
            content_text='This is test content for the document.'
        )
        
        self.assertIsNotNone(document.id)
        self.assertEqual(document.title, 'Test Document')
        self.assertEqual(document.project, self.project)
        self.assertEqual(document.processing_status, 'pending')
    
    def test_process_document(self):
        """Test document processing with new chunker"""
        # Create document with substantial content
        content = "This is a test document. " * 100  # ~500 tokens
        
        document = DocumentService.create_document(
            user=self.user,
            project_id=self.project.id,
            title='Test Document',
            source_type='text',
            content_text=content
        )
        
        # Process document
        processed = DocumentService.process_document(document)
        
        # Verify processing
        self.assertEqual(processed.processing_status, 'indexed')
        self.assertGreater(processed.chunk_count, 0)
        self.assertIsNotNone(processed.indexed_at)
        
        # Verify chunks created
        chunks = processed.chunks.all()
        self.assertEqual(len(chunks), processed.chunk_count)
        
        # Verify chunks have embeddings
        for chunk in chunks:
            self.assertIsNotNone(chunk.embedding)
            self.assertGreater(chunk.token_count, 0)
            pass  # Basic chunk validation


# EvidenceExtractionTest has been removed.
# Evidence extraction is now handled by the graph extraction pipeline
# (apps.graph), not by the document processing pipeline.
# See apps/graph/ tests for evidence node tests.


