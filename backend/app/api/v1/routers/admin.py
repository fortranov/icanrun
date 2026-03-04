"""
Admin router — user management and application settings.

Endpoints:
  GET    /admin/users              — list all users with subscription info
  PATCH  /admin/users/{id}        — update user role / active status
  GET    /admin/settings          — get application-level settings
  PATCH  /admin/settings          — update application-level settings

All endpoints require admin role. Non-admins receive 403.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import CurrentAdmin, DatabaseSession
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import SubscriptionResponse
from app.schemas.user import UserResponse
from app.utils.enums import SubscriptionPlan, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AdminUserResponse(UserResponse):
    """User response including active subscription for the admin view."""
    subscription: Optional[SubscriptionResponse] = None


class AdminUserUpdate(BaseModel):
    """Admin-only user update: can change role and active status."""
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    subscription_plan: Optional[SubscriptionPlan] = None


class AppSettings(BaseModel):
    """Mutable application-level settings (stored in-memory for now)."""
    google_oauth_enabled: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""
    maintenance_mode: bool = False
    registration_open: bool = True


class AppSettingsUpdate(BaseModel):
    google_oauth_enabled: Optional[bool] = None
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    maintenance_mode: Optional[bool] = None
    registration_open: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_user_with_subscription(
    db, user: User
) -> AdminUserResponse:
    """Load user + active subscription into the admin response model."""
    from app.repositories.user_repository import UserRepository
    repo = UserRepository(db)
    sub = await repo.get_active_subscription(user.id)
    return AdminUserResponse(
        **UserResponse.model_validate(user).model_dump(),
        subscription=SubscriptionResponse.model_validate(sub) if sub else None,
    )


# ---------------------------------------------------------------------------
# User management endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/users",
    response_model=List[AdminUserResponse],
    summary="List all users (admin only)",
)
async def list_users(
    current_admin: CurrentAdmin,
    db: DatabaseSession,
) -> List[AdminUserResponse]:
    """Return all registered users with their active subscription info."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = list(result.scalars().all())

    responses = []
    for user in users:
        responses.append(await _get_user_with_subscription(db, user))

    logger.info(f"Admin {current_admin.id} listed {len(users)} users")
    return responses


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Update user role or status (admin only)",
)
async def update_user(
    user_id: int,
    data: AdminUserUpdate,
    current_admin: CurrentAdmin,
    db: DatabaseSession,
) -> AdminUserResponse:
    """
    Update a user's role, active status, or subscription plan.

    Admins cannot demote themselves to prevent lockout.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent admin self-demotion
    if user_id == current_admin.id and data.role is not None and data.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot remove their own admin role",
        )

    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active

    # Handle subscription plan change
    if data.subscription_plan is not None:
        from app.repositories.user_repository import UserRepository
        repo = UserRepository(db)
        existing_sub = await repo.get_active_subscription(user_id)

        if existing_sub is not None:
            existing_sub.is_active = False

        expires_at = None
        if data.subscription_plan != SubscriptionPlan.PRO:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        new_sub = Subscription(
            user_id=user_id,
            plan=data.subscription_plan,
            is_active=True,
            expires_at=expires_at,
        )
        db.add(new_sub)

    await db.flush()
    await db.refresh(user)

    logger.info(
        f"Admin {current_admin.id} updated user {user_id}: "
        f"role={data.role} active={data.is_active} plan={data.subscription_plan}"
    )
    return await _get_user_with_subscription(db, user)


# ---------------------------------------------------------------------------
# Application settings
# ---------------------------------------------------------------------------

@router.get(
    "/settings",
    response_model=AppSettings,
    summary="Get application settings (admin only)",
)
async def get_settings(
    current_admin: CurrentAdmin,
    db: DatabaseSession,
) -> AppSettings:
    """
    Return current application-level settings.

    For this MVP, settings are read from the running config (pydantic-settings).
    A production system would store these in a database table.
    """
    from app.core.config import settings as app_settings
    return AppSettings(
        google_oauth_enabled=app_settings.google_oauth_enabled,
        google_client_id=app_settings.google_client_id,
        google_client_secret="",  # Never expose secret to clients
        maintenance_mode=False,
        registration_open=True,
    )


@router.patch(
    "/settings",
    response_model=AppSettings,
    summary="Update application settings (admin only)",
)
async def update_settings(
    data: AppSettingsUpdate,
    current_admin: CurrentAdmin,
    db: DatabaseSession,
) -> AppSettings:
    """
    Update application-level settings.

    Note: For the MVP, changes are reflected at runtime but are not persisted
    across restarts (environment-variable-based config). A future iteration
    will store these in an AppConfig DB table.
    """
    from app.core.config import settings as app_settings

    if data.google_oauth_enabled is not None:
        app_settings.google_oauth_enabled = data.google_oauth_enabled
    if data.google_client_id is not None:
        app_settings.google_client_id = data.google_client_id
    if data.google_client_secret is not None and data.google_client_secret:
        app_settings.google_client_secret = data.google_client_secret

    logger.info(f"Admin {current_admin.id} updated app settings: {data.model_dump(exclude_none=True)}")

    return AppSettings(
        google_oauth_enabled=app_settings.google_oauth_enabled,
        google_client_id=app_settings.google_client_id,
        google_client_secret="",
        maintenance_mode=False,
        registration_open=True,
    )
