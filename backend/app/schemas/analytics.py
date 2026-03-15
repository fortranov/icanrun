"""
Pydantic schemas for analytics/statistics endpoints.
"""
from typing import Dict, Optional
from pydantic import BaseModel


class SportBreakdown(BaseModel):
    """Minutes and count for a single sport type."""
    total_minutes: int = 0
    completed_minutes: int = 0
    total_workouts: int = 0
    completed_workouts: int = 0


class MonthlyStats(BaseModel):
    """Aggregate statistics for one calendar month."""
    year: int
    month: int
    total_minutes: int
    completed_minutes: int
    total_workouts: int
    completed_workouts: int
    # Completion rate computed only from workouts on/before today (past days).
    # 0.0–100.0
    completion_rate: float
    # Counts used for the completion_rate denominator (past days only).
    past_total_workouts: int = 0
    past_completed_workouts: int = 0
    # sport_type_value → breakdown
    by_sport: Dict[str, SportBreakdown] = {}


class DayStats(BaseModel):
    """Per-day statistics — used for bar chart data."""
    date: str                # "YYYY-MM-DD"
    completed_minutes: int
    planned_minutes: int     # Planned but NOT completed (shown lighter on chart)
    total_minutes: int       # completed + planned (= bar height)


class DailyStatsResponse(BaseModel):
    """Wrapper for the daily stats list."""
    year: int
    month: int
    days: list[DayStats]
    summary: MonthlyStats
