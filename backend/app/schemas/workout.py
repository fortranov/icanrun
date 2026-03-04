"""
Pydantic schemas for Workout CRUD.
"""
import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field

from app.utils.enums import SportType, WorkoutSource, WorkoutType


class WorkoutCreate(BaseModel):
    sport_type: SportType
    workout_type: Optional[WorkoutType] = None
    date: dt.date
    duration_minutes: int = Field(..., gt=0, le=1440)
    comment: Optional[str] = Field(None, max_length=2000)


class WorkoutUpdate(BaseModel):
    sport_type: Optional[SportType] = None
    workout_type: Optional[WorkoutType] = None
    date: Optional[dt.date] = None
    duration_minutes: Optional[int] = Field(None, gt=0, le=1440)
    comment: Optional[str] = Field(None, max_length=2000)
    is_completed: Optional[bool] = None


class WorkoutCompleteRequest(BaseModel):
    """Mark a workout as completed, optionally overriding the actual duration."""
    actual_duration_minutes: Optional[int] = Field(None, gt=0, le=1440)
    comment: Optional[str] = Field(None, max_length=2000)


class WorkoutMoveRequest(BaseModel):
    """Request to move a workout to a different date (drag-and-drop)."""
    new_date: dt.date


class WorkoutFilters(BaseModel):
    """Query filters for listing workouts."""
    date_from: Optional[dt.date] = None
    date_to: Optional[dt.date] = None
    sport_type: Optional[SportType] = None
    is_completed: Optional[bool] = None
    year: Optional[int] = Field(None, ge=2000, le=2100)
    month: Optional[int] = Field(None, ge=1, le=12)
    skip: int = Field(0, ge=0)
    limit: int = Field(200, ge=1, le=500)


class WorkoutResponse(BaseModel):
    id: int
    user_id: int
    sport_type: SportType
    workout_type: Optional[WorkoutType]
    source: WorkoutSource
    date: dt.date
    duration_minutes: int
    is_completed: bool
    comment: Optional[str]
    plan_id: Optional[int]
    garmin_activity_id: Optional[str]
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class WorkoutListResponse(BaseModel):
    items: List[WorkoutResponse]
    total: int
