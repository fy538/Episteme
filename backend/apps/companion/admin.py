"""
Django admin for companion models
"""
from django.contrib import admin
from apps.companion.models import Reflection, InquiryHistory


@admin.register(Reflection)
class ReflectionAdmin(admin.ModelAdmin):
    """Admin for Reflection model"""
    
    list_display = ['id', 'thread', 'trigger_type', 'is_visible', 'created_at']
    list_filter = ['trigger_type', 'is_visible', 'created_at']
    search_fields = ['reflection_text', 'thread__title']
    readonly_fields = ['id', 'created_at', 'updated_at', 'analyzed_messages', 'analyzed_signals', 'patterns']
    
    fieldsets = [
        ('Basic Info', {
            'fields': ['id', 'thread', 'trigger_type', 'is_visible']
        }),
        ('Content', {
            'fields': ['reflection_text']
        }),
        ('Analysis Context', {
            'fields': ['analyzed_messages', 'analyzed_signals', 'patterns'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at', 'viewed_at']
        }),
    ]


@admin.register(InquiryHistory)
class InquiryHistoryAdmin(admin.ModelAdmin):
    """Admin for InquiryHistory model"""
    
    list_display = ['id', 'inquiry', 'confidence', 'timestamp', 'reason']
    list_filter = ['timestamp']
    search_fields = ['inquiry__title', 'reason']
    readonly_fields = ['id', 'timestamp']
    
    fieldsets = [
        ('Basic Info', {
            'fields': ['id', 'inquiry', 'confidence']
        }),
        ('Context', {
            'fields': ['trigger_event', 'reason']
        }),
        ('Timestamp', {
            'fields': ['timestamp']
        }),
    ]
