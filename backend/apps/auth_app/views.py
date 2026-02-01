"""
Authentication views
"""
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User

from .models import UserPreferences
from .serializers import UserSerializer, UserPreferencesSerializer, UserWithPreferencesSerializer


class EmailTokenObtainPairSerializer(serializers.Serializer):
    """Custom serializer that allows login with email instead of username"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        from django.contrib.auth import authenticate
        from rest_framework_simplejwt.tokens import RefreshToken
        
        email = attrs.get('email')
        password = attrs.get('password')
        
        # Find user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('No active account found with the given credentials')
        
        # Authenticate with username and password
        user = authenticate(username=user.username, password=password)
        
        if user is None:
            raise serializers.ValidationError('No active account found with the given credentials')
        
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled')
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class EmailTokenObtainPairView(TokenObtainPairView):
    """Custom token view that accepts email instead of username"""
    serializer_class = EmailTokenObtainPairSerializer


class CurrentUserView(generics.RetrieveAPIView):
    """Get current user profile with preferences"""
    serializer_class = UserWithPreferencesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserPreferencesView(generics.RetrieveUpdateAPIView):
    """
    Get and update user preferences
    
    GET /api/auth/preferences/ - Get current user preferences
    PATCH /api/auth/preferences/ - Update preferences
    """
    serializer_class = UserPreferencesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Get or create preferences for current user"""
        preferences, created = UserPreferences.objects.get_or_create(
            user=self.request.user
        )
        return preferences
    
    def partial_update(self, request, *args, **kwargs):
        """Allow partial updates (PATCH)"""
        return super().update(request, *args, **kwargs, partial=True)
