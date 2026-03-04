"""
Subscriptions router — current user subscription info.

Endpoints:
  GET  /subscriptions/current   — get the current user's active subscription

Payment-related endpoints (YooKassa) are handled in the payments router.
"""
import logging
from typing import Optional

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DatabaseSession
from app.repositories.user_repository import UserRepository
from app.schemas.subscription import SubscriptionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get(
    "/current",
    response_model=Optional[SubscriptionResponse],
    summary="Get current user subscription",
    description=(
        "Return the active subscription for the authenticated user. "
        "Returns null if the user has no active subscription."
    ),
)
async def get_current_subscription(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> Optional[SubscriptionResponse]:
    """Return the active subscription for the current user."""
    repo = UserRepository(db)
    subscription = await repo.get_active_subscription(current_user.id)
    if subscription is None:
        return None
    return SubscriptionResponse.model_validate(subscription)
