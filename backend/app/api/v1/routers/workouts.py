"""
Workouts router.

Endpoints:
  GET    /workouts               — list with filters
  POST   /workouts               — create
  GET    /workouts/{id}          — get one
  PATCH  /workouts/{id}          — update
  DELETE /workouts/{id}          — delete
  POST   /workouts/{id}/complete — mark as completed with optional actual data
  PATCH  /workouts/{id}/move     — move to a different date (drag-and-drop)
  PATCH  /workouts/{id}/toggle-complete — flip is_completed flag
"""
import logging
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.workout import (
    WorkoutCompleteRequest,
    WorkoutCreate,
    WorkoutFilters,
    WorkoutListResponse,
    WorkoutMoveRequest,
    WorkoutResponse,
    WorkoutUpdate,
)
from app.services.workout_service import WorkoutService

router = APIRouter(prefix="/workouts", tags=["workouts"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=WorkoutListResponse,
    summary="List workouts with optional filters",
)
async def list_workouts(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    # Date filters
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Calendar year"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Calendar month (1–12)"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    # Field filters
    sport_type: Optional[str] = Query(None),
    is_completed: Optional[bool] = Query(None),
    # Pagination
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
) -> WorkoutListResponse:
    """
    Return workouts for the current user.

    Filtering priority:
    - If `year` + `month` provided → return that calendar month.
    - Otherwise use `date_from` / `date_to` range.
    - `sport_type` and `is_completed` can be combined with any date filter.
    """
    from app.utils.enums import SportType

    filters = WorkoutFilters(
        year=year,
        month=month,
        date_from=date_from,
        date_to=date_to,
        sport_type=SportType(sport_type) if sport_type else None,
        is_completed=is_completed,
        skip=skip,
        limit=limit,
    )
    service = WorkoutService(db)
    items, total = await service.get_workouts(current_user.id, filters)
    return WorkoutListResponse(
        items=[WorkoutResponse.model_validate(w) for w in items],
        total=total,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=WorkoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workout",
)
async def create_workout(
    data: WorkoutCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkoutResponse:
    """Create a manual workout entry for the current user."""
    service = WorkoutService(db)
    workout = await service.create_workout(current_user.id, data)
    return WorkoutResponse.model_validate(workout)


# ---------------------------------------------------------------------------
# Get one
# ---------------------------------------------------------------------------

@router.get(
    "/{workout_id}",
    response_model=WorkoutResponse,
    summary="Get a single workout",
)
async def get_workout(
    workout_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkoutResponse:
    """Return a single workout. Returns 404 if not found, 403 if not owned."""
    service = WorkoutService(db)
    workout = await service.get_workout(current_user.id, workout_id)
    return WorkoutResponse.model_validate(workout)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.patch(
    "/{workout_id}",
    response_model=WorkoutResponse,
    summary="Update a workout",
)
async def update_workout(
    workout_id: int,
    data: WorkoutUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkoutResponse:
    """Update mutable fields of a workout. Only the owner can update."""
    service = WorkoutService(db)
    workout = await service.update_workout(current_user.id, workout_id, data)
    return WorkoutResponse.model_validate(workout)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete(
    "/{workout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workout",
)
async def delete_workout(
    workout_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a workout. Only the owner can delete."""
    service = WorkoutService(db)
    await service.delete_workout(current_user.id, workout_id)


# ---------------------------------------------------------------------------
# Complete
# ---------------------------------------------------------------------------

@router.post(
    "/{workout_id}/complete",
    response_model=WorkoutResponse,
    summary="Mark a workout as completed",
)
async def complete_workout(
    workout_id: int,
    data: WorkoutCompleteRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkoutResponse:
    """
    Mark a workout as completed. Optionally update actual duration and comment.
    """
    service = WorkoutService(db)
    workout = await service.complete_workout(current_user.id, workout_id, data)
    return WorkoutResponse.model_validate(workout)


# ---------------------------------------------------------------------------
# Toggle complete (lightweight checkbox toggle)
# ---------------------------------------------------------------------------

@router.patch(
    "/{workout_id}/toggle-complete",
    response_model=WorkoutResponse,
    summary="Toggle the is_completed flag",
)
async def toggle_complete(
    workout_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkoutResponse:
    """Flip the is_completed flag (used by the calendar checkbox UI)."""
    service = WorkoutService(db)
    workout = await service.toggle_complete(current_user.id, workout_id)
    return WorkoutResponse.model_validate(workout)


# ---------------------------------------------------------------------------
# Move (drag-and-drop)
# ---------------------------------------------------------------------------

@router.patch(
    "/{workout_id}/move",
    response_model=WorkoutResponse,
    summary="Move a workout to a different date",
)
async def move_workout(
    workout_id: int,
    data: WorkoutMoveRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkoutResponse:
    """Reassign a workout to a new date (calendar drag-and-drop)."""
    service = WorkoutService(db)
    workout = await service.move_workout(current_user.id, workout_id, data.new_date)
    return WorkoutResponse.model_validate(workout)
