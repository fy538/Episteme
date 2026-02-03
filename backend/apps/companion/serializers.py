"""
Companion serializers
"""
from rest_framework import serializers
from apps.companion.models import Reflection, InquiryHistory


class ReflectionSerializer(serializers.ModelSerializer):
    """Serializer for Reflection model"""
    
    class Meta:
        model = Reflection
        fields = [
            'id',
            'thread',
            'reflection_text',
            'trigger_type',
            'analyzed_messages',
            'analyzed_signals',
            'patterns',
            'is_visible',
            'viewed_at',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InquiryHistorySerializer(serializers.ModelSerializer):
    """Serializer for InquiryHistory model"""
    
    inquiry_title = serializers.CharField(source='inquiry.title', read_only=True)
    
    class Meta:
        model = InquiryHistory
        fields = [
            'id',
            'inquiry',
            'inquiry_title',
            'confidence',
            'trigger_event',
            'reason',
            'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']
