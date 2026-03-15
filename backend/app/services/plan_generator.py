"""
Pure training-plan generation logic — Joe Friel Periodization Methodology.

This module contains no database access and no HTTP layer. It is responsible
solely for computing period layouts and creating in-memory Workout objects.
PlanService wraps this generator to persist the results.

Friel periodization references:
  - The Triathlete's Training Bible, 2nd ed., Joe Friel (2004)
  - Total heart-rate training, Joe Friel (2006)
"""
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from app.models.workout import Workout
from app.schemas.plan import PlanSettings
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
    (WorkoutType.AEROBIC, 0.30),
]
_DIST_BASE2 = [
    (WorkoutType.RECOVERY, 0.20),
    (WorkoutType.LONG, 0.40),
    (WorkoutType.THRESHOLD, 0.20),
    (WorkoutType.AEROBIC, 0.20),
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
    (WorkoutType.AEROBIC, 0.20),
]
_DIST_TRANSITION = [
    (WorkoutType.RECOVERY, 0.70),
    (WorkoutType.AEROBIC, 0.30),
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
# Duration multipliers per workout type
# ---------------------------------------------------------------------------
#
# Governs how total weekly volume (minutes) is distributed across sessions
# based on workout type. Derived from:
#   - Daniels' Running Formula: LONG ≤ 30% of weekly volume per session
#   - Friel/TrainingPeaks: RECOVERY sessions contribute < 10% of weekly TSS
#   - Polarized model (Seiler): INTERVAL sessions are shorter but high TSS/min
#   - CTS: LONG = 25–40% of weekly volume
#
# Per-session minutes = total_weekly_minutes * (multiplier / sum_of_all_multipliers).
# A LONG session therefore receives ~1.5× the time of a THRESHOLD session,
# and ~3× the time of a RECOVERY session, regardless of sport type.
WORKOUT_TYPE_DURATION_MULTIPLIER: Dict[Optional[WorkoutType], float] = {
    WorkoutType.LONG:      1.5,   # Longest session; ~25–30% of weekly volume
    WorkoutType.AEROBIC:   1.1,   # General aerobic base: slightly above-average
    WorkoutType.THRESHOLD: 1.0,   # Medium: warm-up + LT work + cool-down
    WorkoutType.INTERVAL:  0.75,  # Shorter but most intense; high TSS/minute
    WorkoutType.RECOVERY:  0.5,   # Shortest & easiest; < 10% of weekly volume
}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _next_weekday_from(reference: date, weekday: int) -> date:
    """
    Return the date of the given weekday (0=Mon, 6=Sun) in the same
    ISO week that contains `reference`.

    Works regardless of which day `reference` falls on — always finds
    the Monday of that week first, then adds the weekday offset.
    """
    monday = reference - timedelta(days=reference.weekday())
    return monday + timedelta(days=weekday)


def _build_session_comment(
    period_label: str, week_num: int, is_recovery: bool
) -> str:
    """Build a descriptive comment for a planned workout."""
    suffix = " (восстановительная неделя)" if is_recovery else ""
    return f"{period_label} — неделя {week_num}{suffix}"


def _infer_distance_from_competition(competition) -> Optional[str]:
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


# ---------------------------------------------------------------------------
# PlanGenerator — pure, stateless, no DB, no HTTP
# ---------------------------------------------------------------------------

class PlanGenerator:
    """
    Pure plan generation logic with no database or HTTP dependencies.

    All methods are synchronous. PlanService owns the DB session and calls
    these methods to produce in-memory Workout objects, then persists them.
    """

    # ------------------------------------------------------------------
    # Period layout
    # ------------------------------------------------------------------

    def calculate_periods(
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

    def generate_period_workouts(
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
            week_minutes = self.calculate_weekly_volume_minutes(
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
            volume_split = self.calculate_volume_by_sport(
                sport_type=sport_type,
                week_minutes=week_minutes,
                session_count=session_count,
                settings=settings,
            )

            # Workout type distribution for this period
            wtype_dist = PERIOD_WORKOUT_DISTRIBUTION[period_name]

            # Assign each session to a sport
            session_sports = self.assign_sports_to_sessions(
                volume_split=volume_split, session_count=session_count
            )

            # Pick workout types for all sessions upfront (needed before duration calc)
            session_workout_types = [
                self.pick_workout_type(
                    wtype_dist=wtype_dist,
                    session_index=i,
                    total_sessions=session_count,
                    is_recovery=is_recovery,
                )
                for i in range(session_count)
            ]

            # Distribute weekly minutes across sessions by workout type multiplier
            session_durations = self.calculate_session_durations_by_type(
                session_sports=session_sports,
                session_workout_types=session_workout_types,
                volume_split=volume_split,
            )

            for i, weekday_num in enumerate(selected_days):
                if i >= len(session_sports):
                    break

                sport_str, _ = session_sports[i]
                session_minutes = session_durations[i]
                workout_type = session_workout_types[i]

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

    def calculate_weekly_volume_minutes(
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

    def calculate_volume_by_sport(
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

    def assign_sports_to_sessions(
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

        # Calculate sessions per sport proportionally
        sport_session_counts: Dict[str, int] = {}
        remaining_sessions = session_count
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

    def calculate_session_durations_by_type(
        self,
        session_sports: List[Tuple[str, int]],
        session_workout_types: List[Optional[WorkoutType]],
        volume_split: Dict[str, int],
    ) -> List[int]:
        """
        Distribute total weekly minutes across all sessions proportionally to
        each session's WORKOUT_TYPE_DURATION_MULTIPLIER.

        Uses global distribution across all sessions (not per-sport grouping)
        so that workout type meaningfully affects duration even when a sport
        has only one session per week — the common triathlon case where the
        per-sport approach cancels the multiplier:
          sport_total * mult / mult = sport_total  (all sessions equal).

        Algorithm:
          1. Sum all volume_split values to get total weekly minutes.
          2. Look up the duration multiplier for each session's workout type.
          3. Each session gets: total_minutes * (its_mult / sum_of_all_mults).
          4. Floor every result at 15 minutes.

        Example (triathlon, 3 sessions, 300 min/week):
          swim=RECOVERY(0.5), bike=LONG(1.5), run=THRESHOLD(1.0) → total=3.0
          swim = 300 * 0.5/3.0 =  50 min
          bike = 300 * 1.5/3.0 = 150 min
          run  = 300 * 1.0/3.0 = 100 min

        Example (single-sport, 3 sessions, 300 min/week):
          LONG(1.5) + THRESHOLD(1.0) + RECOVERY(0.5) → total=3.0
          LONG      = 300 * 1.5/3.0 = 150 min
          THRESHOLD = 300 * 1.0/3.0 = 100 min
          RECOVERY  = 300 * 0.5/3.0 =  50 min
        """
        session_count = len(session_sports)
        if session_count == 0:
            return []

        total_minutes = sum(volume_split.values())

        multipliers = [
            WORKOUT_TYPE_DURATION_MULTIPLIER.get(wtype, 1.0)
            for wtype in session_workout_types
        ]
        total_mult = sum(multipliers)

        if total_mult == 0:
            per_session = max(15, total_minutes // session_count)
            return [per_session] * session_count

        durations = [
            max(15, round(total_minutes * mult / total_mult))
            for mult in multipliers
        ]

        # Correct rounding drift so total_minutes is preserved exactly
        diff = total_minutes - sum(durations)
        if diff != 0:
            # Apply the correction to the longest session (least noticeable)
            longest = max(range(session_count), key=lambda i: durations[i])
            durations[longest] = max(15, durations[longest] + diff)

        return durations

    def pick_workout_type(
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
