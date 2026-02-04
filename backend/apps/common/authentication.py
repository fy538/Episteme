"""
Custom authentication classes for SSE and other special cases.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class QueryParamJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication that supports tokens in query parameters.
    
    This is needed for Server-Sent Events (SSE) endpoints where
    EventSource API cannot send custom headers.
    
    Usage:
        GET /api/endpoint/?token=<jwt_token>
    """
    
    def authenticate(self, request):
        # First try the standard header-based authentication
        header_auth = super().authenticate(request)
        if header_auth is not None:
            return header_auth
        
        # If no header token, try query parameter
        token = request.GET.get('token')
        if token is None:
            return None
        
        try:
            validated_token = self.get_validated_token(token)
            return self.get_user(validated_token), validated_token
        except Exception as e:
            raise AuthenticationFailed(f'Invalid token: {str(e)}')
