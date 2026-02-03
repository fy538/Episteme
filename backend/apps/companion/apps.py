from django.apps import AppConfig


class CompanionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.companion'
    verbose_name = 'Companion'
    
    def ready(self):
        # Import signal handlers
        import apps.companion.signals  # noqa
