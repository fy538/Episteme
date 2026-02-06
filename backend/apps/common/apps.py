from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'

    def ready(self):
        """Register signal handlers for embedding generation."""
        # Import signal handlers to register them
        # This ensures embeddings are auto-generated when Inquiry/Case models are saved
        from apps.common import embedding_hooks  # noqa: F401
