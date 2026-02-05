"""
Management command to migrate embeddings from JSON to pgvector.

Usage:
    python manage.py migrate_to_pgvector --check        # Check if pgvector is available
    python manage.py migrate_to_pgvector --setup       # Set up pgvector column and index
    python manage.py migrate_to_pgvector --migrate     # Migrate embeddings
    python manage.py migrate_to_pgvector --all         # Do everything
"""
from django.core.management.base import BaseCommand
from apps.common.embedding_service import EmbeddingService, PgVectorBackend


class Command(BaseCommand):
    help = 'Migrate embeddings from JSON to pgvector'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check if pgvector extension is available',
        )
        parser.add_argument(
            '--setup',
            action='store_true',
            help='Set up pgvector column and HNSW index',
        )
        parser.add_argument(
            '--migrate',
            action='store_true',
            help='Migrate embeddings from JSON to vector column',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all steps: check, setup, migrate',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for migration (default: 1000)',
        )

    def handle(self, *args, **options):
        if options['all']:
            options['check'] = True
            options['setup'] = True
            options['migrate'] = True

        if not any([options['check'], options['setup'], options['migrate']]):
            self.stdout.write(self.style.WARNING(
                'No action specified. Use --check, --setup, --migrate, or --all'
            ))
            return

        backend = PgVectorBackend()

        # Check pgvector availability
        if options['check']:
            self.stdout.write('Checking pgvector extension...')
            if backend.extension_available:
                self.stdout.write(self.style.SUCCESS('pgvector extension is available'))
            else:
                self.stdout.write(self.style.ERROR(
                    'pgvector extension is NOT available.\n'
                    'Install it in PostgreSQL with: CREATE EXTENSION vector;'
                ))
                return

        # Set up column and index
        if options['setup']:
            self.stdout.write('Setting up pgvector column and index...')
            try:
                if backend.ensure_setup():
                    self.stdout.write(self.style.SUCCESS(
                        'Successfully set up embedding_vector column and HNSW index'
                    ))
                else:
                    self.stdout.write(self.style.ERROR('Failed to set up pgvector'))
                    return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error during setup: {e}'))
                return

        # Migrate embeddings
        if options['migrate']:
            self.stdout.write(f'Migrating embeddings (batch size: {options["batch_size"]})...')
            total_migrated = 0
            batch_size = options['batch_size']

            while True:
                try:
                    migrated = backend.migrate_from_json(batch_size=batch_size)
                    total_migrated += migrated
                    self.stdout.write(f'  Migrated {migrated} chunks (total: {total_migrated})')

                    if migrated < batch_size:
                        # No more chunks to migrate
                        break

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error during migration: {e}'))
                    break

            self.stdout.write(self.style.SUCCESS(
                f'Migration complete. Total migrated: {total_migrated} chunks'
            ))
