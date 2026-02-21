"""
Backfill embeddings for all searchable models.

Usage:
    python manage.py backfill_embeddings                     # backfill all models
    python manage.py backfill_embeddings --model case        # backfill cases only
    python manage.py backfill_embeddings --model all --batch-size 50
    python manage.py backfill_embeddings --dry-run            # show counts only
"""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# Registry of model → backfill function
MODEL_REGISTRY = {
    'inquiry': {
        'label': 'Inquiry',
        'func': 'backfill_inquiry_embeddings',
    },
    'case': {
        'label': 'Case',
        'func': 'backfill_case_embeddings',
    },
    'decision': {
        'label': 'DecisionRecord',
        'func': 'backfill_decision_embeddings',
    },
    'insight': {
        'label': 'ProjectInsight',
        'func': 'backfill_insight_embeddings',
    },
    'research': {
        'label': 'ResearchResult',
        'func': 'backfill_research_embeddings',
    },
    'structure': {
        'label': 'ConversationStructure',
        'func': 'backfill_structure_embeddings',
    },
    'episode': {
        'label': 'ConversationEpisode',
        'func': 'backfill_episode_embeddings',
    },
}


class Command(BaseCommand):
    help = "Backfill embeddings for searchable models (Case, Inquiry, Decision, Insight, Research, Structure, Episode)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            choices=list(MODEL_REGISTRY.keys()) + ['all'],
            default='all',
            help="Which model(s) to backfill (default: all)",
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help="Number of records per batch (default: 100)",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Show counts of records needing backfill without processing",
        )

    def handle(self, *args, **options):
        model_key = options['model']
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        models_to_process = (
            list(MODEL_REGISTRY.keys()) if model_key == 'all'
            else [model_key]
        )

        if dry_run:
            self._show_counts(models_to_process)
            return

        total_stats = {'processed': 0, 'embedded': 0, 'failed': 0}

        for key in models_to_process:
            entry = MODEL_REGISTRY[key]
            label = entry['label']
            func_name = entry['func']

            self.stdout.write(f"\nBackfilling {label}...")

            from apps.common import embedding_hooks
            backfill_func = getattr(embedding_hooks, func_name)

            # Run in batches until no more records need backfill
            batch_num = 0
            while True:
                batch_num += 1
                stats = backfill_func(batch_size=batch_size, verbose=True)

                total_stats['processed'] += stats['processed']
                total_stats['embedded'] += stats['embedded']
                total_stats['failed'] += stats['failed']

                self.stdout.write(
                    f"  Batch {batch_num}: "
                    f"{stats['embedded']} embedded, "
                    f"{stats['failed']} failed"
                )

                # Stop when batch returned fewer than batch_size
                if stats['processed'] < batch_size:
                    break

            self.stdout.write(self.style.SUCCESS(f"  {label} done."))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTotal: {total_stats['embedded']} embedded, "
                f"{total_stats['failed']} failed, "
                f"{total_stats['processed']} processed"
            )
        )

    def _show_counts(self, model_keys):
        """Show how many records need backfill for each model."""
        self.stdout.write("\nRecords needing embedding backfill:\n")

        counts = {
            'inquiry': lambda: self._count('inquiries.Inquiry'),
            'case': lambda: self._count('cases.Case'),
            'decision': lambda: self._count('cases.DecisionRecord'),
            'insight': lambda: self._count('graph.ProjectInsight'),
            'research': lambda: self._count_research(),
            'structure': lambda: self._count_structure(),
            'episode': lambda: self._count_episode(),
        }

        for key in model_keys:
            label = MODEL_REGISTRY[key]['label']
            count = counts[key]()
            self.stdout.write(f"  {label}: {count}")

    def _count(self, model_path):
        """Count records with null embeddings."""
        from django.apps import apps
        app_label, model_name = model_path.split('.')
        Model = apps.get_model(app_label, model_name)
        return Model.objects.filter(embedding__isnull=True).count()

    def _count_research(self):
        """Count completed research results with null embeddings."""
        from apps.chat.models import ResearchResult
        return ResearchResult.objects.filter(
            status='complete',
            embedding__isnull=True,
        ).count()

    def _count_structure(self):
        """Count conversation structures with null embeddings."""
        from apps.chat.models import ConversationStructure
        return ConversationStructure.objects.filter(
            embedding__isnull=True,
        ).exclude(context_summary='').count()

    def _count_episode(self):
        """Count sealed conversation episodes with null embeddings."""
        from apps.chat.models import ConversationEpisode
        return ConversationEpisode.objects.filter(
            sealed=True,
            embedding__isnull=True,
        ).exclude(content_summary='').count()
