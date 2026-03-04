"""
Users router — profile management for authenticated users.

Endpoints:
  GET   /users/me        — get own profile (used by frontend authApi.me())
  PATCH /users/me        — update own profile
"""
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.repositories.user_repository import UserRepository
from app.schemas.subscription import SubscriptionResponse
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


class UserProfileResponse(UserResponse):
    """User profile with active subscription."""
    subscription: Optional[SubscriptionResponse] = None


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Return the current user's profile with their active subscription."""
    repo = UserRepository(db)
    subscription = await repo.get_active_subscription(current_user.id)
    return UserProfileResponse(
        **UserResponse.model_validate(current_user).model_dump(),
        subscription=SubscriptionResponse.model_validate(subscription) if subscription else None,
    )


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="Update current user profile",
)
async def update_me(
    data: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """
    Update the current user's editable profile fields.
    Email changes check for uniqueness before applying.
    """
    repo = UserRepository(db)

    # Check email uniqueness if changing email
    if data.email and data.email.lower() != current_user.email:
        existing = await repo.get_by_email(data.email.lower())
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        current_user.email = data.email.lower()

    if data.name is not None:
        current_user.name = data.name
    if data.birth_year is not None:
        current_user.birth_year = data.birth_year
    if data.gender is not None:
        current_user.gender = data.gender
    if data.weight_kg is not None:
        current_user.weight_kg = data.weight_kg
    if data.height_cm is not None:
        current_user.height_cm = data.height_cm

    await db.flush()
    await db.refresh(current_user)

    subscription = await repo.get_active_subscription(current_user.id)
    logger.info(f"User profile updated: id={current_user.id}")

    return UserProfileResponse(
        **UserResponse.model_validate(current_user).model_dump(),
        subscription=SubscriptionResponse.model_validate(subscription) if subscription else None,
    )
