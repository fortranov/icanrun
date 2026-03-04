"""
Tests for the analytics service and endpoints.

Covers:
  - Monthly stats: total, completed, by_sport breakdown
  - Daily stats: one entry per day, zero-filled for empty days
  - Sport filter: returns only matching sport
  - Completion rate calculation
"""
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workout import Workout
from app.models.user import User
from app.utils.enums import SportType, WorkoutSource
from tests.conftest import get_auth_headers


async def _create_workout(
    db: AsyncSession,
    user_id: int,
    sport: SportType,
    duration: int,
    workout_date: date,
    is_completed: bool = True,
) -> Workout:
    w = Workout(
        user_id=user_id,
        sport_type=sport,
        source=WorkoutSource.MANUAL,
        date=workout_date,
        duration_minutes=duration,
        is_completed=is_completed,
    )
    db.add(w)
    await db.flush()
    return w


# ---------------------------------------------------------------------------
# Monthly stats
# ---------------------------------------------------------------------------

async def test_monthly_stats_empty_month(client: AsyncClient, regular_user: User):
    """Stats for an empty month return zeros."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    r = await client.get(
        "/api/v1/analytics/monthly",
        params={"year": 2010, "month": 1},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_minutes"] == 0
    assert data["total_workouts"] == 0
    assert data["completion_rate"] == 0.0


async def test_monthly_stats_with_workouts(
    client: AsyncClient, regular_user: User, db_session: AsyncSession
):
    """Stats reflect all workouts in the month."""
    year, month = 2025, 6
    await _create_workout(
        db_session, regular_user.id, SportType.RUNNING, 60,
        date(year, month, 5), is_completed=True
    )
    await _create_workout(
        db_session, regular_user.id, SportType.CYCLING, 90,
        date(year, month, 10), is_completed=False
    )
    await _create_workout(
        db_session, regular_user.id, SportType.RUNNING, 45,
        date(year, month, 15), is_completed=True
    )

    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    r = await client.get(
        "/api/v1/analytics/monthly",
        params={"year": year, "month": month},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_workouts"] == 3
    assert data["completed_workouts"] == 2
    assert data["total_minutes"] == 195  # 60 + 90 + 45
    assert data["completed_minutes"] == 105  # 60 + 45
    assert data["completion_rate"] == pytest.approx(66.7, abs=0.5)

    # Sport breakdown
    assert "running" in data["by_sport"]
    running = data["by_sport"]["running"]
    assert running["total_workouts"] == 2
    assert running["total_minutes"] == 105
    assert running["completed_workouts"] == 2

    assert "cycling" in data["by_sport"]
    cycling = data["by_sport"]["cycling"]
    assert cycling["total_workouts"] == 1
    assert cycling["completed_workouts"] == 0


async def test_monthly_stats_sport_filter(
    client: AsyncClient, regular_user: User, db_session: AsyncSession
):
    """Sport filter returns only matching sport workouts."""
    year, month = 2025, 7
    await _create_workout(
        db_session, regular_user.id, SportType.RUNNING, 60,
        date(year, month, 1), is_completed=True
    )
    await _create_workout(
        db_session, regular_user.id, SportType.SWIMMING, 45,
        date(year, month, 2), is_completed=True
    )

    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    r = await client.get(
        "/api/v1/analytics/monthly",
        params={"year": year, "month": month, "sport": "swimming"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_workouts"] == 1
    assert data["total_minutes"] == 45
    assert "running" not in data["by_sport"]


# ---------------------------------------------------------------------------
# Daily stats
# ---------------------------------------------------------------------------

async def test_daily_stats_returns_all_days(
    client: AsyncClient, regular_user: User, db_session: AsyncSession
):
    """Daily stats should return one entry for every day in the month."""
    year, month = 2025, 2  # 28 days
    await _create_workout(
        db_session, regular_user.id, SportType.RUNNING, 30,
        date(year, month, 14), is_completed=True
    )

    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    r = await client.get(
        "/api/v1/analytics/daily",
        params={"year": year, "month": month},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["days"]) == 28  # February 2025

    # Day 14 should have the workout
    day14 = next(d for d in data["days"] if d["date"] == "2025-02-14")
    assert day14["completed_minutes"] == 30
    assert day14["planned_minutes"] == 0
    assert day14["total_minutes"] == 30

    # Day 1 should be zero
    day1 = next(d for d in data["days"] if d["date"] == "2025-02-01")
    assert day1["total_minutes"] == 0


async def test_daily_stats_planned_vs_completed_split(
    client: AsyncClient, regular_user: User, db_session: AsyncSession
):
    """Planned-not-completed workouts appear in planned_minutes, not completed."""
    from app.utils.enums import WorkoutSource
    year, month = 2025, 8

    # Completed workout
    w1 = Workout(
        user_id=regular_user.id,
        sport_type=SportType.CYCLING,
        source=WorkoutSource.PLANNED,
        date=date(year, month, 5),
        duration_minutes=90,
        is_completed=True,
    )
    # Planned-not-completed workout
    w2 = Workout(
        user_id=regular_user.id,
        sport_type=SportType.CYCLING,
        source=WorkoutSource.PLANNED,
        date=date(year, month, 5),
        duration_minutes=60,
        is_completed=False,
    )
    db_session.add_all([w1, w2])
    await db_session.flush()

    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    r = await client.get(
        "/api/v1/analytics/daily",
        params={"year": year, "month": month},
        headers=headers,
    )
    assert r.status_code == 200
    day5 = next(d for d in r.json()["days"] if d["date"] == f"{year}-{month:02d}-05")
    assert day5["completed_minutes"] == 90
    assert day5["planned_minutes"] == 60
    assert day5["total_minutes"] == 150


# ---------------------------------------------------------------------------
# Data isolation (user scoping)
# ---------------------------------------------------------------------------

async def test_analytics_scoped_to_current_user(
    client: AsyncClient,
    regular_user: User,
    admin_user: User,
    db_session: AsyncSession,
):
    """Users only see their own workouts in analytics."""
    year, month = 2025, 9

    # Admin workout
    await _create_workout(
        db_session, admin_user.id, SportType.RUNNING, 999,
        date(year, month, 1), is_completed=True
    )
    # Regular user workout
    await _create_workout(
        db_session, regular_user.id, SportType.RUNNING, 30,
        date(year, month, 1), is_completed=True
    )

    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    r = await client.get(
        "/api/v1/analytics/monthly",
        params={"year": year, "month": month},
        headers=headers,
    )
    data = r.json()
    # Only regular user's 30-minute workout
    assert data["total_minutes"] == 30
    assert data["total_workouts"] == 1
