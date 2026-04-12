"""
Workout data access layer.
"""
from datetime import date
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workout import Workout
from app.repositories.base import BaseRepository
from app.utils.enums import SportType


class WorkoutRepository(BaseRepository[Workout]):
    model = Workout

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_user(
        self,
        user_id: int,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Workout]:
        """Fetch all workouts for a user ordered by date descending."""
        result = await self.db.execute(
            select(Workout)
            .where(Workout.user_id == user_id)
            .order_by(Workout.date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_user_and_month(
        self,
        user_id: int,
        year: int,
        month: int,
    ) -> List[Workout]:
        """Fetch all workouts for a user in a specific month."""
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, last_day)
        result = await self.db.execute(
            select(Workout)
            .where(
                and_(
                    Workout.user_id == user_id,
                    Workout.date >= start,
                    Workout.date <= end,
                )
            )
            .order_by(Workout.date)
        )
        return list(result.scalars().all())

    async def get_by_date_range(
        self,
        user_id: int,
        start: date,
        end: date,
        sport_type: Optional[SportType] = None,
    ) -> List[Workout]:
        """Fetch workouts for a user within a date range, optionally filtered by sport."""
        conditions = [
            Workout.user_id == user_id,
            Workout.date >= start,
            Workout.date <= end,
        ]
        if sport_type:
            conditions.append(Workout.sport_type == sport_type)
        result = await self.db.execute(
            select(Workout).where(and_(*conditions)).order_by(Workout.date)
        )
        return list(result.scalars().all())

    async def get_by_month(
        self,
        user_id: int,
        year: int,
        month: int,
        sport_type: Optional[SportType] = None,
    ) -> List[Workout]:
        """
        Fetch all workouts for a user in a specific month, with optional sport filter.
        Used by the analytics service for statistics aggregation.
        """
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, last_day)
        conditions = [
            Workout.user_id == user_id,
            Workout.date >= start,
            Workout.date <= end,
        ]
        if sport_type is not None:
            conditions.append(Workout.sport_type == sport_type)
        result = await self.db.execute(
            select(Workout)
            .where(and_(*conditions))
            .order_by(Workout.date)
        )
        return list(result.scalars().all())

    async def get_by_garmin_id(self, garmin_activity_id: str) -> Optional[Workout]:
        """Find a workout by Garmin activity ID for deduplication."""
        result = await self.db.execute(
            select(Workout).where(Workout.garmin_activity_id == garmin_activity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_strava_id(self, strava_activity_id: int) -> Optional[Workout]:
        """Find a workout by Strava activity ID for deduplication."""
        result = await self.db.execute(
            select(Workout).where(Workout.strava_activity_id == strava_activity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_plan(self, plan_id: int) -> List[Workout]:
        """Fetch all workouts belonging to a training plan."""
        result = await self.db.execute(
            select(Workout)
            .where(Workout.plan_id == plan_id)
            .order_by(Workout.date)
        )
        return list(result.scalars().all())

    async def get_future_planned(self, plan_id: int, from_date: date) -> List[Workout]:
        """
        Fetch future planned workouts for a plan starting from from_date.
        Used when deleting a plan (keep past workouts, delete future ones).
        """
        result = await self.db.execute(
            select(Workout).where(
                and_(
                    Workout.plan_id == plan_id,
                    Workout.date >= from_date,
                )
            )
        )
        return list(result.scalars().all())
