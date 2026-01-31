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
    
    def validate(self, attrs):
        # The frontend sends 'email', but the parent class expects 'username'
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email:
            try:
                user = User.objects.get(email=email)
                # Replace 'email' with 'username' so authenticate() works
                attrs[self.username_field] = user.username
            except User.DoesNotExist:
                # If email not found, let it proceed to fail naturally 
                # so we don't leak information about which emails exist
                pass
        
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
