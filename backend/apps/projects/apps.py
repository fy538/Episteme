import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ProjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.projects'

    def ready(self):
        """Pre-warm the embedding model on app startup.

        Loads the sentence-transformers model into memory so the first
        document upload doesn't pay a 500ms-2s cold-start penalty.
        Runs in a background thread to avoid blocking app startup.
        """
        import threading

        def _prewarm():
            try:
                from apps.common.embeddings import _get_service
                _get_service()
            except Exception as e:
                logger.warning("Embedding service warm-up skipped: %s", e)

        threading.Thread(target=_prewarm, daemon=True).start()
