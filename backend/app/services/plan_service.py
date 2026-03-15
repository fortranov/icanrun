"""
Training Plan Service — Joe Friel Periodization Methodology.

Implements the classic Friel macro-cycle structure used in "The Triathlete's
Training Bible":

  Transition → Base 1 → Base 2 → Base 3 →
  Build 1 → Build 2 → Peak → Race (→ Transition)

Each period has a defined volume multiplier and intensity emphasis.
Every 4th week is a recovery week at ~65% of the previous week's volume.

The generated plan creates Workout records (source=PLANNED) in the database.
When deleting a plan, future planned workouts are removed; past workouts
(historical data) are preserved with plan_id set to NULL via FK cascade.

Volume distribution by sport is governed by priority weights provided by the
athlete, normalised against the total. For triathlon plans the sport_type is
set to TRIATHLON and workouts are distributed across swim/bike/run.
For single-sport plans all volume goes to that sport.

Friel periodization references
  - The Triathlete's Training Bible, 2nd ed., Joe Friel (2004)
  - Total heart-rate training, Joe Friel (2006)
"""
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import Competition
from app.models.plan import TrainingPlan
from app.models.workout import Workout
from app.repositories.competition_repository import CompetitionRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.workout_repository import WorkoutRepository
from app.schemas.plan import (
    PeriodDetail,
    PeriodWeek,
    PlanDetailResponse,
    PlanGenerateRequest,
    PlanResponse,
    PlanSettings,
    PlanSettingsUpdateRequest,
    PlannedWorkoutSummary,
    WeeklyVolumeBreakdown,
)
from app.services.plan_generator import PlanGenerator, _infer_distance_from_competition
from app.utils.enums import SportType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Plan Service
# ---------------------------------------------------------------------------

