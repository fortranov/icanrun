"""
Tests for workout CRUD endpoints.

Covers:
  GET    /api/v1/workouts
  POST   /api/v1/workouts
  GET    /api/v1/workouts/{id}
  PATCH  /api/v1/workouts/{id}
  DELETE /api/v1/workouts/{id}
  POST   /api/v1/workouts/{id}/complete
  PATCH  /api/v1/workouts/{id}/toggle-complete
  PATCH  /api/v1/workouts/{id}/move
"""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workout import Workout
from tests.conftest import get_auth_headers

BASE = "/api/v1/workouts"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def running_payload() -> dict:
    return {
        "sport_type": "running",
        "workout_type": "long",
        "date": str(date.today()),
        "duration_minutes": 60,
        "comment": "Easy long run",
    }


async def create_workout(client: AsyncClient, headers: dict, payload: dict) -> dict:
    """Helper: POST /workouts, assert 201, return body."""
    resp = await client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_unauthenticated(client: AsyncClient):
    resp = await client.get(BASE)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_unauthenticated(client: AsyncClient, running_payload: dict):
    resp = await client.post(BASE, json=running_payload)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_workout_success(
    client: AsyncClient, regular_user: User, running_payload: dict
):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    body = await create_workout(client, headers, running_payload)

    assert body["sport_type"] == "running"
    assert body["workout_type"] == "long"
    assert body["duration_minutes"] == 60
    assert body["is_completed"] is False
    assert body["source"] == "manual"
    assert body["comment"] == "Easy long run"
    assert body["user_id"] == regular_user.id


@pytest.mark.asyncio
async def test_create_workout_minimal(client: AsyncClient, regular_user: User):
    """Only required fields."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.post(
        BASE,
        json={"sport_type": "swimming", "date": str(date.today()), "duration_minutes": 45},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["workout_type"] is None
    assert body["comment"] is None


@pytest.mark.asyncio
async def test_create_workout_all_sport_types(client: AsyncClient, regular_user: User):
    """Each sport type can be used."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    for sport in ("running", "swimming", "cycling", "strength", "triathlon"):
        resp = await client.post(
            BASE,
            json={"sport_type": sport, "date": str(date.today()), "duration_minutes": 30},
            headers=headers,
        )
        assert resp.status_code == 201, f"failed for sport={sport}: {resp.text}"


