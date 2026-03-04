"""
Workout service — business logic for workout CRUD.

Responsibilities:
  - Ownership enforcement: all mutations verify user_id matches workout.user_id
  - Skip check: warn (not block) when creating a workout on a skipped day
  - complete_workout: set is_completed=True, optionally update duration and comment
  - All DB mutations operate within the session transaction; caller commits.
"""
import logging
from datetime import date
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skip import Skip
from app.models.workout import Workout
from app.repositories.workout_repository import WorkoutRepository
from app.schemas.workout import (
    WorkoutCompleteRequest,
    WorkoutCreate,
    WorkoutFilters,
    WorkoutUpdate,
)
from app.utils.enums import WorkoutSource

logger = logging.getLogger(__name__)


class WorkoutService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = WorkoutRepository(db)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_owned(self, user_id: int, workout_id: int) -> Workout:
        """
        Fetch a workout by ID and verify the caller owns it.

        Raises:
            404 if not found
            403 if the workout belongs to a different user
        """
        workout = await self.repo.get_by_id(workout_id)
        if workout is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workout not found",
            )
        if workout.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return workout

    async def _is_skipped(self, user_id: int, target_date: date) -> bool:
        """Check whether the user has recorded a Skip for the given date."""
        result = await self.db.execute(
            select(Skip).where(
                Skip.user_id == user_id,
                Skip.date == target_date,
            )
        )
        return result.scalar_one_or_none() is not None

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def get_workouts(
        self,
        user_id: int,
        filters: WorkoutFilters,
    ) -> Tuple[List[Workout], int]:
        """
        Return paginated workouts for a user applying all provided filters.

        Priority: if year+month are given → use month range.
                  if date_from/date_to given → use those.
                  otherwise → return all (paginated).

        Returns:
            (items, total_count_before_pagination)
        """
        from sqlalchemy import and_, func

        conditions = [Workout.user_id == user_id]

        # Date range resolution
        if filters.year and filters.month:
            from calendar import monthrange
            _, last_day = monthrange(filters.year, filters.month)
            conditions.append(Workout.date >= date(filters.year, filters.month, 1))
            conditions.append(Workout.date <= date(filters.year, filters.month, last_day))
        else:
            if filters.date_from:
                conditions.append(Workout.date >= filters.date_from)
            if filters.date_to:
                conditions.append(Workout.date <= filters.date_to)

        if filters.sport_type:
            conditions.append(Workout.sport_type == filters.sport_type)
        if filters.is_completed is not None:
            conditions.append(Workout.is_completed == filters.is_completed)

        where_clause = and_(*conditions)

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(Workout).where(where_clause)
        )
        total = count_result.scalar_one()

        # Fetch items
        items_result = await self.db.execute(
            select(Workout)
            .where(where_clause)
            .order_by(Workout.date.asc(), Workout.id.asc())
            .limit(filters.limit)
            .offset(filters.skip)
        )
        items = list(items_result.scalars().all())

        return items, total

    # ------------------------------------------------------------------
    # Single fetch
    # ------------------------------------------------------------------

    async def get_workout(self, user_id: int, workout_id: int) -> Workout:
        """Return a single workout, enforcing ownership."""
        return await self._get_owned(user_id, workout_id)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_workout(self, user_id: int, data: WorkoutCreate) -> Workout:
        """
        Create a new manual workout for the user.

        If the target date has a Skip record, the creation still succeeds
        (user overrides their skip) but a warning is logged.
        """
        if await self._is_skipped(user_id, data.date):
            logger.warning(
                f"User {user_id} creating workout on skipped date {data.date}"
            )

        workout = Workout(
            user_id=user_id,
            sport_type=data.sport_type,
            workout_type=data.workout_type,
            source=WorkoutSource.MANUAL,
            date=data.date,
            duration_minutes=data.duration_minutes,
            is_completed=False,
            comment=data.comment,
        )
        self.db.add(workout)
        await self.db.flush()
        await self.db.refresh(workout)
        logger.info(f"Workout created: id={workout.id} user={user_id} sport={data.sport_type}")
        return workout

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_workout(
        self, user_id: int, workout_id: int, data: WorkoutUpdate
    ) -> Workout:
        """
        Update mutable fields of a workout.
        Only the owner can update; planned workouts (source=PLANNED) can also be updated.
        """
        workout = await self._get_owned(user_id, workout_id)

        if data.sport_type is not None:
            workout.sport_type = data.sport_type
        if data.workout_type is not None:
            workout.workout_type = data.workout_type
        if data.date is not None:
            if await self._is_skipped(user_id, data.date):
                logger.warning(
                    f"User {user_id} moving workout {workout_id} to skipped date {data.date}"
                )
            workout.date = data.date
        if data.duration_minutes is not None:
            workout.duration_minutes = data.duration_minutes
        if data.comment is not None:
            workout.comment = data.comment
        if data.is_completed is not None:
            workout.is_completed = data.is_completed

        await self.db.flush()
        await self.db.refresh(workout)
        logger.info(f"Workout updated: id={workout_id} user={user_id}")
        return workout

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_workout(self, user_id: int, workout_id: int) -> None:
        """
        Delete a workout. Only the owner may delete.
        Garmin-sourced workouts can be deleted (they will re-sync if needed).
        """
        workout = await self._get_owned(user_id, workout_id)
        await self.db.delete(workout)
        await self.db.flush()
        logger.info(f"Workout deleted: id={workout_id} user={user_id}")

    # ------------------------------------------------------------------
    # Complete
    # ------------------------------------------------------------------

    async def complete_workout(
        self,
        user_id: int,
        workout_id: int,
        data: WorkoutCompleteRequest,
    ) -> Workout:
        """
        Mark a workout as completed.

        Optionally update the actual duration (e.g., run was 47 min instead of 50)
        and append/replace the comment with actual notes.
        """
        workout = await self._get_owned(user_id, workout_id)

        workout.is_completed = True

        if data.actual_duration_minutes is not None:
            workout.duration_minutes = data.actual_duration_minutes

        if data.comment is not None:
            workout.comment = data.comment

        await self.db.flush()
        await self.db.refresh(workout)
        logger.info(f"Workout completed: id={workout_id} user={user_id}")
        return workout

    # ------------------------------------------------------------------
    # Toggle complete (lightweight toggle for checkbox UI)
    # ------------------------------------------------------------------

    async def toggle_complete(self, user_id: int, workout_id: int) -> Workout:
        """Flip the is_completed flag without changing other fields."""
        workout = await self._get_owned(user_id, workout_id)
        workout.is_completed = not workout.is_completed
        await self.db.flush()
        await self.db.refresh(workout)
        return workout

    # ------------------------------------------------------------------
    # Move (drag-and-drop)
    # ------------------------------------------------------------------

    async def move_workout(
        self, user_id: int, workout_id: int, new_date: date
    ) -> Workout:
        """
        Move a workout to a new date (used by calendar drag-and-drop).
        Enforces ownership; logs warning if new date is a skip day.
        """
        workout = await self._get_owned(user_id, workout_id)
        if await self._is_skipped(user_id, new_date):
            logger.warning(
                f"User {user_id} moving workout {workout_id} onto skipped date {new_date}"
            )
        workout.date = new_date
        await self.db.flush()
        await self.db.refresh(workout)
        return workout
