"""
Workout description generator — Joe Friel methodology.

Generates human-readable Russian-language workout descriptions based on:
  - Sport type (running / swimming / cycling / strength)
  - Workout type (recovery / aerobic / long / threshold / interval)
  - Duration in minutes
  - Athlete's baseline pace or speed

Pace zone formulas (relative to athlete's base pace):
  Running  (min/km):  easy      = base + 1:00
                      aerobic   = base + 0:30
                      threshold = base - 0:15
                      interval  = base - 0:30
  Cycling  (km/h):    easy      = base * 0.85
                      aerobic   = base * 0.90
                      threshold = base * 1.05
                      interval  = base * 1.10
  Swimming (min/100m):easy      = base + 0:20
                      aerobic   = base + 0:10
                      threshold = base - 0:05

All times are represented as integers (total seconds) internally
and formatted as M:SS or Xмин for display.
"""
from typing import Optional

from app.utils.enums import SportType, WorkoutType


# ---------------------------------------------------------------------------
# Pace helpers
# ---------------------------------------------------------------------------

def _fmt_run_pace(pace_min_per_km: float) -> str:
    """
    Format a float pace (min/km) to 'M:SS/км'.

    E.g. 5.5 -> '5:30/км', 6.0 -> '6:00/км', 4.75 -> '4:45/км'.
    """
    total_seconds = round(pace_min_per_km * 60)
    m, s = divmod(total_seconds, 60)
    return f"{m}:{s:02d}/км"


def _fmt_swim_pace(pace_total_seconds_per_100m: int) -> str:
    """
    Format total seconds per 100m to 'M:SS/100м'.

    E.g. 130 -> '2:10/100м'.
    """
    m, s = divmod(pace_total_seconds_per_100m, 60)
    return f"{m}:{s:02d}/100м"


def _fmt_speed(speed_kmh: float) -> str:
    """Format km/h to '%.1f км/ч'."""
    return f"{speed_kmh:.1f} км/ч"


def _fmt_duration(minutes: int) -> str:
    """Format minutes to 'Xч Yмин' or 'Xмин'."""
    if minutes >= 60:
        h, m = divmod(minutes, 60)
        if m == 0:
            return f"{h}ч"
        return f"{h}ч {m}мин"
    return f"{minutes}мин"


# ---------------------------------------------------------------------------
# Zone calculators
# ---------------------------------------------------------------------------

class RunZones:
    """
    Running intensity zones derived from the athlete's long-run baseline pace.

    Zone names follow Friel's convention:
      easy      — recovery + long runs, conversational
      aerobic   — general aerobic / zone 2–3
      threshold — lactate threshold, comfortably hard
      interval  — VO2max repeats, hard but controlled
    """

    def __init__(self, base_pace_min_per_km: float) -> None:
        self.base = base_pace_min_per_km
        # Faster = lower number, so add time for easier, subtract for harder
        self.easy      = base_pace_min_per_km + 1.0        # +1:00
        self.aerobic   = base_pace_min_per_km + 0.5        # +0:30
        self.threshold = base_pace_min_per_km - 0.25       # -0:15
        self.interval  = base_pace_min_per_km - 0.5        # -0:30

    @property
    def easy_str(self) -> str:
        return _fmt_run_pace(self.easy)

    @property
    def aerobic_str(self) -> str:
        return _fmt_run_pace(self.aerobic)

    @property
    def threshold_str(self) -> str:
        return _fmt_run_pace(self.threshold)

    @property
    def interval_str(self) -> str:
        return _fmt_run_pace(self.interval)


class CyclingZones:
    """
    Cycling intensity zones derived from the athlete's long-ride baseline speed.

    Expressed in km/h: higher speed = higher intensity.
    """

    def __init__(self, base_speed_kmh: float) -> None:
        self.base = base_speed_kmh
        self.easy      = base_speed_kmh * 0.85
        self.aerobic   = base_speed_kmh * 0.90
        self.threshold = base_speed_kmh * 1.05
        self.interval  = base_speed_kmh * 1.10

    @property
    def easy_str(self) -> str:
        return _fmt_speed(self.easy)

    @property
    def aerobic_str(self) -> str:
        return _fmt_speed(self.aerobic)

    @property
    def threshold_str(self) -> str:
        return _fmt_speed(self.threshold)

    @property
    def interval_str(self) -> str:
        return _fmt_speed(self.interval)