@pytest.mark.asyncio
async def test_create_workout_all_types(client: AsyncClient, regular_user: User):
    """Each workout_type value is accepted."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    for wtype in ("recovery", "long", "interval", "threshold"):
        resp = await client.post(
            BASE,
            json={
                "sport_type": "running",
                "workout_type": wtype,
                "date": str(date.today()),
                "duration_minutes": 30,
            },
            headers=headers,
        )
        assert resp.status_code == 201, f"failed for workout_type={wtype}"


@pytest.mark.asyncio
async def test_create_workout_invalid_duration(client: AsyncClient, regular_user: User):
    """Duration must be > 0."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.post(
        BASE,
        json={"sport_type": "running", "date": str(date.today()), "duration_minutes": 0},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_workout_duration_too_long(client: AsyncClient, regular_user: User):
    """Duration cannot exceed 1440 minutes (24 h)."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.post(
        BASE,
        json={"sport_type": "running", "date": str(date.today()), "duration_minutes": 1441},
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_workouts_empty(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.get(BASE, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_list_workouts_returns_own_only(
    client: AsyncClient, regular_user: User, admin_user: User
):
    """Users only see their own workouts."""
    user_headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    admin_headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")

    await create_workout(
        client, user_headers,
        {"sport_type": "running", "date": str(date.today()), "duration_minutes": 40}
    )
    await create_workout(
        client, admin_headers,
        {"sport_type": "cycling", "date": str(date.today()), "duration_minutes": 60}
    )

    user_resp = await client.get(BASE, headers=user_headers)
    user_ids = {w["user_id"] for w in user_resp.json()["items"]}
    assert user_ids == {regular_user.id}


@pytest.mark.asyncio
async def test_list_filter_by_sport(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    today = str(date.today())
    await create_workout(client, headers, {"sport_type": "running", "date": today, "duration_minutes": 30})
    await create_workout(client, headers, {"sport_type": "swimming", "date": today, "duration_minutes": 40})

    resp = await client.get(BASE, params={"sport_type": "running"}, headers=headers)
    assert resp.status_code == 200
    assert all(w["sport_type"] == "running" for w in resp.json()["items"])


@pytest.mark.asyncio
async def test_list_filter_by_month(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    today = date.today()
    await create_workout(
        client, headers,
        {"sport_type": "running", "date": str(today), "duration_minutes": 30}
    )
    resp = await client.get(
        BASE,
        params={"year": today.year, "month": today.month},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_list_filter_by_completed(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    today = str(date.today())
    w = await create_workout(client, headers, {"sport_type": "cycling", "date": today, "duration_minutes": 50})
    # Mark completed
    await client.post(f"{BASE}/{w['id']}/complete", json={}, headers=headers)

    resp = await client.get(BASE, params={"is_completed": "true"}, headers=headers)
    assert resp.status_code == 200
    assert all(w["is_completed"] for w in resp.json()["items"])


# ---------------------------------------------------------------------------
# Get single
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_workout_success(client: AsyncClient, regular_user: User, running_payload: dict):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_workout(client, headers, running_payload)
    resp = await client.get(f"{BASE}/{created['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_workout_not_found(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.get(f"{BASE}/999999", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_workout_forbidden(
    client: AsyncClient, regular_user: User, admin_user: User
):
    """User cannot access another user's workout."""
    admin_headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")
    admin_workout = await create_workout(
        client, admin_headers,
        {"sport_type": "running", "date": str(date.today()), "duration_minutes": 30}
    )
    user_headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.get(f"{BASE}/{admin_workout['id']}", headers=user_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_workout_fields(client: AsyncClient, regular_user: User, running_payload: dict):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_workout(client, headers, running_payload)

    resp = await client.patch(
        f"{BASE}/{created['id']}",
        json={"duration_minutes": 90, "comment": "Updated comment"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["duration_minutes"] == 90
    assert body["comment"] == "Updated comment"


@pytest.mark.asyncio
async def test_update_workout_sport_type(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_workout(
        client, headers,
        {"sport_type": "running", "date": str(date.today()), "duration_minutes": 30}
    )
    resp = await client.patch(
        f"{BASE}/{created['id']}",
        json={"sport_type": "cycling"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["sport_type"] == "cycling"


@pytest.mark.asyncio
async def test_update_workout_date(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    tomorrow = str(date.today() + timedelta(days=1))
    created = await create_workout(
        client, headers,
        {"sport_type": "running", "date": str(date.today()), "duration_minutes": 30}
    )
    resp = await client.patch(
        f"{BASE}/{created['id']}",
        json={"date": tomorrow},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["date"] == tomorrow


@pytest.mark.asyncio
async def test_update_workout_forbidden(
    client: AsyncClient, regular_user: User, admin_user: User
):
    admin_headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")
    admin_workout = await create_workout(
        client, admin_headers,
        {"sport_type": "running", "date": str(date.today()), "duration_minutes": 30}
    )
    user_headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.patch(
        f"{BASE}/{admin_workout['id']}",
        json={"duration_minutes": 99},
        headers=user_headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_workout_success(client: AsyncClient, regular_user: User, running_payload: dict):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_workout(client, headers, running_payload)

    del_resp = await client.delete(f"{BASE}/{created['id']}", headers=headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"{BASE}/{created['id']}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_workout_forbidden(
    client: AsyncClient, regular_user: User, admin_user: User
):
    admin_headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")
    admin_workout = await create_workout(
        client, admin_headers,
        {"sport_type": "running", "date": str(date.today()), "duration_minutes": 30}
    )
    user_headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.delete(f"{BASE}/{admin_workout['id']}", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_nonexistent_workout(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.delete(f"{BASE}/999999", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Complete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_complete_workout(client: AsyncClient, regular_user: User, running_payload: dict):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_workout(client, headers, running_payload)
    assert created["is_completed"] is False

    resp = await client.post(
        f"{BASE}/{created['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_completed"] is True


@pytest.mark.asyncio
async def test_complete_workout_with_actual_duration(
    client: AsyncClient, regular_user: User, running_payload: dict
):
    """Complete with different actual duration overrides the original."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_workout(client, headers, running_payload)  # planned: 60 min

    resp = await client.post(
        f"{BASE}/{created['id']}/complete",
        json={"actual_duration_minutes": 75, "comment": "Felt strong"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_completed"] is True
    assert body["duration_minutes"] == 75
    assert body["comment"] == "Felt strong"


@pytest.mark.asyncio
async def test_complete_workout_forbidden(
    client: AsyncClient, regular_user: User, admin_user: User
):
    admin_headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")
    admin_workout = await create_workout(
        client, admin_headers,
        {"sport_type": "running", "date": str(date.today()), "duration_minutes": 30}
    )
    user_headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.post(
        f"{BASE}/{admin_workout['id']}/complete",
        json={},
        headers=user_headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Toggle complete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_toggle_complete(client: AsyncClient, regular_user: User, running_payload: dict):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_workout(client, headers, running_payload)
    assert created["is_completed"] is False

    # Toggle ON
    resp1 = await client.patch(f"{BASE}/{created['id']}/toggle-complete", headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["is_completed"] is True

    # Toggle OFF
    resp2 = await client.patch(f"{BASE}/{created['id']}/toggle-complete", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["is_completed"] is False


# ---------------------------------------------------------------------------
# Move (drag-and-drop)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_move_workout(client: AsyncClient, regular_user: User, running_payload: dict):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_workout(client, headers, running_payload)

    new_date = str(date.today() + timedelta(days=3))
    resp = await client.patch(
        f"{BASE}/{created['id']}/move",
        json={"new_date": new_date},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["date"] == new_date


@pytest.mark.asyncio
async def test_move_workout_to_past(client: AsyncClient, regular_user: User, running_payload: dict):
    """Moving to the past is allowed (manual backdating)."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_workout(client, headers, running_payload)

    past_date = str(date.today() - timedelta(days=7))
    resp = await client.patch(
        f"{BASE}/{created['id']}/move",
        json={"new_date": past_date},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["date"] == past_date


@pytest.mark.asyncio
async def test_move_workout_forbidden(
    client: AsyncClient, regular_user: User, admin_user: User
):
    admin_headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")
    admin_workout = await create_workout(
        client, admin_headers,
        {"sport_type": "running", "date": str(date.today()), "duration_minutes": 30}
    )
    user_headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.patch(
        f"{BASE}/{admin_workout['id']}/move",
        json={"new_date": str(date.today() + timedelta(days=1))},
        headers=user_headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Skip interaction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_workout_on_skipped_date(
    client: AsyncClient, regular_user: User, db_session: AsyncSession
):
    """
    Creating a workout on a skipped day succeeds (user override).
    The skip is informational, not a hard block.
    """
    from app.models.skip import Skip
    skip = Skip(user_id=regular_user.id, date=date.today(), reason="Sick")
    db_session.add(skip)
    await db_session.flush()

    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.post(
        BASE,
        json={"sport_type": "running", "date": str(date.today()), "duration_minutes": 30},
        headers=headers,
    )
    # Should succeed — skip is a soft reminder, not a hard block
    assert resp.status_code == 201
