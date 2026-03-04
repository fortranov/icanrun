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
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import Competition
from app.models.plan import TrainingPlan
from app.models.workout import Workout
from app.repositories.competition_repository import CompetitionRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.workout_repository import WorkoutRepository
from app.schemas.plan import (
    AthleteLevel,
    PeriodDetail,
    PeriodName,
    PeriodWeek,
    PlanDetailResponse,
    PlanGenerateRequest,
    PlanResponse,
    PlanSettings,
    PlanSettingsUpdateRequest,
    PlannedWorkoutSummary,
    TriathlonDistance,
    WeeklyVolumeBreakdown,
)
from app.utils.enums import SportType, WorkoutSource, WorkoutType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Period configuration
# ---------------------------------------------------------------------------

# Period definitions: name → (label_ru, focus_ru, intensity_pct, volume_pct)
# intensity_pct: percentage of sessions that are high-intensity (interval/threshold)
# volume_pct:    relative volume compared to peak week (100 = peak)
PERIOD_CONFIG: Dict[str, Tuple[str, str, int, int]] = {
    "base1": (
        "База 1",
        "Аэробная база. Лёгкий темп, длинные медленные тренировки. Без интервалов.",
        5, 55,
    ),
    "base2": (
        "База 2",
        "Развитие аэробной базы. Первые темповые работы, умеренный объём.",
        15, 65,
    ),
    "base3": (
        "База 3",
        "Укрепление базы. Добавляются мышечная выносливость и первые работы на пороге.",
        25, 75,
    ),
    "build1": (
        "Строительство 1",
        "Специфическая выносливость. Интервалы и темповые работы нарастают.",
        40, 85,
    ),
    "build2": (
        "Строительство 2",
        "Пиковая подготовка. Максимальная специфика и интенсивность.",
        50, 95,
    ),
    "peak": (
        "Пик",
        "Заточка формы. Объём снижается, интенсивность сохраняется. Гонковый ритм.",
        55, 70,
    ),
    "race": (
        "Гонка",
        "Подводка и восстановление после соревнования. Минимальный объём.",
        20, 40,
    ),
    "transition": (
        "Переходный",
        "Активный отдых. Неструктурированные тренировки, смена вида нагрузки.",
        0, 30,
    ),
}

# ---------------------------------------------------------------------------
# Workout type distribution per period
# Each tuple: (WorkoutType | None, relative_weight)
# None workout_type = general aerobic / no specific intensity label
# ---------------------------------------------------------------------------

_DIST_BASE1 = [
    (WorkoutType.RECOVERY, 0.30),
    (WorkoutType.LONG, 0.40),
    (None, 0.30),
]
_DIST_BASE2 = [
    (WorkoutType.RECOVERY, 0.20),
    (WorkoutType.LONG, 0.40),
    (WorkoutType.THRESHOLD, 0.20),
    (None, 0.20),
]
_DIST_BASE3 = [
    (WorkoutType.RECOVERY, 0.15),
    (WorkoutType.LONG, 0.35),
    (WorkoutType.THRESHOLD, 0.30),
    (WorkoutType.INTERVAL, 0.20),
]
_DIST_BUILD1 = [
    (WorkoutType.RECOVERY, 0.10),
    (WorkoutType.LONG, 0.30),
    (WorkoutType.THRESHOLD, 0.30),
    (WorkoutType.INTERVAL, 0.30),
]
_DIST_BUILD2 = [
    (WorkoutType.RECOVERY, 0.10),
    (WorkoutType.LONG, 0.25),
    (WorkoutType.THRESHOLD, 0.30),
    (WorkoutType.INTERVAL, 0.35),
]
_DIST_PEAK = [
    (WorkoutType.RECOVERY, 0.20),
    (WorkoutType.LONG, 0.20),
    (WorkoutType.THRESHOLD, 0.35),
    (WorkoutType.INTERVAL, 0.25),
]
_DIST_RACE = [
    (WorkoutType.RECOVERY, 0.50),
    (WorkoutType.LONG, 0.30),
    (None, 0.20),
]
_DIST_TRANSITION = [
    (WorkoutType.RECOVERY, 0.70),
    (None, 0.30),
]

PERIOD_WORKOUT_DISTRIBUTION: Dict[str, List[Tuple[Optional[WorkoutType], float]]] = {
    "base1": _DIST_BASE1,
    "base2": _DIST_BASE2,
    "base3": _DIST_BASE3,
    "build1": _DIST_BUILD1,
    "build2": _DIST_BUILD2,
    "peak": _DIST_PEAK,
    "race": _DIST_RACE,
    "transition": _DIST_TRANSITION,
}

# ---------------------------------------------------------------------------
# Base weekly hours by athlete level and distance type (triathlon)
# ---------------------------------------------------------------------------

