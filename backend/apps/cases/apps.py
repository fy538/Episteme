from django.apps import AppConfig


class CasesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cases'

    def ready(self):
        # Register Django signal handlers for brief evolution triggers.
        # These listen for Signal/Evidence/Inquiry changes and schedule
        # async brief grounding recomputation via Celery.
        import apps.cases.brief_signals  # noqa: F401
