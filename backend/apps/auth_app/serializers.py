"""
Serializers for authentication and user preferences
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserPreferences


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']


class UserPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for UserPreferences"""
    
    class Meta:
        model = UserPreferences
        fields = [
            # Workspace
            'default_case_view',
            'auto_save_delay_ms',
            'auto_create_inquiries',
            'auto_detect_assumptions',
            'auto_generate_titles',
            
            # AI/Agents
            'chat_model',
            'agent_check_interval',
            'agent_min_confidence',
            'agent_auto_run',
            
            # Evidence
            'evidence_min_credibility',
            
            # Appearance
            'theme',
            'font_size',
            'density',
            
            # Notifications
            'email_notifications',
            'notify_on_inquiry_resolved',
            'notify_on_agent_complete',
            
            # Advanced
            'show_debug_info',
            'show_ai_prompts',
            
            # Metadata
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserWithPreferencesSerializer(serializers.ModelSerializer):
    """User serializer that includes preferences"""
    preferences = UserPreferencesSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'preferences']
        read_only_fields = ['id', 'username']
