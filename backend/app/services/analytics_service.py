"""
Analytics Service — workout statistics aggregation.

Provides per-month and per-day statistics for the Results page.

Aggregation logic:
  - Workouts are grouped by date within the requested month.
  - Completed vs planned-not-completed distinction drives the chart dual-bars.
  - Sport breakdown counts both completed and total minutes.
  - Completion rate = completed_count / total_count (0 if no workouts).
"""
import logging
from calendar import monthrange
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.workout_repository import WorkoutRepository
from app.schemas.analytics import DayStats, MonthlyStats, SportBreakdown
from app.utils.enums import SportType

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Aggregate workout data for analytics/results views."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = WorkoutRepository(db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_monthly_stats(
        self,
        user_id: int,
        year: int,
        month: int,
        sport_type: Optional[SportType] = None,
    ) -> MonthlyStats:
        """
        Return aggregate statistics for a calendar month.

        Args:
            user_id: The requesting user.
            year:    4-digit year.
            month:   Month number 1–12.
            sport_type: Optional filter to a single sport.

        Returns:
            MonthlyStats with total, completed, and per-sport breakdowns.
        """
        workouts = await self.repo.get_by_month(user_id, year, month, sport_type)

        today = date.today()

        total_minutes = 0
        completed_minutes = 0
        total_count = 0
        completed_count = 0
        # Past-only counters for completion rate (workouts on/before today)
        past_total = 0
        past_completed = 0
        by_sport: Dict[str, SportBreakdown] = {}

        for w in workouts:
            total_minutes += w.duration_minutes
            total_count += 1

            if w.is_completed:
                completed_minutes += w.duration_minutes
                completed_count += 1

            # Accumulate past-days counters for completion rate
            workout_date = w.date if isinstance(w.date, date) else date.fromisoformat(str(w.date))
            if workout_date <= today:
                past_total += 1
                if w.is_completed:
                    past_completed += 1

            sport_key = w.sport_type.value if hasattr(w.sport_type, "value") else w.sport_type
            if sport_key not in by_sport:
                by_sport[sport_key] = SportBreakdown()

            by_sport[sport_key].total_minutes += w.duration_minutes
            by_sport[sport_key].total_workouts += 1
            if w.is_completed:
                by_sport[sport_key].completed_minutes += w.duration_minutes
                by_sport[sport_key].completed_workouts += 1

        # Completion rate based only on past days (excludes future planned workouts)
        completion_rate = (
            round(past_completed / past_total * 100, 1) if past_total > 0 else 0.0
        )

        logger.debug(
            f"Monthly stats user={user_id} {year}-{month:02d}: "
            f"workouts={total_count} completed={completed_count} "
            f"past={past_total} past_completed={past_completed}"
        )

        return MonthlyStats(
            year=year,
            month=month,
            total_minutes=total_minutes,
            completed_minutes=completed_minutes,
            total_workouts=total_count,
            completed_workouts=completed_count,
            completion_rate=completion_rate,
            past_total_workouts=past_total,
            past_completed_workouts=past_completed,
            by_sport=by_sport,
        )

    async def get_daily_stats(
        self,
        user_id: int,
        year: int,
        month: int,
        sport_type: Optional[SportType] = None,
    ) -> List[DayStats]:
        """
        Return per-day statistics for a month — used to build bar charts.

        Every day in the month is represented (even days with no workouts
        have zeroed entries), allowing the chart to render a complete timeline.

        Args:
            user_id:    The requesting user.
            year:       4-digit year.
            month:      Month number 1–12.
            sport_type: Optional sport filter.

        Returns:
            List of DayStats, one per calendar day, sorted by date.
        """
        workouts = await self.repo.get_by_month(user_id, year, month, sport_type)

        # Build per-day buckets
        days_in_month = monthrange(year, month)[1]
        day_data: Dict[str, DayStats] = {}

        for day_num in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{day_num:02d}"
            day_data[date_str] = DayStats(
                date=date_str,
                completed_minutes=0,
                planned_minutes=0,
                total_minutes=0,
            )

        for w in workouts:
            date_str = str(w.date)
            if date_str not in day_data:
                # Shouldn't happen but guard against it
                day_data[date_str] = DayStats(
                    date=date_str,
                    completed_minutes=0,
                    planned_minutes=0,
                    total_minutes=0,
                )

            entry = day_data[date_str]
            entry.total_minutes += w.duration_minutes

            if w.is_completed:
                entry.completed_minutes += w.duration_minutes
            else:
                entry.planned_minutes += w.duration_minutes

        return sorted(day_data.values(), key=lambda d: d.date)
