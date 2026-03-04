"""
Authentication router.

Endpoints:
  POST /auth/register   — create a new account
  POST /auth/login      — obtain access + refresh tokens
  POST /auth/refresh    — rotate tokens using a valid refresh token
  POST /auth/logout     — invalidate the refresh token
  GET  /auth/me         — return the current authenticated user profile
"""
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AccessTokenResponse,
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
# Register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Create a new user account and automatically assign a 30-day Trial subscription.
    Returns access and refresh tokens so the user is immediately logged in.
    """
    service = AuthService(db)
    user, access_token, refresh_token = await service.register(data)
    return TokenResponse(
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
