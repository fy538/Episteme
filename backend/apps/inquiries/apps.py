from django.apps import AppConfig


class InquiriesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inquiries'

    def ready(self):
        """Import signals when app is ready"""
        import apps.inquiries.signals  # noqa
