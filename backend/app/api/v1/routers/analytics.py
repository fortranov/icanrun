"""
Analytics router — workout statistics for the Results page.

Endpoints:
  GET /analytics/monthly  — aggregate stats for one month
  GET /analytics/daily    — per-day stats list for bar chart rendering

All endpoints require authentication. Results are scoped to the current user.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DatabaseSession
from app.schemas.analytics import DailyStatsResponse, MonthlyStats
from app.services.analytics_service import AnalyticsService
from app.utils.enums import SportType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/monthly",
    response_model=MonthlyStats,
    summary="Get monthly aggregate statistics",
    description=(
        "Return total and per-sport statistics for a calendar month. "
        "Includes completed vs planned-but-not-completed breakdown."
    ),
)
async def get_monthly_stats(
    current_user: CurrentUser,
    db: DatabaseSession,
    year: int = Query(..., ge=2000, le=2100, description="4-digit year"),
    month: int = Query(..., ge=1, le=12, description="Month 1–12"),
    sport: Optional[str] = Query(None, description="Filter by sport type"),
) -> MonthlyStats:
    sport_type: Optional[SportType] = None
    if sport:
        try:
            sport_type = SportType(sport)
        except ValueError:
            pass  # Invalid sport → no filter

    service = AnalyticsService(db)
    return await service.get_monthly_stats(
        user_id=current_user.id,
        year=year,
        month=month,
        sport_type=sport_type,
    )


@router.get(
    "/daily",
    response_model=DailyStatsResponse,
    summary="Get per-day statistics for bar chart",
    description=(
        "Return one DayStats entry per calendar day in the month. "
        "Days with no workouts have zeroed values. "
        "Completed and planned-not-completed minutes are split for dual-bar charts."
    ),
)
async def get_daily_stats(
    current_user: CurrentUser,
    db: DatabaseSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    sport: Optional[str] = Query(None),
) -> DailyStatsResponse:
    sport_type: Optional[SportType] = None
    if sport:
        try:
            sport_type = SportType(sport)
        except ValueError:
            pass

    service = AnalyticsService(db)
    days = await service.get_daily_stats(
        user_id=current_user.id,
        year=year,
        month=month,
        sport_type=sport_type,
    )
    summary = await service.get_monthly_stats(
        user_id=current_user.id,
        year=year,
        month=month,
        sport_type=sport_type,
    )

    return DailyStatsResponse(
        year=year,
        month=month,
        days=days,
        summary=summary,
    )
