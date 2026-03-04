"""
Competition service — business logic for competition CRUD and result recording.

A competition represents a target race/event. It can optionally be linked
to a TrainingPlan as its goal event (used by the Friel plan generator).

Result recording stores the actual finish time as a comment on the competition
and can also create a workout record for the race day if desired.
"""
import logging
from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import Competition
from app.repositories.competition_repository import CompetitionRepository
from app.schemas.competition import (
    CompetitionCreate,
    CompetitionFilters,
    CompetitionResultRequest,
    CompetitionUpdate,
)

logger = logging.getLogger(__name__)


class CompetitionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CompetitionRepository(db)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_owned(self, user_id: int, competition_id: int) -> Competition:
        """
        Fetch a competition by ID, enforcing ownership.

        Raises:
            404 if not found
            403 if competition belongs to a different user
        """
        competition = await self.repo.get_by_id(competition_id)
        if competition is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competition not found",
            )
        if competition.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return competition

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def get_competitions(
        self,
        user_id: int,
        filters: CompetitionFilters,
    ) -> Tuple[List[Competition], int]:
        """
        Return all competitions for a user with optional filters.
        Returns (items, total).
        """
        items = await self.repo.get_by_user_filtered(
            user_id=user_id,
            sport_type=filters.sport_type,
            importance=filters.importance,
            date_from=filters.date_from,
            date_to=filters.date_to,
        )
        return items, len(items)

    # ------------------------------------------------------------------
    # Single fetch
    # ------------------------------------------------------------------

    async def get_competition(self, user_id: int, competition_id: int) -> Competition:
        """Return a single competition, enforcing ownership."""
        return await self._get_owned(user_id, competition_id)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_competition(
        self, user_id: int, data: CompetitionCreate
    ) -> Competition:
        """
        Create a new competition entry.

        Distance validation:
          - SWIMMING and CYCLING types require a distance value.
          - Standard distance types (5K, marathon, etc.) ignore distance field.
        """
        from app.utils.enums import CompetitionType

        needs_distance = data.competition_type in (
            CompetitionType.SWIMMING,
            CompetitionType.CYCLING,
        )
        if needs_distance and not data.distance:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="distance is required for swimming and cycling competition types",
            )

        competition = Competition(
            user_id=user_id,
            sport_type=data.sport_type,
            competition_type=data.competition_type,
            importance=data.importance,
            date=data.date,
            name=data.name,
            distance=data.distance,
        )
        self.db.add(competition)
        await self.db.flush()
        await self.db.refresh(competition)
        logger.info(
            f"Competition created: id={competition.id} user={user_id} "
            f"name={data.name} date={data.date}"
        )
        return competition

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_competition(
        self, user_id: int, competition_id: int, data: CompetitionUpdate
    ) -> Competition:
        """Update mutable fields of a competition."""
        competition = await self._get_owned(user_id, competition_id)

        if data.sport_type is not None:
            competition.sport_type = data.sport_type
        if data.competition_type is not None:
            competition.competition_type = data.competition_type
        if data.importance is not None:
            competition.importance = data.importance
        if data.date is not None:
            competition.date = data.date
        if data.name is not None:
            competition.name = data.name
        if data.distance is not None:
            competition.distance = data.distance

        await self.db.flush()
        await self.db.refresh(competition)
        logger.info(f"Competition updated: id={competition_id} user={user_id}")
        return competition

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_competition(
        self, user_id: int, competition_id: int
    ) -> None:
        """
        Delete a competition.
        Also detaches any TrainingPlan that referenced this competition
        (plan.competition_id is SET NULL via FK cascade).
        """
        competition = await self._get_owned(user_id, competition_id)
        await self.db.delete(competition)
        await self.db.flush()
        logger.info(f"Competition deleted: id={competition_id} user={user_id}")

    # ------------------------------------------------------------------
    # Add result
    # ------------------------------------------------------------------

    async def add_result(
        self,
        user_id: int,
        competition_id: int,
        result_data: CompetitionResultRequest,
    ) -> Competition:
        """
        Record the actual race result.

        Stores finish time and comment in the competition's name/comment fields.
        Since the Competition model has no dedicated result columns, we encode
        the result into the name suffix and/or create a corresponding Workout
        entry for the race day with is_completed=True.

        Design note: The Competition model intentionally has no result fields
        to keep the schema simple for MVP. Results are stored as a completed
        Workout on the race day with race details in the comment field.
        This method creates that workout if it doesn't exist yet.
        """
        competition = await self._get_owned(user_id, competition_id)

        # Build result comment text
        parts = []
        if result_data.finish_time_seconds:
            total = result_data.finish_time_seconds
            h = total // 3600
            m = (total % 3600) // 60
            s = total % 60
            time_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
            parts.append(f"Результат: {time_str}")
        if result_data.result_comment:
            parts.append(result_data.result_comment)

        result_text = " | ".join(parts)

        # Create a completed workout for the race day if not already present
        from app.models.workout import Workout
        from app.utils.enums import WorkoutSource

        # Try to find existing completed workout on race day with same sport
        existing_result = await self.db.execute(
            select(Workout).where(
                Workout.user_id == user_id,
                Workout.date == competition.date,
                Workout.sport_type == competition.sport_type,
                Workout.is_completed == True,
            )
        )
        race_workout = existing_result.scalar_one_or_none()

        if race_workout is None:
            # Determine a reasonable race duration estimate from competition type
            duration = _estimate_race_duration(competition)
            if result_data.finish_time_seconds:
                duration = result_data.finish_time_seconds // 60

            race_workout = Workout(
                user_id=user_id,
                sport_type=competition.sport_type,
                source=WorkoutSource.MANUAL,
                date=competition.date,
                duration_minutes=max(1, duration),
                is_completed=True,
                comment=f"Гонка: {competition.name}" + (f"\n{result_text}" if result_text else ""),
            )
            self.db.add(race_workout)

        elif result_text:
            # Append result to existing workout comment
            existing_comment = race_workout.comment or ""
            race_workout.comment = (
                existing_comment.rstrip() + f"\n{result_text}" if existing_comment else result_text
            )

        await self.db.flush()
        await self.db.refresh(competition)
        logger.info(f"Race result recorded: competition_id={competition_id} user={user_id}")
        return competition


def _estimate_race_duration(competition: Competition) -> int:
    """
    Return a rough duration estimate in minutes based on competition type.
    Used when recording a result without an explicit finish time.
    """
    from app.utils.enums import CompetitionType

    estimates = {
        CompetitionType.RUN_5K: 30,
        CompetitionType.RUN_10K: 60,
        CompetitionType.HALF_MARATHON: 120,
        CompetitionType.MARATHON: 240,
        CompetitionType.SWIMMING: 60,
        CompetitionType.CYCLING: 120,
        CompetitionType.SUPER_SPRINT: 45,
        CompetitionType.SPRINT: 75,
        CompetitionType.OLYMPIC: 120,
        CompetitionType.HALF_IRON: 270,
        CompetitionType.IRON: 600,
    }
    return estimates.get(competition.competition_type, 60)
