"""
Pydantic schemas for TrainingPlan generation and responses.

Supports the Joe Friel periodization methodology for triathlon training.
Periods: Base 1/2/3 → Build 1/2 → Peak → Race → Transition
"""
from datetime import date, datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.utils.enums import SportType, WorkoutType

# ---------------------------------------------------------------------------
# Enum-like literals for plan settings
# ---------------------------------------------------------------------------

AthleteLevel = Literal["beginner", "intermediate", "advanced"]
TriathlonDistance = Literal["sprint", "olympic", "half", "full"]
PeriodName = Literal[
    "base1", "base2", "base3",
    "build1", "build2",
    "peak",
    "race",
    "transition",
]


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class PlanSettings(BaseModel):
    """
    Settings controlling how the Friel plan is generated.
    These can be updated later to trigger a plan recalculation.
    """
    athlete_level: AthleteLevel = "intermediate"
    # Used for triathlon plans to calibrate total weekly volume
    distance_type: Optional[TriathlonDistance] = None
    # Number of training days per week (drives workout count per week)
    sessions_per_week: int = Field(default=4, ge=3, le=6)
    # Relative priority weights for swim/bike/run. Will be normalised to sum=1.
    swim_priority: float = Field(default=1.0, ge=0.0, le=3.0)
    bike_priority: float = Field(default=1.0, ge=0.0, le=3.0)
    run_priority: float = Field(default=1.0, ge=0.0, le=3.0)
    # Current baseline pace / speed — used for future intensity zone calibration
    long_run_pace: Optional[float] = Field(default=None, ge=1.0, le=30.0,
        description="Long run pace in min/km (e.g. 5.5 = 5:30/km)")
    swim_pace_min: Optional[int] = Field(default=None, ge=0, le=10,
        description="Swim pace minutes part per 100m")
    swim_pace_sec: Optional[int] = Field(default=None, ge=0, le=59,
        description="Swim pace seconds part per 100m")
    long_ride_speed: Optional[float] = Field(default=None, ge=5.0, le=60.0,
        description="Long ride average speed in km/h")


class WeeklyVolumeBreakdown(BaseModel):
    """Minutes per sport discipline for one week."""
    swimming: int = 0
    cycling: int = 0
    running: int = 0
    strength: int = 0


class PlannedWorkoutSummary(BaseModel):
    """Lightweight summary of one planned workout inside a period week."""
    id: int
    sport_type: SportType
    workout_type: Optional[WorkoutType]
    date: date
    duration_minutes: int
    is_completed: bool
    comment: Optional[str]

    model_config = {"from_attributes": True}


class PeriodWeek(BaseModel):
    """One calendar week inside a training period."""
    week_number: int          # 1-based week index within the period
    start_date: date
    end_date: date
    is_recovery: bool         # True for every 4th week (reduced volume)
    total_minutes: int
    volume: WeeklyVolumeBreakdown
    workouts: List[PlannedWorkoutSummary] = []


class PeriodDetail(BaseModel):
    """
    One training period (Base1, Build1, Peak, …) with all its weeks
    and a description of the training focus.
    """
    name: PeriodName
    label: str                # Human-readable Russian label
    start_date: date
    end_date: date
    weeks: List[PeriodWeek]
    focus: str                # e.g. "Аэробная база, низкая интенсивность"
    # Intensity emphasis 0-100 (higher = more high-intensity work)
    intensity_pct: int
    # Volume relative to peak week (0-100)
    volume_pct: int


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class PlanGenerateRequest(BaseModel):
    """Request body for POST /plans/generate."""
    sport_type: SportType
    # Link to a key competition that the plan builds toward.
    # If None → 26-week maintenance plan (no tapering).
    competition_id: Optional[int] = None
    # Preferred training days: [0=Mon … 6=Sun]
    preferred_days: List[int] = Field(..., min_length=1, max_length=7)
    max_hours_per_week: float = Field(..., gt=0.0, le=40.0)
    settings: PlanSettings = Field(default_factory=PlanSettings)


class PlanSettingsUpdateRequest(BaseModel):
    """
    Request body for PATCH /plans/{id}/settings.
    All fields optional — only provided ones are changed before recalculating.
    """
    preferred_days: Optional[List[int]] = Field(None, min_length=1, max_length=7)
    max_hours_per_week: Optional[float] = Field(None, gt=0.0, le=40.0)
    settings: Optional[PlanSettings] = None


class PlanResponse(BaseModel):
    """Lightweight plan summary (list endpoint)."""
    id: int
    user_id: int
    sport_type: SportType
    competition_id: Optional[int]
    target_date: Optional[date]
    weeks_count: int
    preferred_days: List[int]
    max_hours_per_week: float
    is_active: bool
    created_at: datetime
    # Summary stats
    athlete_level: Optional[str] = None
    distance_type: Optional[str] = None
    sessions_per_week: Optional[int] = None

    model_config = {"from_attributes": True}


class PlanDetailResponse(PlanResponse):
    """Full plan detail including all periods and workouts."""
    periods: List[PeriodDetail] = []
    total_workouts: int = 0
    # Preview stats for UI
    preview_weeks: int = 0
    preview_total_hours: float = 0.0
