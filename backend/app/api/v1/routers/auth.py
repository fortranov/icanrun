"""
Authentication router.

Endpoints:
  POST /auth/register             — create a new account
  POST /auth/login                — obtain access + refresh tokens
  POST /auth/refresh              — rotate tokens using a valid refresh token
  POST /auth/logout               — invalidate the refresh token
  GET  /auth/me                   — return the current authenticated user profile
  POST /auth/confirm-email        — activate account via confirmation token
  POST /auth/resend-confirmation  — re-send confirmation email
  GET  /auth/settings             — public settings (google_oauth_enabled flag)
  GET  /auth/google               — get Google OAuth redirect URL
  POST /auth/google/callback      — exchange Google code for tokens or pending token
  POST /auth/google/complete      — complete Google sign-up after terms acceptance
"""
import logging
from typing import Annotated, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AccessTokenResponse,
    AuthSettingsResponse,
    GoogleCallbackRequest,
    GoogleCallbackResponse,
    GoogleCompleteRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.subscription import SubscriptionResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Register response — may be tokens OR "check your email" message
# ---------------------------------------------------------------------------

class RegisterResponse(BaseModel):
    """
    Response for POST /auth/register.

    When email confirmation is disabled (default), access_token and
    refresh_token are returned and the user is immediately logged in.

    When email confirmation is enabled, both token fields are None and
    requires_confirmation=True signals the client to show "check your inbox".
    """
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    requires_confirmation: bool = False


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegisterResponse:
    """
    Create a new user account and automatically assign a 30-day Trial subscription.

    If the email_confirmation_enabled app setting is true, a confirmation email
    is sent and the response contains requires_confirmation=True with no tokens.
    Otherwise returns access and refresh tokens so the user is immediately logged in.
    """
    service = AuthService(db)
    user, access_token, refresh_token = await service.register(data)
    if access_token is None:
        return RegisterResponse(requires_confirmation=True)
    return RegisterResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
async def login(
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Authenticate with email and password.
    Returns a short-lived access token (30 min) and a long-lived refresh token (7 days).
    """
    service = AuthService(db)
    _, access_token, refresh_token = await service.login(data.email, data.password)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using a valid refresh token",
)
async def refresh(
    data: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    The old refresh token is immediately blacklisted (rotation strategy).
    """
    service = AuthService(db)
    new_access, new_refresh = await service.refresh_token(data.refresh_token)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
    )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class LogoutRequest(RefreshRequest):
    """Body for logout — accepts optional refresh token to blacklist."""
    pass


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout and invalidate the refresh token",
)
async def logout(
    data: Optional[LogoutRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Blacklist the provided refresh token so it can no longer be used.
    The client must discard both tokens after calling this endpoint.
    """
    service = AuthService(db)
    refresh_token = data.refresh_token if data else None
    await service.logout(refresh_token)


# ---------------------------------------------------------------------------
# Me — current user profile
# ---------------------------------------------------------------------------

class MeResponse(UserResponse):
    """Extended /me response that includes the user's active subscription."""
    subscription: Optional[SubscriptionResponse] = None


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current authenticated user profile",
)
async def me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    """
    Return the currently authenticated user's profile along with their active subscription.
    """
    repo = UserRepository(db)
    subscription = await repo.get_active_subscription(current_user.id)
    return MeResponse(
        **UserResponse.model_validate(current_user).model_dump(),
        subscription=SubscriptionResponse.model_validate(subscription) if subscription else None,
    )


# ---------------------------------------------------------------------------
# Email confirmation
# ---------------------------------------------------------------------------

class ConfirmEmailResponse(BaseModel):
    message: str = "Email confirmed successfully"


class ResendConfirmationRequest(BaseModel):
    email: EmailStr


@router.post(
    "/confirm-email",
    response_model=ConfirmEmailResponse,
    summary="Confirm email address via token",
)
async def confirm_email(
    token: Annotated[str, Query(description="JWT confirmation token from the email link")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConfirmEmailResponse:
    """
    Activate a user account by validating the JWT confirmation token.

    The token is passed as a query parameter: POST /auth/confirm-email?token=xxx

    On success the user's email_confirmed flag is set to True and the stored
    token is cleared. The client should redirect to /login.
    """
    service = AuthService(db)
    await service.confirm_email(token)
    return ConfirmEmailResponse()


@router.post(
    "/resend-confirmation",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Re-send email confirmation link",
)
async def resend_confirmation(
    data: ResendConfirmationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Request a new confirmation email.

    Always returns 204 regardless of whether the email exists or is already
    confirmed, to prevent email enumeration attacks.
    """
    service = AuthService(db)
    await service.resend_confirmation(data.email)


# ---------------------------------------------------------------------------
# Public auth settings
# ---------------------------------------------------------------------------

@router.get(
    "/settings",
    response_model=AuthSettingsResponse,
    summary="Get public authentication settings",
)
async def get_auth_settings() -> AuthSettingsResponse:
    """
    Return public authentication settings that the frontend needs without
    requiring authentication. Currently exposes the google_oauth_enabled flag
    so the UI can decide whether to show the 'Sign in with Google' button.
    """
    from app.core.config import settings as app_settings

    return AuthSettingsResponse(
        google_oauth_enabled=app_settings.google_oauth_enabled,
    )


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

class GoogleAuthUrlResponse(BaseModel):
    auth_url: str


@router.get(
    "/google",
    response_model=GoogleAuthUrlResponse,
    summary="Get Google OAuth2 authorization URL",
)
async def get_google_auth_url() -> GoogleAuthUrlResponse:
    """
    Return the Google OAuth2 authorization URL that the frontend should redirect
    the user to. Requires google_oauth_enabled to be true in settings.

    The redirect_uri embedded in the URL is read from the GOOGLE_REDIRECT_URI
    environment variable (defaults to http://localhost:3000/auth/google/callback).
    """
    from app.core.config import settings as app_settings

    if not app_settings.google_oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not enabled",
            headers={"X-Error-Code": "GOOGLE_OAUTH_DISABLED"},
        )

    import urllib.parse

    params = {
        "client_id": app_settings.google_client_id,
        "redirect_uri": app_settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return GoogleAuthUrlResponse(auth_url=auth_url)


@router.post(
    "/google/callback",
    response_model=GoogleCallbackResponse,
    summary="Handle Google OAuth2 callback — exchange code for tokens",
)
async def google_callback(
    data: GoogleCallbackRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoogleCallbackResponse:
    """
    Exchange the Google authorization code for user info.

    Response cases:
    - Existing user (matched by google_id or email): returns access + refresh tokens.
    - New user: returns requires_terms_acceptance=True + pending_token (10-min JWT)
      + name + email. The frontend should redirect to /auth/google/accept-terms.
    """
    service = AuthService(db)
    result = await service.google_login(data.code, data.redirect_uri)

    if result.requires_terms_acceptance:
        return GoogleCallbackResponse(
            requires_terms_acceptance=True,
            pending_token=result.pending_token,
            name=result.name,
            email=result.email,
        )

    return GoogleCallbackResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
    )


@router.post(
    "/google/complete",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Complete Google sign-up after terms acceptance",
)
async def google_complete(
    data: GoogleCompleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Finalize Google account creation. Called after the user accepts the
    terms of service on the /auth/google/accept-terms page.

    Validates the short-lived pending_token JWT, creates the user account
    with a 30-day Trial subscription, and returns access + refresh tokens.
    """
    service = AuthService(db)
    _, access_token, refresh_token = await service.google_complete(data.pending_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
