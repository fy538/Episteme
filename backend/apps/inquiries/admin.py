"""
Django admin for inquiry models
"""
from django.contrib import admin
from apps.inquiries.models import InquiryHistory


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
