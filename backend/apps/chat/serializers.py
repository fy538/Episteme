"""
Chat serializers
"""
from rest_framework import serializers
from .models import ChatThread, Message


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model with rich content support"""
    
    is_rich_content = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id',
            'thread',
            'role',
            'content',
            'content_type',
            'structured_content',
            'is_rich_content',
            'metadata',
            'created_at',
            'event_id',
        ]
        read_only_fields = ['id', 'created_at', 'event_id', 'is_rich_content']
    
    def get_is_rich_content(self, obj):
        """Check if this is a rich message (not plain text)"""
        return obj.content_type != 'text'


class ChatThreadSerializer(serializers.ModelSerializer):
    """Serializer for ChatThread model"""
    
    message_count = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatThread
        fields = [
            'id',
            'title',
            'thread_type',
            'user',
            'primary_case',
            'project',
            'archived',
            'metadata',
            'created_at',
            'updated_at',
            'message_count',
            'latest_message',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_latest_message(self, obj):
        latest = obj.messages.last()
        if latest:
            return {
                'id': str(latest.id),
                'role': latest.role,
                'content': latest.content[:100] + '...' if len(latest.content) > 100 else latest.content,
                'created_at': latest.created_at,
            }
        return None


class ChatThreadDetailSerializer(ChatThreadSerializer):
    """Detailed serializer with messages"""
    
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta(ChatThreadSerializer.Meta):
        fields = ChatThreadSerializer.Meta.fields + ['messages']


class CreateMessageSerializer(serializers.Serializer):
    """Serializer for creating a new message"""
    
    content = serializers.CharField()
    
    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        return value.strip()
