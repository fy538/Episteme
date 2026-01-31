"""
Management command to re-chunk documents with new chunking strategy

Usage:
    python manage.py rechunk_documents --strategy=recursive_token
    python manage.py rechunk_documents --document-id=<uuid>
    python manage.py rechunk_documents --all
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.projects.models import Document, DocumentChunk
from apps.projects.services import DocumentService


class Command(BaseCommand):
    help = 'Re-chunk documents with new chunking strategy'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--strategy',
            type=str,
            default='recursive_token',
            choices=['recursive_token', 'semantic', 'page_level'],
            help='Chunking strategy to use'
        )
        
        parser.add_argument(
            '--document-id',
            type=str,
            help='Re-chunk specific document by ID'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Re-chunk all documents'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be done without making changes'
        )
    
    def handle(self, *args, **options):
        strategy = options['strategy']
        document_id = options.get('document_id')
        all_docs = options.get('all')
        dry_run = options.get('dry_run')
        
        # Get documents to process
        if document_id:
            try:
                documents = [Document.objects.get(id=document_id)]
            except Document.DoesNotExist:
                raise CommandError(f'Document {document_id} does not exist')
        elif all_docs:
            documents = Document.objects.all()
        else:
            # Default: re-chunk documents with old chunking strategy
            documents = Document.objects.exclude(
                chunks__chunking_strategy=strategy
            ).distinct()
        
        total = len(documents)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would re-chunk {total} documents')
            )
            for doc in documents:
                self.stdout.write(f'  - {doc.title} ({doc.chunk_count} chunks)')
            return
        
        self.stdout.write(f'Re-chunking {total} documents with strategy: {strategy}')
        
        # Process each document
        success_count = 0
        error_count = 0
        
        for i, document in enumerate(documents, 1):
            self.stdout.write(f'[{i}/{total}] Processing: {document.title}')
            
            try:
                # Delete existing chunks
                old_chunk_count = document.chunks.count()
                document.chunks.all().delete()
                
                # Re-process document
                DocumentService.process_document(document)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Re-chunked: {old_chunk_count} → {document.chunk_count} chunks'
                    )
                )
                success_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error: {str(e)}')
                )
                error_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ Success: {success_count} documents'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'✗ Errors: {error_count} documents'))
        
        self.stdout.write('')
        self.stdout.write('Re-chunking complete!')
