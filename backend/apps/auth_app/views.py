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
    email = serializers.EmailField(required=True)
    username = None  # Remove username field
    
    def validate(self, attrs):
        # Get email from the request
        email = attrs.get('email')
        password = attrs.get('password')
        
        # Find user by email and convert to username
        try:
            user = User.objects.get(email=email)
            # Replace email with username for the parent class
            attrs['username'] = user.username
            del attrs['email']  # Remove email so parent doesn't get confused
        except User.DoesNotExist:
            # If user doesn't exist, set a dummy username so parent can handle the error properly
            attrs['username'] = email
            if 'email' in attrs:
                del attrs['email']
        
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
