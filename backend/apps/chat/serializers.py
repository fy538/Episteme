"""
Chat serializers
"""
from rest_framework import serializers
from .models import ChatThread, Message, ConversationEpisode


class ConversationEpisodeSerializer(serializers.ModelSerializer):
    """Read-only serializer for ConversationEpisode."""

    start_message_id = serializers.UUIDField(source='start_message_id', read_only=True, allow_null=True)
    end_message_id = serializers.UUIDField(source='end_message_id', read_only=True, allow_null=True)

    class Meta:
        model = ConversationEpisode
        fields = [
            'id',
            'episode_index',
            'topic_label',
            'content_summary',
            'message_count',
            'shift_type',
            'sealed',
            'sealed_at',
            'start_message_id',
            'end_message_id',
            'created_at',
        ]
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model with rich content support"""

    is_rich_content = serializers.SerializerMethodField()
    source_chunks = serializers.SerializerMethodField()
    episode_id = serializers.UUIDField(source='episode_id', read_only=True, allow_null=True)

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
            'source_chunks',
            'created_at',
            'event_id',
            'episode_id',
        ]
        read_only_fields = ['id', 'created_at', 'event_id', 'is_rich_content', 'source_chunks', 'episode_id']

    def get_is_rich_content(self, obj):
        """Check if this is a rich message (not plain text)"""
        return obj.content_type != 'text'

    def get_source_chunks(self, obj):
        """Return source chunks for RAG-grounded messages."""
        if obj.role != 'assistant':
            return []
        chunks = obj.source_chunks.select_related('document').all()
        if not chunks:
            return []
        return [
            {
                'index': i,
                'chunk_id': str(chunk.id),
                'document_id': str(chunk.document_id),
                'document_title': chunk.document.title if chunk.document else '',
                'chunk_index': chunk.chunk_index,
                'excerpt': chunk.chunk_text[:200],
            }
            for i, chunk in enumerate(chunks)
        ]


class ChatThreadSerializer(serializers.ModelSerializer):
    """Serializer for ChatThread model"""

    message_count = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()
    episode_count = serializers.SerializerMethodField()

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
            'episode_count',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_episode_count(self, obj):
        if hasattr(obj, '_episode_count'):
            return obj._episode_count
        return obj.episodes.count()

    def get_message_count(self, obj):
        # Use annotated value from queryset when available
        if hasattr(obj, '_message_count'):
            return obj._message_count
        return obj.messages.count()

    def get_latest_message(self, obj):
        # Use prefetched messages when available, else fallback to query
        try:
            messages = obj.messages.all()
            if messages:
                latest = list(messages)[-1]  # Use prefetched cache
            else:
                return None
        except AttributeError:
            latest = obj.messages.last()
        if latest:
            content = latest.content or ''
            return {
                'id': str(latest.id),
                'role': latest.role,
                'content': content[:100] + '...' if len(content) > 100 else content,
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
