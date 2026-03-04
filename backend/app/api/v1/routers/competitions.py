"""
Competitions router.

Endpoints:
  GET    /competitions           — list with optional filters
  POST   /competitions           — create
  GET    /competitions/{id}      — get one
  PATCH  /competitions/{id}      — update
  DELETE /competitions/{id}      — delete
  POST   /competitions/{id}/result — record actual race result
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.competition import (
    CompetitionCreate,
    CompetitionFilters,
    CompetitionListResponse,
    CompetitionResponse,
    CompetitionResultRequest,
    CompetitionUpdate,
)
from app.services.competition_service import CompetitionService

router = APIRouter(prefix="/competitions", tags=["competitions"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=CompetitionListResponse,
    summary="List competitions with optional filters",
)
async def list_competitions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    sport_type: Optional[str] = Query(None),
    importance: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
) -> CompetitionListResponse:
    """Return all competitions for the current user with optional filters."""
    from app.utils.enums import CompetitionImportance, SportType

    filters = CompetitionFilters(
        sport_type=SportType(sport_type) if sport_type else None,
        importance=CompetitionImportance(importance) if importance else None,
        date_from=date_from,
        date_to=date_to,
    )
    service = CompetitionService(db)
    items, total = await service.get_competitions(current_user.id, filters)
    return CompetitionListResponse(
        items=[CompetitionResponse.model_validate(c) for c in items],
        total=total,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=CompetitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new competition entry",
)
async def create_competition(
    data: CompetitionCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompetitionResponse:
    """
    Create a competition entry.
    Distance is required for swimming and cycling competition types.
    """
    service = CompetitionService(db)
    competition = await service.create_competition(current_user.id, data)
    return CompetitionResponse.model_validate(competition)


# ---------------------------------------------------------------------------
# Get one
# ---------------------------------------------------------------------------

@router.get(
    "/{competition_id}",
    response_model=CompetitionResponse,
    summary="Get a single competition",
)
async def get_competition(
    competition_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompetitionResponse:
    """Return a single competition. 404 if not found, 403 if not owned."""
    service = CompetitionService(db)
    competition = await service.get_competition(current_user.id, competition_id)
    return CompetitionResponse.model_validate(competition)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.patch(
    "/{competition_id}",
    response_model=CompetitionResponse,
    summary="Update a competition",
)
async def update_competition(
    competition_id: int,
    data: CompetitionUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompetitionResponse:
    """Update mutable fields of a competition. Only the owner can update."""
    service = CompetitionService(db)
    competition = await service.update_competition(current_user.id, competition_id, data)
    return CompetitionResponse.model_validate(competition)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete(
    "/{competition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a competition",
)
async def delete_competition(
    competition_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a competition. Detaches any linked training plan automatically."""
    service = CompetitionService(db)
    await service.delete_competition(current_user.id, competition_id)


# ---------------------------------------------------------------------------
# Record result
# ---------------------------------------------------------------------------

@router.post(
    "/{competition_id}/result",
    response_model=CompetitionResponse,
    summary="Record the actual race result",
)
async def add_result(
    competition_id: int,
    data: CompetitionResultRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompetitionResponse:
    """
    Record a race result. Creates a completed workout entry on the race day
    with the finish time and comment stored in the workout's comment field.
    """
    service = CompetitionService(db)
    competition = await service.add_result(current_user.id, competition_id, data)
    return CompetitionResponse.model_validate(competition)