class PlanService:
    """
    Generates and manages Joe Friel periodized training plans.

    The service creates Workout records (source=PLANNED) for each session in
    the plan.  Workouts are linked back to the TrainingPlan via plan_id so
    they can be found and deleted when the plan is removed.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.plan_repo = PlanRepository(db)
        self.workout_repo = WorkoutRepository(db)
        self.competition_repo = CompetitionRepository(db)
        self.generator = PlanGenerator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_plan(
        self, user_id: int, data: PlanGenerateRequest
    ) -> PlanDetailResponse:
        """
        Generate a new training plan and persist all planned workouts.

        Steps:
          1. Validate competition ownership (if competition_id given).
          2. Deactivate any existing active plan for the same sport.
          3. Calculate period layout from today → race date.
          4. For each week in each period, create Workout records.
          5. Persist TrainingPlan record.
          6. Return full PlanDetailResponse.
        """
        competition: Optional[Competition] = None
        target_date: Optional[date] = None

        if data.competition_id is not None:
            competition = await self._get_owned_competition(user_id, data.competition_id)
            target_date = competition.date

        plan_start = date.today()

        # Determine distance_type for triathlon plans
        distance_type: Optional[str] = data.settings.distance_type
        if data.sport_type == SportType.TRIATHLON and not distance_type:
            # Infer from competition type if possible
            if competition is not None:
                distance_type = _infer_distance_from_competition(competition)
            if not distance_type:
                distance_type = "olympic"  # safe default

        # Deactivate any existing active plan for this sport
        existing = await self.plan_repo.get_active_by_user_and_sport(
            user_id, data.sport_type
        )
        if existing:
            existing.is_active = False
            await self.db.flush()

        # Determine period layout
        period_definitions = self.generator.calculate_periods(
            race_date=target_date,
            plan_start=plan_start,
            distance_type=distance_type,
        )

        total_weeks = sum(p["weeks"] for p in period_definitions)

        # Persist the plan record first (so we have plan.id for workouts)
        plan = TrainingPlan(
            user_id=user_id,
            sport_type=data.sport_type,
            competition_id=data.competition_id,
            target_date=target_date,
            weeks_count=total_weeks,
            preferred_days=data.preferred_days,
            max_hours_per_week=data.max_hours_per_week,
            is_active=True,
        )
        self.db.add(plan)
        await self.db.flush()  # assign plan.id

        # Generate and persist workouts
        all_workouts: List[Workout] = []
        for period_def in period_definitions:
            period_workouts = self.generator.generate_period_workouts(
                plan_id=plan.id,
                user_id=user_id,
                sport_type=data.sport_type,
                period_def=period_def,
                settings=data.settings,
                preferred_days=sorted(data.preferred_days),
                max_hours_per_week=data.max_hours_per_week,
                distance_type=distance_type,
            )
            all_workouts.extend(period_workouts)

        for w in all_workouts:
            self.db.add(w)
        await self.db.flush()

        await self.db.refresh(plan)

        logger.info(
            f"Plan generated: id={plan.id} user={user_id} sport={data.sport_type} "
            f"weeks={total_weeks} workouts={len(all_workouts)}"
        )

        return await self._build_detail_response(plan, all_workouts, period_definitions)

    async def get_plan(self, user_id: int, plan_id: int) -> PlanDetailResponse:
        """Return full plan detail with all workouts grouped by period."""
        plan = await self._get_owned_plan(user_id, plan_id)
        workouts = await self.workout_repo.get_by_plan(plan_id)
        # Reconstruct period layout from plan metadata
        distance_type = self._extract_distance_type(plan)
        period_defs = self.generator.calculate_periods(
            race_date=plan.target_date,
            plan_start=plan.created_at.date(),
            distance_type=distance_type,
        )
        return await self._build_detail_response(plan, workouts, period_defs)

    async def get_user_plans(self, user_id: int) -> List[PlanResponse]:
        """Return summary list of all active plans for the user."""
        plans = await self.plan_repo.get_active_by_user(user_id)
        return [PlanResponse.model_validate(p) for p in plans]

    async def update_plan_settings(
        self, user_id: int, plan_id: int, data: PlanSettingsUpdateRequest
    ) -> PlanDetailResponse:
        """
        Recalculate the plan with new settings.

        Future unstarted workouts are deleted and regenerated.
        Past workouts (is_completed=True or date < today) are preserved.
        """
        plan = await self._get_owned_plan(user_id, plan_id)

        # Apply setting overrides
        if data.preferred_days is not None:
            plan.preferred_days = data.preferred_days
        if data.max_hours_per_week is not None:
            plan.max_hours_per_week = data.max_hours_per_week
        await self.db.flush()

        # Delete all future planned workouts belonging to this plan
        today = date.today()
        future_workouts = await self.workout_repo.get_future_planned(plan_id, today)
        for w in future_workouts:
            await self.db.delete(w)
        await self.db.flush()

        # Rebuild settings from request or use defaults
        settings = data.settings or PlanSettings()
        distance_type = settings.distance_type or self._extract_distance_type(plan)

        # Regenerate plan workouts from today
        period_defs = self.generator.calculate_periods(
            race_date=plan.target_date,
            plan_start=today,
            distance_type=distance_type,
        )

        new_workouts: List[Workout] = []
        for period_def in period_defs:
            period_workouts = self.generator.generate_period_workouts(
                plan_id=plan.id,
                user_id=user_id,
                sport_type=plan.sport_type,
                period_def=period_def,
                settings=settings,
                preferred_days=sorted(plan.preferred_days),
                max_hours_per_week=plan.max_hours_per_week,
                distance_type=distance_type,
            )
            new_workouts.extend(period_workouts)

        for w in new_workouts:
            self.db.add(w)
        await self.db.flush()
        await self.db.refresh(plan)

        # Combine preserved past workouts + new future workouts
        past_workouts = await self.workout_repo.get_by_plan(plan_id)
        logger.info(
            f"Plan updated: id={plan_id} user={user_id} "
            f"new_workouts={len(new_workouts)}"
        )
        return await self._build_detail_response(plan, past_workouts, period_defs)

    async def delete_plan(self, user_id: int, plan_id: int) -> None:
        """
        Delete the plan and all future planned workouts.

        Past workouts (date < today) have their plan_id set to NULL by the
        FK cascade (ondelete="SET NULL") so historical data is not lost.
        Future unstarted workouts are explicitly deleted.
        """
        plan = await self._get_owned_plan(user_id, plan_id)

        today = date.today()
        future_workouts = await self.workout_repo.get_future_planned(plan_id, today)
        for w in future_workouts:
            await self.db.delete(w)
        await self.db.flush()

        await self.db.delete(plan)
        await self.db.flush()
        logger.info(
            f"Plan deleted: id={plan_id} user={user_id} "
            f"future_workouts_removed={len(future_workouts)}"
        )

    # ------------------------------------------------------------------
    # Response builder
    # ------------------------------------------------------------------

    async def _build_detail_response(
        self,
        plan: TrainingPlan,
        workouts: List[Workout],
        period_defs: List[Dict],
    ) -> PlanDetailResponse:
        """
        Assemble a PlanDetailResponse from the plan record, flat workout list,
        and period definitions.

        Workouts are grouped into their respective period by date range.
        """
        # Index workouts by date for fast lookup
        workout_by_date: Dict[date, List[Workout]] = {}
        for w in workouts:
            workout_by_date.setdefault(w.date, []).append(w)

        periods: List[PeriodDetail] = []
        total_minutes = 0

        for period_def in period_defs:
            period_weeks: List[PeriodWeek] = []
            p_start: date = period_def["start_date"]
            num_weeks: int = period_def["weeks"]
            period_name: str = period_def["name"]

            for week_idx in range(num_weeks):
                is_recovery = (week_idx + 1) % 4 == 0
                week_start = p_start + timedelta(weeks=week_idx)
                week_end = week_start + timedelta(days=6)

                # Collect workouts for this week
                week_workouts: List[Workout] = []
                cur = week_start
                while cur <= week_end:
                    week_workouts.extend(workout_by_date.get(cur, []))
                    cur += timedelta(days=1)

                week_total = sum(w.duration_minutes for w in week_workouts)
                total_minutes += week_total

                volume = _build_volume_breakdown(week_workouts)

                period_weeks.append(PeriodWeek(
                    week_number=week_idx + 1,
                    start_date=week_start,
                    end_date=week_end,
                    is_recovery=is_recovery,
                    total_minutes=week_total,
                    volume=volume,
                    workouts=[PlannedWorkoutSummary(
                        id=w.id,
                        sport_type=w.sport_type,
                        workout_type=w.workout_type,
                        date=w.date,
                        duration_minutes=w.duration_minutes,
                        is_completed=w.is_completed,
                        comment=w.comment,
                    ) for w in sorted(week_workouts, key=lambda x: x.date)],
                ))

            periods.append(PeriodDetail(
                name=period_name,
                label=period_def["label"],
                start_date=period_def["start_date"],
                end_date=period_def["end_date"],
                weeks=period_weeks,
                focus=period_def["focus"],
                intensity_pct=period_def["intensity_pct"],
                volume_pct=period_def["volume_pct"],
            ))

        return PlanDetailResponse(
            id=plan.id,
            user_id=plan.user_id,
            sport_type=plan.sport_type,
            competition_id=plan.competition_id,
            target_date=plan.target_date,
            weeks_count=plan.weeks_count,
            preferred_days=plan.preferred_days,
            max_hours_per_week=plan.max_hours_per_week,
            is_active=plan.is_active,
            created_at=plan.created_at,
            periods=periods,
            total_workouts=len(workouts),
            preview_weeks=plan.weeks_count,
            preview_total_hours=round(total_minutes / 60, 1),
        )

    # ------------------------------------------------------------------
    # Ownership & validation helpers
    # ------------------------------------------------------------------

    async def _get_owned_plan(self, user_id: int, plan_id: int) -> TrainingPlan:
        plan = await self.plan_repo.get_by_id(plan_id)
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Training plan not found",
            )
        if plan.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return plan

    async def _get_owned_competition(
        self, user_id: int, competition_id: int
    ) -> Competition:
        competition = await self.competition_repo.get_by_id(competition_id)
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

    def _extract_distance_type(self, plan: TrainingPlan) -> Optional[str]:
        """
        Attempt to retrieve distance_type stored in plan metadata.
        Currently the TrainingPlan model does not store settings directly;
        for now we return None (maintenance) and let callers provide settings.
        """
        # TODO: Consider adding a JSON settings column to TrainingPlan model
        # to persist athlete_level and distance_type across plan updates.
        return None


# ---------------------------------------------------------------------------
# Module-level helpers (used only within this module)
# ---------------------------------------------------------------------------

def _build_volume_breakdown(workouts: List[Workout]) -> WeeklyVolumeBreakdown:
    """Aggregate workout minutes by sport for a week."""
    v = WeeklyVolumeBreakdown()
    for w in workouts:
        if w.sport_type == SportType.SWIMMING:
            v.swimming += w.duration_minutes
        elif w.sport_type == SportType.CYCLING:
            v.cycling += w.duration_minutes
        elif w.sport_type == SportType.RUNNING:
            v.running += w.duration_minutes
        elif w.sport_type == SportType.STRENGTH:
            v.strength += w.duration_minutes
        elif w.sport_type == SportType.TRIATHLON:
            # Combined triathlon workouts go into running (closest overall)
            v.running += w.duration_minutes
    return v
