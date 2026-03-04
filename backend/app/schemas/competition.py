"""
Pydantic schemas for Competition CRUD.
"""
import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field

from app.utils.enums import CompetitionImportance, CompetitionType, SportType


class CompetitionCreate(BaseModel):
    sport_type: SportType
    competition_type: CompetitionType
    importance: CompetitionImportance = CompetitionImportance.KEY
    date: dt.date
    name: str = Field(..., min_length=1, max_length=255)
    distance: Optional[float] = Field(None, gt=0)


class CompetitionUpdate(BaseModel):
    sport_type: Optional[SportType] = None
    competition_type: Optional[CompetitionType] = None
    importance: Optional[CompetitionImportance] = None
    date: Optional[dt.date] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    distance: Optional[float] = Field(None, gt=0)


class CompetitionResultRequest(BaseModel):
    """Record the actual result of a competition."""
    finish_time_seconds: Optional[int] = Field(None, gt=0, description="Total finish time in seconds")
    result_comment: Optional[str] = Field(None, max_length=2000)


class CompetitionFilters(BaseModel):
    """Query filters for listing competitions."""
    sport_type: Optional[SportType] = None
    importance: Optional[CompetitionImportance] = None
    date_from: Optional[dt.date] = None
    date_to: Optional[dt.date] = None


class CompetitionResponse(BaseModel):
    id: int
    user_id: int
    sport_type: SportType
    competition_type: CompetitionType
    importance: CompetitionImportance
    date: dt.date
    name: str
    distance: Optional[float]
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class CompetitionListResponse(BaseModel):
    items: List[CompetitionResponse]
    total: int
