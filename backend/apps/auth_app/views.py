"""
Authentication views
"""
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User

from .serializers import UserSerializer


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer that allows login with email instead of username"""
    username_field = 'email'
    
    def validate(self, attrs):
        # Get email from the request
        email = attrs.get('email')
        password = attrs.get('password')
        
        # Find user by email
        try:
            user = User.objects.get(email=email)
            # Replace email with username for the parent class
            attrs['username'] = user.username
        except User.DoesNotExist:
            pass  # Let the parent class handle the error
        
        # Call parent validation with username
        return super().validate(attrs)


class EmailTokenObtainPairView(TokenObtainPairView):
    """Custom token view that accepts email instead of username"""
    serializer_class = EmailTokenObtainPairSerializer


class CurrentUserView(generics.RetrieveAPIView):
    """Get current user profile"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
