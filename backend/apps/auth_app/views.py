"""
Authentication views
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import UserSerializer


class CurrentUserView(generics.RetrieveAPIView):
    """Get current user profile"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


# JWT token views are provided by rest_framework_simplejwt
# We can customize them here if needed
