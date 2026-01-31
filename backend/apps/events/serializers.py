"""
Event serializers
"""
from rest_framework import serializers
from .models import Event


class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for Event model
    Read-only (events are append-only via EventService)
    """
    
    class Meta:
        model = Event
        fields = [
            'id',
            'timestamp',
            'actor_type',
            'actor_id',
            'type',
            'payload',
            'correlation_id',
            'case_id',
            'thread_id',
        ]
        read_only_fields = fields  # All fields are read-only
