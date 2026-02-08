import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class SignalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.signals'

    def ready(self):
        """Register signal handlers when app is ready."""
        from django.db.models.signals import post_save
        from apps.signals.models import Signal

        def generate_embedding_on_save(sender, instance, created, **kwargs):
            """Generate embedding for new signals (async-safe)."""
            if created and not instance.embedding and instance.text:
                try:
                    from apps.common.embeddings import generate_embedding
                    embedding = generate_embedding(instance.text)
                    if embedding:
                        # Use update to avoid triggering save again
                        Signal.objects.filter(pk=instance.pk).update(embedding=embedding)
                except Exception as e:
                    # Don't fail the save if embedding fails
                    logger.warning(f"Failed to generate embedding for signal {instance.pk}: {e}")

        post_save.connect(generate_embedding_on_save, sender=Signal)

        # Listen for changes to Evidence.supports_signals and Evidence.contradicts_signals
        # to trigger assumption status cascade when evidence is linked/unlinked.
        from django.db.models.signals import m2m_changed
        from apps.signals.assumption_cascade import _on_evidence_m2m_changed
        from apps.projects.models import Evidence

        m2m_changed.connect(
            _on_evidence_m2m_changed,
            sender=Evidence.supports_signals.through,
        )
        m2m_changed.connect(
            _on_evidence_m2m_changed,
            sender=Evidence.contradicts_signals.through,
        )
