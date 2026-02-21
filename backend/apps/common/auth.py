"""
Shared authentication utilities for async views outside DRF.
"""
from asgiref.sync import sync_to_async


async def authenticate_jwt(request):
    """Authenticate a raw Django request using JWT.

    Used by async streaming views that bypass DRF's authentication layer.
    Returns the authenticated User, or None if authentication fails.
    """
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import (
        InvalidToken,
        AuthenticationFailed as JWTAuthFailed,
    )

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return None

    jwt_auth = JWTAuthentication()
    try:
        validated_token = await sync_to_async(jwt_auth.get_validated_token)(
            auth_header.split(' ', 1)[1]
        )
        user = await sync_to_async(jwt_auth.get_user)(validated_token)
        return user
    except (InvalidToken, JWTAuthFailed):
        return None