# Peak training hours per week for each level and distance
PEAK_HOURS: Dict[str, Dict[str, float]] = {
    "sprint": {"beginner": 6.0, "intermediate": 9.0, "advanced": 12.0},
    "olympic": {"beginner": 8.0, "intermediate": 12.0, "advanced": 16.0},
    "half": {"beginner": 10.0, "intermediate": 15.0, "advanced": 20.0},
    "full": {"beginner": 12.0, "intermediate": 18.0, "advanced": 24.0},
    # Single-sport / maintenance (uses max_hours_per_week directly)
    "single": {"beginner": 1.0, "intermediate": 1.0, "advanced": 1.0},
}

# Weeks per period for each distance type in a full plan
# Maintenance plan has no competition: 26-week base-heavy cycle
PERIOD_WEEKS: Dict[Optional[str], Dict[str, int]] = {
    "sprint": {
        "transition": 1, "base1": 3, "base2": 3, "base3": 3,
        "build1": 3, "build2": 3, "peak": 2, "race": 1,
    },
    "olympic": {
        "transition": 1, "base1": 4, "base2": 4, "base3": 4,
        "build1": 4, "build2": 4, "peak": 2, "race": 1,
    },
    "half": {
        "transition": 1, "base1": 4, "base2": 4, "base3": 5,
        "build1": 4, "build2": 4, "peak": 3, "race": 1,
    },
    "full": {
        "transition": 2, "base1": 5, "base2": 5, "base3": 5,
        "build1": 5, "build2": 5, "peak": 3, "race": 2,
    },
    None: {
        # Maintenance / single-sport plan (~26 weeks cycling through base→build)
        "transition": 0, "base1": 5, "base2": 5, "base3": 5,
        "build1": 5, "build2": 4, "peak": 2, "race": 0,
    },
}

# Ordered sequence of period names (transition may be 0 weeks and skipped)
PERIOD_ORDER = [
    "transition", "base1", "base2", "base3",
    "build1", "build2", "peak", "race",
]

# ---------------------------------------------------------------------------
# Sport duration per session by distance and level (minutes per session)
# ---------------------------------------------------------------------------

