"""
Intelligence app configuration
"""

from django.apps import AppConfig


class IntelligenceConfig(AppConfig):
    """Configuration for intelligence app"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.intelligence'
    verbose_name = 'Intelligence'
