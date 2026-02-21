"""
Backfill ConversationEpisodes for existing threads.

Creates one episode per thread (spanning all messages), sealing threads
that haven't been active in 7+ days. Links messages to episodes and sets
thread.current_episode. After creating episodes, triggers embedding
backfill for structures and episodes.

Usage:
    python manage.py backfill_episodes                    # backfill all threads
    python manage.py backfill_episodes --batch-size 50    # custom batch size
    python manage.py backfill_episodes --dry-run           # show counts only
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Backfill ConversationEpisodes for existing threads. "
        "Creates one episode per thread, sealing inactive threads. "
        "Then backfills structure and episode embeddings."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help="Number of threads to process per batch (default: 100)",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Show counts of threads needing backfill without processing",
        )
        parser.add_argument(
            '--skip-embeddings',
            action='store_true',
            help="Skip embedding backfill after creating episodes",
        )

    def handle(self, *args, **options):
        from apps.chat.models import (
            ChatThread, ConversationStructure, ConversationEpisode, Message,
        )

        batch_size = options['batch_size']
        dry_run = options['dry_run']
        skip_embeddings = options['skip_embeddings']

        # Find threads that have structures but no episodes
        threads_with_structures = ChatThread.objects.filter(
            structures__isnull=False,
        ).exclude(
            episodes__isnull=False,
        ).distinct()

        total = threads_with_structures.count()

        if dry_run:
            self.stdout.write(f"\nThreads needing episode backfill: {total}")
            # Also show threads without structures (no episode needed)
            no_structure = ChatThread.objects.filter(
                structures__isnull=True,
            ).count()
            self.stdout.write(f"Threads without structures (skipped): {no_structure}")

            # Show embedding backfill needs
            structures_need_embed = ConversationStructure.objects.filter(
                embedding__isnull=True,
            ).exclude(context_summary='').count()
            self.stdout.write(f"Structures needing embeddings: {structures_need_embed}")
            return

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No threads need episode backfill."))
        else:
            self.stdout.write(f"\nBackfilling episodes for {total} threads...\n")

            cutoff = timezone.now() - timedelta(days=7)
            stats = {
                'processed': 0,
                'episodes_created': 0,
                'sealed': 0,
                'unsealed': 0,
                'messages_linked': 0,
            }

            offset = 0
            while offset < total:
                threads = list(
                    threads_with_structures[offset:offset + batch_size]
                )
                if not threads:
                    break

                for thread in threads:
                    try:
                        self._backfill_thread(
                            thread, cutoff, stats,
                            ConversationStructure, ConversationEpisode, Message,
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to backfill thread {thread.id}: {e}"
                        )

                offset += batch_size
                self.stdout.write(
                    f"  Processed {min(offset, total)}/{total} threads "
                    f"({stats['episodes_created']} episodes created)"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nEpisode backfill complete:\n"
                    f"  Threads processed: {stats['processed']}\n"
                    f"  Episodes created: {stats['episodes_created']}\n"
                    f"  Sealed (inactive): {stats['sealed']}\n"
                    f"  Unsealed (active): {stats['unsealed']}\n"
                    f"  Messages linked: {stats['messages_linked']}"
                )
            )

        # --- Embedding backfill ---
        if not skip_embeddings:
            self.stdout.write("\nBackfilling structure embeddings...")
            from apps.common.embedding_hooks import (
                backfill_structure_embeddings,
                backfill_episode_embeddings,
            )

            # Structure embeddings (also updates ChatThread.embedding)
            total_structure_stats = {'processed': 0, 'embedded': 0, 'failed': 0}
            batch_num = 0
            while True:
                batch_num += 1
                s_stats = backfill_structure_embeddings(
                    batch_size=batch_size, verbose=True
                )
                for k in total_structure_stats:
                    total_structure_stats[k] += s_stats[k]
                self.stdout.write(
                    f"  Structure batch {batch_num}: "
                    f"{s_stats['embedded']} embedded, {s_stats['failed']} failed"
                )
                if s_stats['processed'] < batch_size:
                    break

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Structures done: {total_structure_stats['embedded']} embedded"
                )
            )

            # Episode embeddings
            self.stdout.write("\nBackfilling episode embeddings...")
            total_episode_stats = {'processed': 0, 'embedded': 0, 'failed': 0}
            batch_num = 0
            while True:
                batch_num += 1
                e_stats = backfill_episode_embeddings(
                    batch_size=batch_size, verbose=True
                )
                for k in total_episode_stats:
                    total_episode_stats[k] += e_stats[k]
                self.stdout.write(
                    f"  Episode batch {batch_num}: "
                    f"{e_stats['embedded']} embedded, {e_stats['failed']} failed"
                )
                if e_stats['processed'] < batch_size:
                    break

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Episodes done: {total_episode_stats['embedded']} embedded"
                )
            )

        self.stdout.write(self.style.SUCCESS("\nAll done!"))

    def _backfill_thread(
        self, thread, cutoff, stats,
        ConversationStructure, ConversationEpisode, Message,
    ):
        """Create one episode for an existing thread."""
        # Get latest structure
        latest_structure = ConversationStructure.objects.filter(
            thread=thread
        ).order_by('-version').first()

        if not latest_structure:
            return

        # Get message range
        first_message = Message.objects.filter(
            thread=thread, content_type='text'
        ).order_by('created_at').first()

        last_message = Message.objects.filter(
            thread=thread, content_type='text'
        ).order_by('-created_at').first()

        msg_count = Message.objects.filter(
            thread=thread, content_type='text'
        ).count()

        if not first_message:
            return

        # Determine if thread is active or inactive
        is_active = thread.updated_at >= cutoff if thread.updated_at else False
        should_seal = not is_active

        # Create episode
        episode = ConversationEpisode.objects.create(
            thread=thread,
            episode_index=0,
            shift_type='initial',
            topic_label=thread.title[:200] if thread.title else '',
            content_summary=latest_structure.context_summary or '',
            start_message=first_message,
            end_message=last_message if should_seal else None,
            message_count=msg_count,
            reasoning_snapshot=latest_structure,
            sealed=should_seal,
            sealed_at=timezone.now() if should_seal else None,
        )

        stats['processed'] += 1
        stats['episodes_created'] += 1
        if should_seal:
            stats['sealed'] += 1
        else:
            stats['unsealed'] += 1

        # Link all messages to this episode
        linked = Message.objects.filter(
            thread=thread, episode__isnull=True,
        ).update(episode=episode)
        stats['messages_linked'] += linked

        # Set thread.current_episode
        thread.current_episode = episode
        thread.save(update_fields=['current_episode'])