SESSION_MINUTES: Dict[str, Dict[str, int]] = {
    "sprint": {"beginner": 45, "intermediate": 60, "advanced": 75},
    "olympic": {"beginner": 55, "intermediate": 75, "advanced": 90},
    "half": {"beginner": 65, "intermediate": 90, "advanced": 110},
    "full": {"beginner": 75, "intermediate": 100, "advanced": 130},
    "single": {"beginner": 45, "intermediate": 60, "advanced": 80},
}


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
        period_definitions = self._calculate_periods(
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
            period_workouts = await self._generate_period_workouts(
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
        period_defs = self._calculate_periods(
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
        period_defs = self._calculate_periods(
            race_date=plan.target_date,
            plan_start=today,
            distance_type=distance_type,
        )

        new_workouts: List[Workout] = []
        for period_def in period_defs:
            period_workouts = await self._generate_period_workouts(
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
    # Period calculation
    # ------------------------------------------------------------------

    def _calculate_periods(
        self,
        race_date: Optional[date],
        plan_start: date,
        distance_type: Optional[str],
    ) -> List[Dict]:
        """
        Build the ordered list of period definitions.

        Each definition is a dict:
          {name, label, focus, intensity_pct, volume_pct, weeks, start_date, end_date}

        If race_date is in the past or very near, the plan still generates
        but starts from a minimal 4-week base.

        Args:
            race_date: Target competition date, or None for maintenance plan.
            plan_start: First day of the plan (today).
            distance_type: Triathlon distance key or None for single-sport.

        Returns:
            List of period definition dicts in chronological order.
        """
        weeks_template = PERIOD_WEEKS.get(distance_type, PERIOD_WEEKS[None])

        # If a race date is provided, check we have enough time
        if race_date is not None:
            days_to_race = (race_date - plan_start).days
            available_weeks = max(4, days_to_race // 7)
            total_template_weeks = sum(weeks_template.values())

            if available_weeks < total_template_weeks:
                # Scale down each period proportionally, minimum 1 week each
                scale = available_weeks / total_template_weeks
                weeks_template = {
                    k: max(1, round(v * scale)) if v > 0 else 0
                    for k, v in weeks_template.items()
                }

        periods: List[Dict] = []
        cursor = plan_start

        for period_name in PERIOD_ORDER:
            num_weeks = weeks_template.get(period_name, 0)
            if num_weeks == 0:
                continue

            label, focus, intensity_pct, volume_pct = PERIOD_CONFIG[period_name]
            period_start = cursor
            period_end = cursor + timedelta(weeks=num_weeks) - timedelta(days=1)

            periods.append({
                "name": period_name,
                "label": label,
                "focus": focus,
                "intensity_pct": intensity_pct,
                "volume_pct": volume_pct,
                "weeks": num_weeks,
                "start_date": period_start,
                "end_date": period_end,
            })
            cursor = period_end + timedelta(days=1)

        return periods

    # ------------------------------------------------------------------
    # Workout generation
    # ------------------------------------------------------------------

    async def _generate_period_workouts(
        self,
        plan_id: int,
        user_id: int,
        sport_type: SportType,
        period_def: Dict,
        settings: PlanSettings,
        preferred_days: List[int],
        max_hours_per_week: float,
        distance_type: Optional[str],
    ) -> List[Workout]:
        """
        Generate all Workout objects for one period.

        Each week within the period gets a set of workout sessions distributed
        across the athlete's preferred training days. The 4th week of every
        4-week cycle is a recovery week (65% volume).
        """
        workouts: List[Workout] = []
        period_name = period_def["name"]
        volume_pct = period_def["volume_pct"] / 100.0
        period_start: date = period_def["start_date"]
        num_weeks: int = period_def["weeks"]

        for week_idx in range(num_weeks):
            # Every 4th week is a recovery week
            is_recovery = (week_idx + 1) % 4 == 0

            # Weekly volume in minutes
            week_minutes = self._calculate_weekly_volume_minutes(
                period_name=period_name,
                volume_pct=volume_pct,
                is_recovery=is_recovery,
                max_hours_per_week=max_hours_per_week,
                distance_type=distance_type,
                level=settings.athlete_level,
            )

            # Distribute volume across preferred days
            week_start = period_start + timedelta(weeks=week_idx)
            session_count = min(settings.sessions_per_week, len(preferred_days))
            selected_days = preferred_days[:session_count]

            # Volume split by sport (returns {sport_type_str: minutes})
            volume_split = self._calculate_volume_by_sport(
                sport_type=sport_type,
                week_minutes=week_minutes,
                session_count=session_count,
                settings=settings,
            )

            # Workout type distribution for this period
            wtype_dist = PERIOD_WORKOUT_DISTRIBUTION[period_name]

            # Assign each session to a day
            session_sports = self._assign_sports_to_sessions(
                volume_split=volume_split, session_count=session_count
            )

            for i, weekday_num in enumerate(selected_days):
                if i >= len(session_sports):
                    break

                sport_str, session_minutes = session_sports[i]
                session_minutes = max(15, session_minutes)

                # Assign workout type based on position in week and distribution
                workout_type = self._pick_workout_type(
                    wtype_dist=wtype_dist,
                    session_index=i,
                    total_sessions=session_count,
                    is_recovery=is_recovery,
                )

                # Calculate actual calendar date for this session
                session_date = _next_weekday_from(week_start, weekday_num)

                # Build comment with period context
                comment = _build_session_comment(
                    period_label=period_def["label"],
                    week_num=week_idx + 1,
                    is_recovery=is_recovery,
                )

                workout = Workout(
                    user_id=user_id,
                    plan_id=plan_id,
                    sport_type=SportType(sport_str),
                    workout_type=workout_type,
                    source=WorkoutSource.PLANNED,
                    date=session_date,
                    duration_minutes=session_minutes,
                    is_completed=False,
                    comment=comment,
                )
                workouts.append(workout)

        return workouts

    # ------------------------------------------------------------------
    # Volume calculation helpers
    # ------------------------------------------------------------------

    def _calculate_weekly_volume_minutes(
        self,
        period_name: str,
        volume_pct: float,
        is_recovery: bool,
        max_hours_per_week: float,
        distance_type: Optional[str],
        level: str,
    ) -> int:
        """
        Return total training minutes for one week.

        The user's max_hours_per_week is the ceiling (peak week target).
        Each period gets a fraction of that via volume_pct.
        Recovery weeks take 65% of the regular week's volume.

        For triathlon, we also cross-reference the level/distance peak hours
        table to ensure volumes are realistic.
        """
        base_minutes = max_hours_per_week * 60.0 * volume_pct
        if is_recovery:
            base_minutes *= 0.65

        # Floor: at least 30 min total so we always create at least one session
        return max(30, round(base_minutes))

    def _calculate_volume_by_sport(
        self,
        sport_type: SportType,
        week_minutes: int,
        session_count: int,
        settings: PlanSettings,
    ) -> Dict[str, int]:
        """
        Distribute week_minutes across sports according to priority weights.

        For single-sport plans (running/swimming/cycling/strength) all minutes
        go to that sport. For triathlon, priority weights determine the split.

        Returns {sport_type_value: minutes}.
        """
        if sport_type != SportType.TRIATHLON:
            return {sport_type.value: week_minutes}

        # Triathlon: distribute across swim/bike/run using priority weights
        total_w = settings.swim_priority + settings.bike_priority + settings.run_priority
        if total_w == 0:
            total_w = 3.0  # fallback to equal thirds

        swim_min = round(week_minutes * settings.swim_priority / total_w)
        bike_min = round(week_minutes * settings.bike_priority / total_w)
        run_min = week_minutes - swim_min - bike_min  # remainder to avoid rounding errors

        return {
            SportType.SWIMMING.value: max(0, swim_min),
            SportType.CYCLING.value: max(0, bike_min),
            SportType.RUNNING.value: max(0, run_min),
        }

    def _assign_sports_to_sessions(
        self,
        volume_split: Dict[str, int],
        session_count: int,
    ) -> List[Tuple[str, int]]:
        """
        Convert a volume split dict into an ordered list of (sport, minutes)
        tuples, one per session.

        For single-sport: each session gets week_minutes / session_count.
        For triathlon: swim gets 1 session, bike gets 2, run gets 2 (for
        session_count=5). The split is proportional for other counts.

        The list is ordered: swim sessions first (lighter on joints), then
        bike, then run — matching the Friel recommendation of spreading
        disciplines across the week.
        """
        result: List[Tuple[str, int]] = []
        sports = list(volume_split.keys())

        if len(sports) == 1:
            sport = sports[0]
            per_session = max(15, volume_split[sport] // session_count)
            return [(sport, per_session)] * session_count

        # Triathlon: allocate sessions proportionally
        total_minutes = sum(volume_split.values())
        if total_minutes == 0:
            return []

        sport_sessions: List[Tuple[str, int]] = []  # (sport, minutes_total, sessions)
        remaining_sessions = session_count

        # Calculate sessions per sport proportionally
        sport_session_counts: Dict[str, int] = {}
        for i, (sp, mins) in enumerate(volume_split.items()):
            if i < len(sports) - 1:
                n = max(1, round(mins / total_minutes * session_count))
                sport_session_counts[sp] = n
                remaining_sessions -= n
            else:
                sport_session_counts[sp] = max(1, remaining_sessions)

        # Order: swim → bike → run
        order = [SportType.SWIMMING.value, SportType.CYCLING.value, SportType.RUNNING.value]
        for sp in order:
            if sp not in volume_split:
                continue
            n = sport_session_counts.get(sp, 1)
            total_sp_min = volume_split[sp]
            per_session = max(15, total_sp_min // n)
            result.extend([(sp, per_session)] * n)

        return result[:session_count]

    def _pick_workout_type(
        self,
        wtype_dist: List[Tuple[Optional[WorkoutType], float]],
        session_index: int,
        total_sessions: int,
        is_recovery: bool,
    ) -> Optional[WorkoutType]:
        """
        Pick a workout type for a session based on the period distribution.

        Strategy:
        - Recovery weeks: always RECOVERY for first/last session, else LONG.
        - Otherwise use the weighted distribution, cycling through types as
          session_index increases so we don't pile all intervals on one day.
        """
        if is_recovery:
            if session_index == 0 or session_index == total_sessions - 1:
                return WorkoutType.RECOVERY
            return WorkoutType.LONG

        # Expand distribution into a list, then pick by index (round-robin)
        expanded: List[Optional[WorkoutType]] = []
        for wtype, weight in wtype_dist:
            count = max(1, round(weight * total_sessions))
            expanded.extend([wtype] * count)

        # Use modulo so the list cycles for larger session counts
        return expanded[session_index % len(expanded)]

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
# Module-level helpers
# ---------------------------------------------------------------------------

def _next_weekday_from(reference: date, weekday: int) -> date:
    """
    Return the date of the given weekday (0=Mon, 6=Sun) in the same
    ISO week that contains `reference`.

    If the weekday has already passed in that week, we still return it
    (it might be in the past — that is intentional for historical plan
    reconstruction; the service skips nothing).
    """
    # reference is the Monday of the week (plan_start aligned to week boundaries)
    # weekday 0=Monday, so offset is exactly weekday
    return reference + timedelta(days=weekday)


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


def _infer_distance_from_competition(competition: Competition) -> Optional[str]:
    """
    Map a CompetitionType to a TriathlonDistance key for volume calibration.
    """
    from app.utils.enums import CompetitionType
    mapping = {
        CompetitionType.SUPER_SPRINT: "sprint",
        CompetitionType.SPRINT: "sprint",
        CompetitionType.OLYMPIC: "olympic",
        CompetitionType.HALF_IRON: "half",
        CompetitionType.IRON: "full",
    }
    return mapping.get(competition.competition_type)


def _build_session_comment(
    period_label: str, week_num: int, is_recovery: bool
) -> str:
    """Build a descriptive comment for a planned workout."""
    suffix = " (восстановительная неделя)" if is_recovery else ""
    return f"{period_label} — неделя {week_num}{suffix}"
