"""
Plans router — training plan generation and management.

Endpoints:
  POST   /plans/generate          — generate a new Friel periodized plan
  GET    /plans                   — list all active plans for current user
  GET    /plans/{plan_id}         — full plan detail with periods and workouts
  PATCH  /plans/{plan_id}/settings — recalculate plan with new settings
  DELETE /plans/{plan_id}         — delete plan and future planned workouts

Subscription check: plan generation requires Trial or Pro subscription.
Basic plan holders are blocked from creating/modifying plans.
"""
import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DatabaseSession
from app.schemas.plan import (
    PlanDetailResponse,
    PlanGenerateRequest,
    PlanResponse,
    PlanSettingsUpdateRequest,
)
from app.services.plan_service import PlanService
from app.utils.enums import SubscriptionPlan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plans", tags=["plans"])


def _require_plan_access(current_user, db) -> None:
    """
    Inline subscription check for plan features.

    Basic subscribers cannot generate or modify plans.
    Trial and Pro subscribers have full access.

    Note: This check is intentionally synchronous and uses the user's
    subscription cached in the request context to avoid an extra DB hit.
    The PlanService itself does not perform subscription checks — that
    responsibility lives at the router boundary.
    """
    # We access the subscription through the repository in a lazy fashion.
    # The dependency layer (get_current_user) does not pre-load subscriptions,
    # so we perform a quick check here using the user relationships.
    # In a more complete implementation this would use a dedicated
    # SubscriptionService.check_feature("plans", user) method.
    pass  # Subscription enforcement is handled via the dependency below


async def _check_plan_subscription(current_user, db) -> None:
    """
    Verify the user's active subscription allows plan generation.
    Raises 403 for Basic plan users.
    """
    from app.repositories.user_repository import UserRepository
    repo = UserRepository(db)
    subscription = await repo.get_active_subscription(current_user.id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required to use training plans",
        )
    if subscription.plan == SubscriptionPlan.BASIC:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Training plan generation requires a Pro or Trial subscription. "
                "Upgrade your plan to access this feature."
            ),
        )


@router.post(
    "/generate",
    response_model=PlanDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new training plan",
    description=(
        "Generate a Joe Friel periodized training plan. "
        "The plan is built from today until the target competition date "
        "(or 26 weeks for a maintenance plan). "
        "All planned workouts are persisted immediately. "
        "Requires Trial or Pro subscription."
    ),
)
async def generate_plan(
    data: PlanGenerateRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> PlanDetailResponse:
    await _check_plan_subscription(current_user, db)
    service = PlanService(db)
    return await service.generate_plan(user_id=current_user.id, data=data)


@router.get(
    "",
    response_model=List[PlanResponse],
    summary="List all active training plans",
)
async def list_plans(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> List[PlanResponse]:
    service = PlanService(db)
    return await service.get_user_plans(user_id=current_user.id)


@router.get(
    "/{plan_id}",
    response_model=PlanDetailResponse,
    summary="Get full plan detail with periods and workouts",
)
async def get_plan(
    plan_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> PlanDetailResponse:
    service = PlanService(db)
    return await service.get_plan(user_id=current_user.id, plan_id=plan_id)


@router.patch(
    "/{plan_id}/settings",
    response_model=PlanDetailResponse,
    summary="Update plan settings and regenerate future workouts",
    description=(
        "Recalculate the plan with updated settings. "
        "Past workouts (date < today) are preserved. "
        "Future planned workouts are deleted and regenerated. "
        "Requires Trial or Pro subscription."
    ),
)
async def update_plan_settings(
    plan_id: int,
    data: PlanSettingsUpdateRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> PlanDetailResponse:
    await _check_plan_subscription(current_user, db)
    service = PlanService(db)
    return await service.update_plan_settings(
        user_id=current_user.id, plan_id=plan_id, data=data
    )


@router.delete(
    "/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a training plan",
    description=(
        "Delete the plan and all future planned workouts. "
        "Past workouts are preserved with plan_id set to NULL."
    ),
)
async def delete_plan(
    plan_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> None:
    service = PlanService(db)
    await service.delete_plan(user_id=current_user.id, plan_id=plan_id)
