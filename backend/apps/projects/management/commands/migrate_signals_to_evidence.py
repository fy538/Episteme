"""
Management command to migrate document-sourced signals to evidence

This is a one-time migration to clean up the conceptual model:
- Signals should only come from USER chat
- Evidence should come from DOCUMENTS

Usage:
    python manage.py migrate_signals_to_evidence --dry-run
    python manage.py migrate_signals_to_evidence
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.signals.models import Signal, SignalSourceType
from apps.projects.models import Evidence, DocumentChunk


class Command(BaseCommand):
    help = 'Migrate document-sourced signals to evidence model'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be migrated without making changes'
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        
        # Find all signals sourced from documents
        document_signals = Signal.objects.filter(
            source_type=SignalSourceType.DOCUMENT
        ).select_related('document')
        
        total = document_signals.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No document-sourced signals found. Migration not needed.'))
            return
        
        self.stdout.write(f'Found {total} signals sourced from documents')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: Would migrate these signals to evidence'))
            for signal in document_signals[:10]:  # Show first 10
                self.stdout.write(f'  - {signal.type}: {signal.text[:50]}...')
            if total > 10:
                self.stdout.write(f'  ... and {total - 10} more')
            return
        
        # Perform migration
        self.stdout.write('Starting migration...')
        
        migrated_count = 0
        error_count = 0
        skipped_count = 0
        
        for signal in document_signals:
            try:
                with transaction.atomic():
                    # Map signal type to evidence type
                    evidence_type = self._map_signal_to_evidence_type(signal.type)
                    
                    if not evidence_type:
                        # Skip signals that don't map to evidence types
                        self.stdout.write(
                            self.style.WARNING(f'Skipping {signal.type} (no evidence mapping)')
                        )
                        skipped_count += 1
                        continue
                    
                    # Get chunk if available
                    chunk_id = signal.span.get('chunk_id') if signal.span else None
                    chunk = None
                    
                    if chunk_id:
                        try:
                            chunk = DocumentChunk.objects.get(id=chunk_id)
                        except DocumentChunk.DoesNotExist:
                            pass
                    
                    # If no chunk, try to find one from document and sequence
                    if not chunk and signal.document:
                        chunk = signal.document.chunks.filter(
                            chunk_index=signal.sequence_index
                        ).first()
                    
                    if not chunk:
                        self.stdout.write(
                            self.style.WARNING(f'No chunk found for signal {signal.id}')
                        )
                        skipped_count += 1
                        continue
                    
                    # Create evidence
                    Evidence.objects.create(
                        text=signal.text,
                        type=evidence_type,
                        chunk=chunk,
                        document=signal.document,
                        extraction_confidence=signal.confidence,
                        embedding=signal.embedding,
                    )
                    
                    # Delete the signal (it shouldn't have been a signal)
                    signal.delete()
                    
                    migrated_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating signal {signal.id}: {str(e)}')
                )
                error_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ Migrated: {migrated_count} signals → evidence'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'⊘ Skipped: {skipped_count} signals'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'✗ Errors: {error_count} signals'))
        
        self.stdout.write('')
        self.stdout.write('Migration complete!')
    
    def _map_signal_to_evidence_type(self, signal_type: str) -> str:
        """Map signal types to evidence types"""
        
        mapping = {
            'Claim': 'claim',
            'EvidenceMention': 'fact',
            'Goal': 'claim',  # Goals in documents are claims
        }
        
        # Signal types that shouldn't become evidence
        skip_types = [
            'Assumption',  # User assumptions shouldn't come from docs
            'Question',    # User questions shouldn't come from docs
            'Constraint',  # User constraints shouldn't come from docs
            'DecisionIntent',  # User decisions shouldn't come from docs
        ]
        
        if signal_type in skip_types:
            return None
        
        return mapping.get(signal_type, 'claim')
