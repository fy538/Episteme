"""
User authentication and preferences models
"""
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserPreferences(models.Model):
    """
    User preferences and settings
    
    Stores all user-configurable options for workspace, AI, appearance, etc.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferences',
        primary_key=True
    )
    
    # Workspace preferences
    default_case_view = models.CharField(
        max_length=20,
        choices=[
            ('brief', 'Brief'),
            ('dashboard', 'Dashboard'),
            ('documents', 'Documents')
        ],
        default='brief',
        help_text="Default view when opening a case"
    )
    
    auto_save_delay_ms = models.IntegerField(
        default=1000,
        help_text="Delay in milliseconds before auto-saving (1000 = 1 second)"
    )
    
    # Case creation preferences
    auto_create_inquiries = models.BooleanField(
        default=True,
        help_text="Auto-create inquiries from conversation questions"
    )
    
    auto_detect_assumptions = models.BooleanField(
        default=True,
        help_text="Auto-detect assumptions in conversations"
    )
    
    auto_generate_titles = models.BooleanField(
        default=True,
        help_text="Auto-generate titles for cases and inquiries"
    )
    
    # AI/Agent preferences
    chat_model = models.CharField(
        max_length=100,
        default='anthropic:claude-haiku-4-5',
        help_text="Preferred model for chat conversations"
    )
    
    agent_check_interval = models.IntegerField(
        default=3,
        help_text="Check for agent inflection points every N turns"
    )
    
    agent_min_confidence = models.FloatField(
        default=0.75,
        help_text="Minimum confidence to suggest agents (0.0-1.0)"
    )
    
    agent_auto_run = models.BooleanField(
        default=False,
        help_text="Auto-run agents when confidence is very high (>0.95)"
    )
    
    # Evidence preferences
    evidence_min_credibility = models.IntegerField(
        default=3,
        help_text="Minimum credibility rating for resolution (1-5 stars)"
    )
    
    # Appearance preferences
    theme = models.CharField(
        max_length=10,
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('auto', 'Auto (system)')
        ],
        default='light',
        help_text="UI theme"
    )
    
    font_size = models.CharField(
        max_length=10,
        choices=[
            ('small', 'Small'),
            ('medium', 'Medium'),
            ('large', 'Large')
        ],
        default='medium',
        help_text="Editor font size"
    )
    
    density = models.CharField(
        max_length=15,  # 'comfortable' is 11 chars
        choices=[
            ('compact', 'Compact'),
            ('comfortable', 'Comfortable'),
            ('relaxed', 'Relaxed')
        ],
        default='comfortable',
        help_text="UI spacing density"
    )
    
    # Notification preferences
    email_notifications = models.BooleanField(
        default=False,
        help_text="Enable email notifications"
    )
    
    notify_on_inquiry_resolved = models.BooleanField(
        default=True,
        help_text="Notify when inquiry is resolved"
    )
    
    notify_on_agent_complete = models.BooleanField(
        default=True,
        help_text="Notify when agent completes"
    )
    
    # Advanced preferences
    show_debug_info = models.BooleanField(
        default=False,
        help_text="Show event IDs, correlation IDs in UI"
    )
    
    show_ai_prompts = models.BooleanField(
        default=False,
        help_text="Show AI prompts for transparency"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_preferences'
        verbose_name = 'User Preferences'
        verbose_name_plural = 'User Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.username}"


@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """
    Auto-create default preferences when user is created
    """
    if created:
        UserPreferences.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_preferences(sender, instance, **kwargs):
    """
    Ensure preferences exist (in case signal was missed)
    """
    if not hasattr(instance, 'preferences'):
        UserPreferences.objects.create(user=instance)
