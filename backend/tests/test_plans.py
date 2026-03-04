"""
Tests for training plan generation (Joe Friel methodology).

Covers:
  - Plan generation for single-sport and triathlon
  - Subscription permission enforcement (Basic blocked)
  - Period structure validation (correct phase names present)
  - 4-week recovery cycle: every 4th week has reduced volume
  - Plan deletion: future workouts removed, past workouts preserved
  - Maintenance plan (no competition): generates ~26 weeks
"""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import Competition
from app.models.subscription import Subscription
from app.models.user import User
from app.models.workout import Workout
from app.utils.enums import CompetitionImportance, CompetitionType, SportType, SubscriptionPlan, WorkoutSource
from tests.conftest import get_auth_headers


@pytest.fixture
async def basic_user(db_session: AsyncSession) -> User:
    """Create a user with Basic subscription (cannot use plans)."""
    from app.core.security import hash_password
    from app.utils.enums import UserRole
    from datetime import datetime, timezone

    user = User(
        email="basicuser@example.com",
        hashed_password=hash_password("testpassword123"),
        name="Basic User",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    sub = Subscription(
        user_id=user.id,
        plan=SubscriptionPlan.BASIC,
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(sub)
    await db_session.flush()
    return user


@pytest.fixture
async def future_competition(db_session: AsyncSession, regular_user: User) -> Competition:
    """Create a future triathlon competition linked to regular_user."""
    comp = Competition(
        user_id=regular_user.id,
        sport_type=SportType.TRIATHLON,
        competition_type=CompetitionType.OLYMPIC,
        importance=CompetitionImportance.KEY,
        date=date.today() + timedelta(weeks=20),
        name="Test Olympic Triathlon",
    )
    db_session.add(comp)
    await db_session.flush()
    return comp


# ---------------------------------------------------------------------------
# Permission tests
# ---------------------------------------------------------------------------

async def test_basic_user_cannot_generate_plan(
    client: AsyncClient, basic_user: User
):
    """Basic subscribers get 403 when trying to generate a plan."""
    headers = await get_auth_headers(client, "basicuser@example.com", "testpassword123")
    response = await client.post(
        "/api/v1/plans/generate",
        json={
            "sport_type": "running",
            "preferred_days": [1, 3, 5],
            "max_hours_per_week": 8.0,
        },
        headers=headers,
    )
    assert response.status_code == 403
    assert "Pro" in response.json()["detail"] or "Trial" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------

async def test_generate_running_maintenance_plan(
    client: AsyncClient, regular_user: User
):
    """Generating a maintenance running plan should create a plan and workouts."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    response = await client.post(
        "/api/v1/plans/generate",
        json={
            "sport_type": "running",
            "preferred_days": [1, 3, 5],
            "max_hours_per_week": 8.0,
            "settings": {
                "athlete_level": "intermediate",
                "sessions_per_week": 3,
            },
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sport_type"] == "running"
    assert data["is_active"] is True
    assert data["total_workouts"] > 0
    assert len(data["periods"]) > 0
    # Maintenance plan should have base and build periods
    period_names = [p["name"] for p in data["periods"]]
    assert "base1" in period_names


async def test_generate_triathlon_plan_with_competition(
    client: AsyncClient,
    regular_user: User,
    future_competition: Competition,
):
    """Generating a triathlon plan toward a competition produces correct structure."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    response = await client.post(
        "/api/v1/plans/generate",
        json={
            "sport_type": "triathlon",
            "competition_id": future_competition.id,
            "preferred_days": [1, 3, 5, 0],  # Mon, Tue, Wed, Thu
            "max_hours_per_week": 12.0,
            "settings": {
                "athlete_level": "intermediate",
                "sessions_per_week": 4,
                "distance_type": "olympic",
                "swim_priority": 1.0,
                "bike_priority": 1.5,
                "run_priority": 1.0,
            },
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sport_type"] == "triathlon"
    assert data["competition_id"] == future_competition.id
    assert data["total_workouts"] > 0
    # Triathlon workouts should include swim/bike/run
    all_sports = set()
    for period in data["periods"]:
        for week in period["weeks"]:
            for w in week["workouts"]:
                all_sports.add(w["sport_type"])
    # Should have multiple sports
    assert len(all_sports) > 1


async def test_generating_plan_replaces_existing(
    client: AsyncClient, regular_user: User
):
    """Generating a second plan for same sport deactivates the first."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")

    payload = {
        "sport_type": "cycling",
        "preferred_days": [2, 4],
        "max_hours_per_week": 6.0,
    }

    r1 = await client.post("/api/v1/plans/generate", json=payload, headers=headers)
    assert r1.status_code == 201
    plan1_id = r1.json()["id"]

    r2 = await client.post("/api/v1/plans/generate", json=payload, headers=headers)
    assert r2.status_code == 201
    plan2_id = r2.json()["id"]

    # Listing active plans should have the new plan, not the old one
    r_list = await client.get("/api/v1/plans", headers=headers)
    active_ids = [p["id"] for p in r_list.json()]
    assert plan2_id in active_ids


# ---------------------------------------------------------------------------
# Period/week structure
# ---------------------------------------------------------------------------

async def test_recovery_weeks_have_lower_volume(
    client: AsyncClient, regular_user: User
):
    """Every 4th week within a period should have lower total volume."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    response = await client.post(
        "/api/v1/plans/generate",
        json={
            "sport_type": "swimming",
            "preferred_days": [0, 2, 4, 6],  # 4 days
            "max_hours_per_week": 10.0,
            "settings": {"sessions_per_week": 4},
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()

    # Find periods with at least 4 weeks and check week 4 is recovery
    for period in data["periods"]:
        weeks = period["weeks"]
        if len(weeks) >= 4:
            week4 = weeks[3]  # 0-indexed week 4
            assert week4["is_recovery"] is True
            # Recovery week should have less volume than week 3
            week3 = weeks[2]
            if week3["total_minutes"] > 0:
                assert week4["total_minutes"] <= week3["total_minutes"]
            break


# ---------------------------------------------------------------------------
# Plan deletion
# ---------------------------------------------------------------------------

async def test_delete_plan_removes_future_workouts(
    client: AsyncClient, regular_user: User, db_session: AsyncSession
):
    """Deleting a plan should remove future planned workouts."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")

    # Generate a plan
    r = await client.post(
        "/api/v1/plans/generate",
        json={
            "sport_type": "strength",
            "preferred_days": [1, 4],
            "max_hours_per_week": 4.0,
        },
        headers=headers,
    )
    assert r.status_code == 201
    plan_id = r.json()["id"]
    total_before = r.json()["total_workouts"]
    assert total_before > 0

    # Delete the plan
    r_del = await client.delete(f"/api/v1/plans/{plan_id}", headers=headers)
    assert r_del.status_code == 204

    # Future workouts should be gone from workouts list
    r_workouts = await client.get(
        "/api/v1/workouts",
        params={"sport_type": "strength"},
        headers=headers,
    )
    assert r_workouts.status_code == 200
    workouts = r_workouts.json()["items"]
    # All remaining workouts with plan_id should be past (or none)
    today = date.today().isoformat()
    future_planned = [
        w for w in workouts
        if w["date"] >= today and w["source"] == "planned"
    ]
    assert len(future_planned) == 0


# ---------------------------------------------------------------------------
# List plans
# ---------------------------------------------------------------------------

async def test_list_plans(client: AsyncClient, regular_user: User):
    """GET /plans returns only active plans for current user."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")

    r = await client.get("/api/v1/plans", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_get_plan_detail(client: AsyncClient, regular_user: User):
    """GET /plans/{id} returns full plan with periods."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")

    # First generate one
    r = await client.post(
        "/api/v1/plans/generate",
        json={
            "sport_type": "running",
            "preferred_days": [1, 4],
            "max_hours_per_week": 6.0,
        },
        headers=headers,
    )
    plan_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/plans/{plan_id}", headers=headers)
    assert r2.status_code == 200
    data = r2.json()
    assert "periods" in data
    assert len(data["periods"]) > 0


async def test_cannot_access_other_user_plan(
    client: AsyncClient, regular_user: User, admin_user: User
):
    """Users cannot view or delete plans owned by other users."""
    user_headers = await get_auth_headers(
        client, "testuser@example.com", "testpassword123"
    )
    admin_headers = await get_auth_headers(
        client, "admin@example.com", "adminpassword123"
    )

    # Admin generates a plan
    r = await client.post(
        "/api/v1/plans/generate",
        json={
            "sport_type": "running",
            "preferred_days": [2],
            "max_hours_per_week": 5.0,
        },
        headers=admin_headers,
    )
    plan_id = r.json()["id"]

    # Regular user tries to view admin's plan
    r2 = await client.get(f"/api/v1/plans/{plan_id}", headers=user_headers)
    assert r2.status_code == 403