class SwimZones:
    """
    Swimming intensity zones derived from the athlete's long-swim baseline pace
    (seconds per 100m).

    Expressed in seconds/100m: higher = slower = easier.
    """

    def __init__(self, base_seconds_per_100m: int) -> None:
        self.base = base_seconds_per_100m
        self.easy      = base_seconds_per_100m + 20    # +0:20
        self.aerobic   = base_seconds_per_100m + 10    # +0:10
        self.threshold = base_seconds_per_100m - 5     # -0:05
        # No formal interval pace for swimming; use threshold as ceiling

    @property
    def easy_str(self) -> str:
        return _fmt_swim_pace(self.easy)

    @property
    def aerobic_str(self) -> str:
        return _fmt_swim_pace(self.aerobic)

    @property
    def threshold_str(self) -> str:
        return _fmt_swim_pace(self.threshold)


# ---------------------------------------------------------------------------
# Description generators per sport
# ---------------------------------------------------------------------------

def _describe_running(
    workout_type: Optional[WorkoutType],
    duration_minutes: int,
    zones: Optional[RunZones],
) -> str:
    """
    Generate a running workout description.

    Warm-up / main set / cool-down breakdown follows Friel conventions.
    If no pace data is provided, the description omits specific paces.
    """
    total = duration_minutes

    if workout_type == WorkoutType.RECOVERY:
        if zones:
            return (
                f"Лёгкий восстановительный бег {_fmt_duration(total)} "
                f"в темпе {zones.easy_str}. "
                f"Полностью аэробно, ЧСС не выше зоны 2."
            )
        return (
            f"Лёгкий восстановительный бег {_fmt_duration(total)}. "
            f"Полностью аэробно, ЧСС не выше зоны 2."
        )

    if workout_type == WorkoutType.AEROBIC:
        if zones:
            return (
                f"{_fmt_duration(total)} в аэробном темпе "
                f"({zones.aerobic_str}), зона 2–3."
            )
        return f"{_fmt_duration(total)} в аэробном темпе, зона 2–3."

    if workout_type == WorkoutType.LONG:
        # Structure: 15 min warm-up + main aerobic block + 10 min cool-down
        warmup   = 15
        cooldown = 10
        main     = max(10, total - warmup - cooldown)
        if zones:
            return (
                f"Разминка {warmup}мин в лёгком темпе ({zones.easy_str}), "
                f"основная часть {_fmt_duration(main)} в аэробном темпе "
                f"({zones.aerobic_str}), "
                f"заминка {cooldown}мин ({zones.easy_str})."
            )
        return (
            f"Разминка {warmup}мин, "
            f"основная часть {_fmt_duration(main)} в лёгком аэробном темпе, "
            f"заминка {cooldown}мин."
        )

    if workout_type == WorkoutType.THRESHOLD:
        # Structure: 15 min warm-up + threshold block + 10 min cool-down
        warmup   = 15
        cooldown = 10
        main     = max(10, total - warmup - cooldown)
        if zones:
            return (
                f"Разминка {warmup}мин, "
                f"{_fmt_duration(main)} в пороговом темпе "
                f"({zones.threshold_str}), "
                f"заминка {cooldown}мин."
            )
        return (
            f"Разминка {warmup}мин, "
            f"{_fmt_duration(main)} в пороговом темпе (зона 4), "
            f"заминка {cooldown}мин."
        )

    if workout_type == WorkoutType.INTERVAL:
        # Structure: 15 min warm-up + intervals + 10 min cool-down
        warmup   = 15
        cooldown = 10
        work_min = max(10, total - warmup - cooldown)
        # Each rep: 5 min work + 2 min rest = 7 min cycle
        rep_duration = 5   # minutes per interval
        rest_duration = 2  # minutes rest
        cycle = rep_duration + rest_duration
        reps = max(1, work_min // cycle)
        if zones:
            return (
                f"Разминка {warmup}мин, "
                f"затем {reps}×{rep_duration}мин в темпе {zones.interval_str} "
                f"/ отдых {rest_duration}мин трусцой, "
                f"заминка {cooldown}мин."
            )
        return (
            f"Разминка {warmup}мин, "
            f"затем {reps}×{rep_duration}мин в интервальном темпе (зона 5) "
            f"/ отдых {rest_duration}мин трусцой, "
            f"заминка {cooldown}мин."
        )

    # Fallback for any unrecognised workout type
    if zones:
        return (
            f"Бег {_fmt_duration(total)} "
            f"в аэробном темпе ({zones.aerobic_str}), зона 2–3."
        )
    return f"Бег {_fmt_duration(total)} в аэробном темпе, зона 2–3."


def _describe_cycling(
    workout_type: Optional[WorkoutType],
    duration_minutes: int,
    zones: Optional[CyclingZones],
) -> str:
    """Generate a cycling workout description."""
    total = duration_minutes

    if workout_type == WorkoutType.RECOVERY:
        if zones:
            return (
                f"Восстановительная поездка {_fmt_duration(total)} "
                f"в лёгком темпе ({zones.easy_str}). "
                f"Низкая интенсивность, зона 1–2."
            )
        return (
            f"Восстановительная поездка {_fmt_duration(total)}. "
            f"Низкая интенсивность, зона 1–2."
        )

    if workout_type == WorkoutType.AEROBIC:
        if zones:
            return (
                f"{_fmt_duration(total)} в аэробной зоне "
                f"({zones.aerobic_str}), зона 2–3."
            )
        return f"{_fmt_duration(total)} в аэробной зоне, зона 2–3."

    if workout_type == WorkoutType.LONG:
        warmup   = 15
        cooldown = 10
        main     = max(10, total - warmup - cooldown)
        if zones:
            return (
                f"Разминка {warmup}мин ({zones.easy_str}), "
                f"основная часть {_fmt_duration(main)} "
                f"в аэробной зоне ({zones.aerobic_str}), "
                f"заминка {cooldown}мин ({zones.easy_str})."
            )
        return (
            f"Разминка {warmup}мин, "
            f"основная часть {_fmt_duration(main)} в аэробной зоне, "
            f"заминка {cooldown}мин."
        )

    if workout_type == WorkoutType.THRESHOLD:
        warmup   = 15
        cooldown = 10
        main     = max(10, total - warmup - cooldown)
        if zones:
            return (
                f"Разминка {warmup}мин, "
                f"{_fmt_duration(main)} в пороговой зоне "
                f"({zones.threshold_str}), "
                f"заминка {cooldown}мин."
            )
        return (
            f"Разминка {warmup}мин, "
            f"{_fmt_duration(main)} в пороговой зоне (зона 4), "
            f"заминка {cooldown}мин."
        )

    if workout_type == WorkoutType.INTERVAL:
        warmup   = 15
        cooldown = 10
        work_min = max(10, total - warmup - cooldown)
        rep_duration  = 5
        rest_duration = 3
        cycle = rep_duration + rest_duration
        reps  = max(1, work_min // cycle)
        if zones:
            return (
                f"Разминка {warmup}мин, "
                f"затем {reps}×{rep_duration}мин "
                f"в интервальной зоне ({zones.interval_str}) "
                f"/ отдых {rest_duration}мин на низкой интенсивности, "
                f"заминка {cooldown}мин."
            )
        return (
            f"Разминка {warmup}мин, "
            f"затем {reps}×{rep_duration}мин в интервальной зоне (зона 5) "
            f"/ отдых {rest_duration}мин на низкой интенсивности, "
            f"заминка {cooldown}мин."
        )

    if zones:
        return (
            f"Поездка {_fmt_duration(total)} "
            f"в аэробной зоне ({zones.aerobic_str}), зона 2–3."
        )
    return f"Поездка {_fmt_duration(total)} в аэробной зоне, зона 2–3."


def _describe_swimming(
    workout_type: Optional[WorkoutType],
    duration_minutes: int,
    zones: Optional[SwimZones],
) -> str:
    """Generate a swimming workout description."""
    total = duration_minutes

    if workout_type == WorkoutType.RECOVERY:
        if zones:
            return (
                f"Лёгкий восстановительный заплыв {_fmt_duration(total)} "
                f"в темпе {zones.easy_str}. "
                f"Техника + дыхание, зона 1–2."
            )
        return (
            f"Лёгкий восстановительный заплыв {_fmt_duration(total)}. "
            f"Техника + дыхание, зона 1–2."
        )

    if workout_type == WorkoutType.AEROBIC:
        if zones:
            return (
                f"Непрерывный заплыв {_fmt_duration(total)} "
                f"в аэробном темпе ({zones.aerobic_str}), зона 2–3."
            )
        return (
            f"Непрерывный заплыв {_fmt_duration(total)} "
            f"в аэробном темпе, зона 2–3."
        )

    if workout_type == WorkoutType.LONG:
        warmup   = 10
        cooldown = 10
        main     = max(10, total - warmup - cooldown)
        if zones:
            return (
                f"Разминка {warmup}мин ({zones.easy_str}), "
                f"длительный непрерывный заплыв {_fmt_duration(main)} "
                f"в аэробном темпе ({zones.aerobic_str}), "
                f"заминка {cooldown}мин."
            )
        return (
            f"Разминка {warmup}мин, "
            f"длительный непрерывный заплыв {_fmt_duration(main)} "
            f"в аэробном темпе, "
            f"заминка {cooldown}мин."
        )

    if workout_type == WorkoutType.THRESHOLD:
        warmup   = 10
        cooldown = 10
        main     = max(10, total - warmup - cooldown)
        if zones:
            return (
                f"Разминка {warmup}мин, "
                f"{_fmt_duration(main)} в пороговом темпе "
                f"({zones.threshold_str}), "
                f"заминка {cooldown}мин."
            )
        return (
            f"Разминка {warmup}мин, "
            f"{_fmt_duration(main)} в пороговом темпе (зона 4), "
            f"заминка {cooldown}мин."
        )

    if workout_type == WorkoutType.INTERVAL:
        warmup   = 10
        cooldown = 10
        work_min = max(10, total - warmup - cooldown)
        # Swim intervals: 200m repeats ~3–4 min each with 45s rest
        rep_duration  = 4   # minutes per 200m rep
        rest_duration = 1   # minutes rest
        cycle = rep_duration + rest_duration
        reps  = max(1, work_min // cycle)
        if zones:
            return (
                f"Разминка {warmup}мин, "
                f"затем {reps}×200м в темпе {zones.threshold_str} "
                f"/ отдых 45 сек, "
                f"заминка {cooldown}мин."
            )
        return (
            f"Разминка {warmup}мин, "
            f"затем {reps}×200м в интенсивном темпе (зона 4–5) "
            f"/ отдых 45 сек, "
            f"заминка {cooldown}мин."
        )

    if zones:
        return (
            f"Заплыв {_fmt_duration(total)} "
            f"в аэробном темпе ({zones.aerobic_str}), зона 2–3."
        )
    return f"Заплыв {_fmt_duration(total)} в аэробном темпе, зона 2–3."


def _describe_strength(duration_minutes: int) -> str:
    """
    Generate a strength training description.

    Structure: 10 min warm-up + strength block + 10 min cool-down.
    The exercise list follows Friel's functional strength recommendations
    for endurance athletes.
    """
    total    = duration_minutes
    warmup   = 10
    cooldown = 10
    main     = max(10, total - warmup - cooldown)
    return (
        f"Силовая тренировка в тренажёрном зале. "
        f"Общая разминка {warmup}мин, "
        f"силовой блок {_fmt_duration(main)} "
        f"(приседания, становая тяга, жим, тяга, кор), "
        f"растяжка {cooldown}мин."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_workout_description(
    sport_type: SportType,
    workout_type: Optional[WorkoutType],
    duration_minutes: int,
    # Pace / speed parameters — all optional (plan may not include pace data)
    long_run_pace: Optional[float] = None,       # min/km (e.g. 5.5 = 5:30/km)
    swim_pace_min: Optional[int] = None,          # minutes part of pace/100m
    swim_pace_sec: Optional[int] = None,          # seconds part of pace/100m
    long_ride_speed: Optional[float] = None,      # km/h
    period_label: Optional[str] = None,           # e.g. "База 1"
    week_num: Optional[int] = None,               # 1-based week index within period
    cycle_week_label: Optional[str] = None,       # e.g. "базовая нагрузка", "восстановительная"
    # Kept for backward compatibility with existing callers / tests
    is_recovery_week: bool = False,
) -> str:
    """
    Generate a human-readable Russian-language description for a planned workout.

    The description includes:
      - Warm-up / main set / cool-down breakdown (where applicable)
      - Specific pace / speed targets derived from the athlete's baseline
      - Period context (period label + week number + cycle type) as a footer

    Args:
        sport_type: Running, swimming, cycling, strength, or triathlon.
        workout_type: Recovery, aerobic, long, threshold, or interval.
        duration_minutes: Total planned session duration.
        long_run_pace: Athlete's long-run baseline pace in min/km.
        swim_pace_min: Swim pace minutes component per 100m.
        swim_pace_sec: Swim pace seconds component per 100m.
        long_ride_speed: Athlete's long-ride baseline speed in km/h.
        period_label: Friel period name in Russian (appended to description).
        week_num: Week index within the period (1-based).
        cycle_week_label: Human-readable 3:1 cycle position, e.g. "пиковая".
        is_recovery_week: Deprecated — kept for backward compatibility.

    Returns:
        A ready-to-display string in Russian.
    """
    # Build pace/speed zone objects where data is available
    run_zones: Optional[RunZones] = (
        RunZones(long_run_pace) if long_run_pace is not None else None
    )
    cycling_zones: Optional[CyclingZones] = (
        CyclingZones(long_ride_speed) if long_ride_speed is not None else None
    )
    swim_zones: Optional[SwimZones] = None
    if swim_pace_min is not None and swim_pace_sec is not None:
        total_sec = swim_pace_min * 60 + swim_pace_sec
        swim_zones = SwimZones(total_sec)

    # Dispatch by sport
    if sport_type == SportType.STRENGTH:
        body = _describe_strength(duration_minutes)
    elif sport_type == SportType.RUNNING:
        body = _describe_running(workout_type, duration_minutes, run_zones)
    elif sport_type == SportType.CYCLING:
        body = _describe_cycling(workout_type, duration_minutes, cycling_zones)
    elif sport_type == SportType.SWIMMING:
        body = _describe_swimming(workout_type, duration_minutes, swim_zones)
    elif sport_type == SportType.TRIATHLON:
        # Triathlon workouts are sport-specific (swim/bike/run) but labelled
        # TRIATHLON at the plan level.  Treat as general aerobic without zones.
        body = (
            f"Тренировка по триатлону {_fmt_duration(duration_minutes)}. "
            f"Держите аэробную зону (зона 2–3), техника важнее скорости."
        )
    else:
        body = f"Тренировка {_fmt_duration(duration_minutes)}."

    # Append period + cycle context as a footer line
    if period_label and week_num is not None:
        # Prefer explicit cycle_week_label; fall back to legacy is_recovery_week flag
        if cycle_week_label:
            footer_suffix = f" ({cycle_week_label})"
        elif is_recovery_week:
            footer_suffix = " (восст. неделя)"
        else:
            footer_suffix = ""
        body = f"{body}\n{period_label} — неделя {week_num}{footer_suffix}"
    elif period_label:
        body = f"{body}\n{period_label}"

    return body
