"""
Signal serializers (Phase 1)
"""
from rest_framework import serializers
from .models import Signal, SignalType


class SignalSerializer(serializers.ModelSerializer):
    """Serializer for Signal model"""
    
    is_dismissed = serializers.SerializerMethodField()
    is_elevated = serializers.SerializerMethodField()
    
    class Meta:
        model = Signal
        fields = [
            'id',
            'event',
            'type',
            'text',
            'normalized_text',
            'span',
            'confidence',
            'temperature',
            'assumption_status',
            'dedupe_key',
            'case',
            'thread',
            'inquiry',
            'dismissed_at',
            'created_at',
            'is_dismissed',
            'is_elevated',
        ]
        read_only_fields = [
            'id',
            'event',
            'normalized_text',
            'dedupe_key',
            'created_at',
            'is_dismissed',
            'is_elevated',
        ]
    
    def get_is_dismissed(self, obj):
        """Check if signal has been dismissed"""
        return obj.dismissed_at is not None
    
    def get_is_elevated(self, obj):
        """Check if signal has been elevated to an inquiry"""
        return obj.inquiry_id is not None


class EditSignalSerializer(serializers.Serializer):
    """Serializer for editing signal text"""
    
    text = serializers.CharField()
