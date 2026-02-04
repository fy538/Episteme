from django.apps import AppConfig


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
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Failed to generate embedding for signal {instance.pk}: {e}"
                    )

        post_save.connect(generate_embedding_on_save, sender=Signal)
