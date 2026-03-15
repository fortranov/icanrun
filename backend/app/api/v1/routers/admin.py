"""
Admin router — user management and application settings.

Endpoints:
  GET    /admin/users              — list all users with subscription info
  PATCH  /admin/users/{id}        — update user role / active status
  GET    /admin/settings          — get application-level settings (from DB)
  PUT    /admin/settings          — update application-level settings (persisted to DB)
  POST   /admin/settings/test-email — send a test email to the admin's address

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


class AppSettingsResponse(BaseModel):
    """Full app settings returned to admin UI."""
    # Google OAuth
    google_oauth_enabled: bool = False
    google_client_id: str = ""
    # Note: google_client_secret is never returned to the client
    maintenance_mode: bool = False
    registration_open: bool = True
    # Email confirmation
    email_confirmation_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "ICanRun"
    confirmation_token_hours: int = 24


class AppSettingsUpdate(BaseModel):
    """Partial update payload for admin settings."""
    # Google OAuth
    google_oauth_enabled: Optional[bool] = None
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None  # write-only field
    # Email confirmation
    email_confirmation_enabled: Optional[bool] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None  # write-only field
    smtp_from_email: Optional[str] = None
    smtp_from_name: Optional[str] = None
    confirmation_token_hours: Optional[int] = Field(None, ge=1, le=168)


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


async def _build_settings_response(db) -> AppSettingsResponse:
    """
    Build AppSettingsResponse by merging DB settings with runtime config.
    google_client_secret and smtp_password are intentionally omitted.
    """
    from app.core.config import settings as app_settings
    from app.services.settings_service import SettingsService

    svc = SettingsService(db)
    all_settings = await svc.get_all()

    def _bool(key: str) -> bool:
        return all_settings.get(key, "false").lower() == "true"

    def _int(key: str, default: int) -> int:
        try:
            return int(all_settings.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    return AppSettingsResponse(
        # Google OAuth comes from pydantic-settings (still env-var driven)
        google_oauth_enabled=app_settings.google_oauth_enabled,
        google_client_id=app_settings.google_client_id,
        maintenance_mode=False,
        registration_open=True,
        # Email confirmation comes from DB
        email_confirmation_enabled=_bool("email_confirmation_enabled"),
        smtp_host=all_settings.get("smtp_host", ""),
        smtp_port=_int("smtp_port", 587),
        smtp_user=all_settings.get("smtp_user", ""),
        smtp_from_email=all_settings.get("smtp_from_email", ""),
        smtp_from_name=all_settings.get("smtp_from_name", "ICanRun"),
        confirmation_token_hours=_int("confirmation_token_hours", 24),
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
# Application settings — DB-persisted
# ---------------------------------------------------------------------------

@router.get(
    "/settings",
    response_model=AppSettingsResponse,
    summary="Get application settings (admin only)",
)
async def get_settings(
    current_admin: CurrentAdmin,
    db: DatabaseSession,
) -> AppSettingsResponse:
    """
    Return current application-level settings.

    SMTP password and Google client secret are never returned to the client.
    """
    return await _build_settings_response(db)


@router.put(
    "/settings",
    response_model=AppSettingsResponse,
    summary="Update application settings (admin only) — full replace",
    include_in_schema=False,  # Alias for PATCH — kept for REST convention
)
@router.patch(
    "/settings",
    response_model=AppSettingsResponse,
    summary="Update application settings (admin only)",
)
async def update_settings(
    data: AppSettingsUpdate,
    current_admin: CurrentAdmin,
    db: DatabaseSession,
) -> AppSettingsResponse:
    """
    Update application-level settings.

    Google OAuth fields update the runtime config (pydantic-settings object).
    All other fields are persisted to the app_settings DB table.
    """
    from app.core.config import settings as app_settings
    from app.services.settings_service import SettingsService

    svc = SettingsService(db)

    # Google OAuth — still stored in runtime settings object (env-var approach)
    if data.google_oauth_enabled is not None:
        app_settings.google_oauth_enabled = data.google_oauth_enabled
    if data.google_client_id is not None:
        app_settings.google_client_id = data.google_client_id
    if data.google_client_secret:
        app_settings.google_client_secret = data.google_client_secret

    # DB-persisted settings
    db_updates: dict[str, str] = {}

    if data.email_confirmation_enabled is not None:
        db_updates["email_confirmation_enabled"] = (
            "true" if data.email_confirmation_enabled else "false"
        )
    if data.smtp_host is not None:
        db_updates["smtp_host"] = data.smtp_host
    if data.smtp_port is not None:
        db_updates["smtp_port"] = str(data.smtp_port)
    if data.smtp_user is not None:
        db_updates["smtp_user"] = data.smtp_user
    if data.smtp_password:  # empty string = "not changing"
        db_updates["smtp_password"] = data.smtp_password
    if data.smtp_from_email is not None:
        db_updates["smtp_from_email"] = data.smtp_from_email
    if data.smtp_from_name is not None:
        db_updates["smtp_from_name"] = data.smtp_from_name
    if data.confirmation_token_hours is not None:
        db_updates["confirmation_token_hours"] = str(data.confirmation_token_hours)

    if db_updates:
        await svc.update_many(db_updates)
        await db.flush()

    logger.info(
        f"Admin {current_admin.id} updated app settings: "
        f"{data.model_dump(exclude_none=True, exclude={'smtp_password', 'google_client_secret'})}"
    )
    return await _build_settings_response(db)


# ---------------------------------------------------------------------------
# Test email
# ---------------------------------------------------------------------------

@router.post(
    "/settings/test-email",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Send a test email to verify SMTP settings (admin only)",
)
async def test_email(
    current_admin: CurrentAdmin,
    db: DatabaseSession,
) -> None:
    """
    Send a test email to the admin's own address using the current SMTP settings.
    Returns 204 on success. Raises 400 if SMTP settings are incomplete or sending fails.
    """
    from app.services.email_service import send_test_email
    from app.services.settings_service import SettingsService

    svc = SettingsService(db)

    smtp_host = await svc.smtp_host()
    smtp_port = await svc.smtp_port()
    smtp_user = await svc.smtp_user()
    smtp_password = await svc.smtp_password()
    from_email = await svc.smtp_from_email()
    from_name = await svc.smtp_from_name()

    if not smtp_host or not from_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP host and sender email must be configured before testing",
        )

    try:
        await send_test_email(
            to_email=current_admin.email,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            from_email=from_email,
            from_name=from_name,
        )
    except Exception as exc:
        logger.error(f"Test email failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SMTP error: {exc}",
        )
