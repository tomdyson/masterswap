"""
Authentication API endpoints.
"""

from ninja import Router
from django.contrib.auth import login, logout
from django.urls import reverse
from sesame.utils import get_token
from core.models import User
from core.api.schemas import (
    MagicLinkRequestSchema,
    MagicLinkResponseSchema,
    ErrorSchema
)
from core.tasks import send_magic_link_email

router = Router()


@router.post("/request-magic-link", response={200: MagicLinkResponseSchema, 400: ErrorSchema})
def request_magic_link(request, payload: MagicLinkRequestSchema):
    """
    Request a magic link for passwordless authentication.
    Creates a new user if email doesn't exist.
    """
    email = payload.email.lower().strip()

    # Get or create user
    user, created = User.objects.get_or_create(
        email=email,
        defaults={'username': email.split('@')[0]}
    )

    # Generate magic link token
    token = get_token(user)

    # Build magic link URL
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'

    magic_link = f"{protocol}://{request.get_host()}{reverse('auth_verify')}?token={token}"

    # Send email asynchronously
    send_magic_link_email.delay(user.email, magic_link)

    return 200, {
        "message": "Magic link sent! Check your email.",
        "email": email
    }


@router.post("/logout", response={200: dict})
def logout_user(request):
    """
    Log out the current user.
    """
    logout(request)
    return 200, {"message": "Successfully logged out"}


@router.get("/verify-status", response={200: dict})
def verify_status(request):
    """
    Check if user is authenticated.
    """
    if request.user.is_authenticated:
        return 200, {
            "authenticated": True,
            "user_id": str(request.user.id),
            "email": request.user.email,
            "token_balance": request.user.token_balance
        }
    else:
        return 200, {
            "authenticated": False
        }
