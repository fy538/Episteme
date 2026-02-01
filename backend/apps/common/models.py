"""
Abstract base models and mixins
"""
import uuid
from django.db import models


class TimestampedModel(models.Model):
    """
    Abstract base class with created_at and updated_at timestamps
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    Abstract base class with UUID primary key
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True


class Organization(UUIDModel, TimestampedModel):
    """Organization/team for multi-user collaboration"""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    
    # Settings
    settings = models.JSONField(default=dict, blank=True)
    
    # Subscription/Plan (future)
    plan = models.CharField(
        max_length=50,
        choices=[('free', 'Free'), ('team', 'Team'), ('enterprise', 'Enterprise')],
        default='free'
    )
    
    class Meta:
        db_table = 'organizations'
        ordering = ['name']
    
    def __str__(self):
        return self.name
