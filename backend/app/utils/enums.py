"""
All application enums used across models, schemas, and services.
"""
from enum import Enum


class SportType(str, Enum):
    RUNNING = "running"
    SWIMMING = "swimming"
    CYCLING = "cycling"
    STRENGTH = "strength"
    TRIATHLON = "triathlon"


class WorkoutType(str, Enum):
    RECOVERY = "recovery"
    LONG = "long"
    INTERVAL = "interval"
    THRESHOLD = "threshold"
    AEROBIC = "aerobic"


class WorkoutSource(str, Enum):
    PLANNED = "planned"      # Created within a training plan
    MANUAL = "manual"        # Created manually by the user
    GARMIN = "garmin"        # Imported from Garmin Connect
    STRAVA = "strava"        # Imported from Strava


class CompetitionType(str, Enum):
    # Running distances
    RUN_5K = "run_5k"
    RUN_10K = "run_10k"
    HALF_MARATHON = "half_marathon"
    MARATHON = "marathon"
    # Swimming (distance in meters stored in Competition.distance)
    SWIMMING = "swimming"
    # Cycling (distance in km stored in Competition.distance)
    CYCLING = "cycling"
    # Triathlon formats
    SUPER_SPRINT = "super_sprint"
    SPRINT = "sprint"
    OLYMPIC = "olympic"
    HALF_IRON = "half_iron"
    IRON = "iron"


class CompetitionImportance(str, Enum):
    KEY = "key"              # A-priority race, plan peaks toward this
    SECONDARY = "secondary"  # B-priority race, no special tapering


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class SubscriptionPlan(str, Enum):
    TRIAL = "trial"    # 30 days, all features enabled
    BASIC = "basic"    # Paid: workouts + integrations, no plan generation
    PRO = "pro"        # Paid: all features including plan generation


class TrainingPhase(str, Enum):
    """Friel periodization phases used in plan generation."""
    BASE = "base"      # >16 weeks to competition: aerobic base building
    BUILD = "build"    # 8-16 weeks: add intervals and threshold work
    PEAK = "peak"      # <8 weeks: high intensity, controlled volume
    TAPER = "taper"    # Last 2-3 weeks: reduce volume 30-50%


class PeriodName(str, Enum):
    """Granular Friel period names within phases."""
    BASE1 = "base1"
    BASE2 = "base2"
    BASE3 = "base3"
    BUILD1 = "build1"
    BUILD2 = "build2"
    PEAK = "peak"
    RACE = "race"
    TRANSITION = "transition"


class AthleteLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TriathlonDistance(str, Enum):
    SPRINT = "sprint"
    OLYMPIC = "olympic"
    HALF = "half"
    FULL = "full"
