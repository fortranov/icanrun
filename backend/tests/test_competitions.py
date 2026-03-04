"""
Tests for competition CRUD endpoints.

Covers:
  GET    /api/v1/competitions
  POST   /api/v1/competitions
  GET    /api/v1/competitions/{id}
  PATCH  /api/v1/competitions/{id}
  DELETE /api/v1/competitions/{id}
  POST   /api/v1/competitions/{id}/result
"""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import get_auth_headers

BASE = "/api/v1/competitions"

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def marathon_payload() -> dict:
    return {
        "sport_type": "running",
        "competition_type": "marathon",
        "importance": "key",
        "date": str(date.today() + timedelta(days=90)),
        "name": "City Marathon 2026",
    }


@pytest.fixture
def sprint_triathlon_payload() -> dict:
    return {
        "sport_type": "triathlon",
        "competition_type": "sprint",
        "importance": "secondary",
        "date": str(date.today() + timedelta(days=30)),
        "name": "Sprint Tri Test",
    }


async def create_competition(client: AsyncClient, headers: dict, payload: dict) -> dict:
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
async def test_create_unauthenticated(client: AsyncClient, marathon_payload: dict):
    resp = await client.post(BASE, json=marathon_payload)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_competition_success(
    client: AsyncClient, regular_user: User, marathon_payload: dict
):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    body = await create_competition(client, headers, marathon_payload)

    assert body["sport_type"] == "running"
    assert body["competition_type"] == "marathon"
    assert body["importance"] == "key"
    assert body["name"] == "City Marathon 2026"
    assert body["distance"] is None
    assert body["user_id"] == regular_user.id


@pytest.mark.asyncio
async def test_create_all_running_types(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    for comp_type in ("run_5k", "run_10k", "half_marathon", "marathon"):
        resp = await client.post(
            BASE,
            json={
                "sport_type": "running",
                "competition_type": comp_type,
                "importance": "key",
                "date": str(date.today() + timedelta(days=60)),
                "name": f"Test {comp_type}",
            },
            headers=headers,
        )
        assert resp.status_code == 201, f"failed for {comp_type}: {resp.text}"


@pytest.mark.asyncio
async def test_create_all_triathlon_types(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    for comp_type in ("super_sprint", "sprint", "olympic", "half_iron", "iron"):
        resp = await client.post(
            BASE,
            json={
                "sport_type": "triathlon",
                "competition_type": comp_type,
                "importance": "secondary",
                "date": str(date.today() + timedelta(days=60)),
                "name": f"Test {comp_type}",
            },
            headers=headers,
        )
        assert resp.status_code == 201, f"failed for {comp_type}: {resp.text}"


@pytest.mark.asyncio
async def test_create_swimming_requires_distance(client: AsyncClient, regular_user: User):
    """Swimming competition must include a distance in meters."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    # Without distance — should fail
    resp = await client.post(
        BASE,
        json={
            "sport_type": "swimming",
            "competition_type": "swimming",
            "importance": "key",
            "date": str(date.today() + timedelta(days=30)),
            "name": "Pool 1500m",
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_swimming_with_distance(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.post(
        BASE,
        json={
            "sport_type": "swimming",
            "competition_type": "swimming",
            "importance": "key",
            "date": str(date.today() + timedelta(days=30)),
            "name": "Pool 1500m",
            "distance": 1500.0,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["distance"] == 1500.0


@pytest.mark.asyncio
async def test_create_cycling_with_distance(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.post(
        BASE,
        json={
            "sport_type": "cycling",
            "competition_type": "cycling",
            "importance": "secondary",
            "date": str(date.today() + timedelta(days=45)),
            "name": "Gran Fondo 100km",
            "distance": 100.0,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["distance"] == 100.0


@pytest.mark.asyncio
async def test_create_competition_invalid_date_format(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.post(
        BASE,
        json={
            "sport_type": "running",
            "competition_type": "marathon",
            "importance": "key",
            "date": "not-a-date",
            "name": "Bad Date",
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_competition_empty_name(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.post(
        BASE,
        json={
            "sport_type": "running",
            "competition_type": "marathon",
            "importance": "key",
            "date": str(date.today() + timedelta(days=60)),
            "name": "",
        },
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_competitions_empty(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.get(BASE, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body


@pytest.mark.asyncio
async def test_list_competitions_own_only(
    client: AsyncClient, regular_user: User, admin_user: User
):
    user_headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    admin_headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")

    await create_competition(
        client, user_headers,
        {
            "sport_type": "running",
            "competition_type": "marathon",
            "importance": "key",
            "date": str(date.today() + timedelta(days=60)),
            "name": "User Marathon",
        },
    )
    await create_competition(
        client, admin_headers,
        {
            "sport_type": "triathlon",
            "competition_type": "olympic",
            "importance": "key",
            "date": str(date.today() + timedelta(days=90)),
            "name": "Admin Olympic",
        },
    )

    user_resp = await client.get(BASE, headers=user_headers)
    names = [c["name"] for c in user_resp.json()["items"]]
    assert "User Marathon" in names
    assert "Admin Olympic" not in names


@pytest.mark.asyncio
async def test_list_filter_by_sport(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    await create_competition(
        client, headers,
        {"sport_type": "running", "competition_type": "marathon", "importance": "key",
         "date": str(date.today() + timedelta(days=60)), "name": "Running Race"}
    )
    await create_competition(
        client, headers,
        {"sport_type": "triathlon", "competition_type": "sprint", "importance": "key",
         "date": str(date.today() + timedelta(days=80)), "name": "Tri Race"}
    )

    resp = await client.get(BASE, params={"sport_type": "running"}, headers=headers)
    assert resp.status_code == 200
    assert all(c["sport_type"] == "running" for c in resp.json()["items"])


@pytest.mark.asyncio
async def test_list_filter_by_importance(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    await create_competition(
        client, headers,
        {"sport_type": "running", "competition_type": "marathon", "importance": "key",
         "date": str(date.today() + timedelta(days=60)), "name": "Key Race"}
    )
    await create_competition(
        client, headers,
        {"sport_type": "running", "competition_type": "run_10k", "importance": "secondary",
         "date": str(date.today() + timedelta(days=20)), "name": "Secondary Race"}
    )

    resp = await client.get(BASE, params={"importance": "key"}, headers=headers)
    assert resp.status_code == 200
    assert all(c["importance"] == "key" for c in resp.json()["items"])


# ---------------------------------------------------------------------------
# Get single
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_competition_success(
    client: AsyncClient, regular_user: User, marathon_payload: dict
):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_competition(client, headers, marathon_payload)
    resp = await client.get(f"{BASE}/{created['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_competition_not_found(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.get(f"{BASE}/999999", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_competition_forbidden(
    client: AsyncClient, regular_user: User, admin_user: User
):
    admin_headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")
    admin_comp = await create_competition(
        client, admin_headers,
        {"sport_type": "triathlon", "competition_type": "olympic", "importance": "key",
         "date": str(date.today() + timedelta(days=90)), "name": "Admin Only"}
    )
    user_headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.get(f"{BASE}/{admin_comp['id']}", headers=user_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_competition_name(
    client: AsyncClient, regular_user: User, marathon_payload: dict
):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_competition(client, headers, marathon_payload)

    resp = await client.patch(
        f"{BASE}/{created['id']}",
        json={"name": "Updated Marathon 2026"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Marathon 2026"


@pytest.mark.asyncio
async def test_update_competition_date(
    client: AsyncClient, regular_user: User, marathon_payload: dict
):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_competition(client, headers, marathon_payload)
    new_date = str(date.today() + timedelta(days=120))

    resp = await client.patch(
        f"{BASE}/{created['id']}",
        json={"date": new_date},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["date"] == new_date


@pytest.mark.asyncio
async def test_update_competition_importance(
    client: AsyncClient, regular_user: User, marathon_payload: dict
):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_competition(client, headers, marathon_payload)

    resp = await client.patch(
        f"{BASE}/{created['id']}",
        json={"importance": "secondary"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["importance"] == "secondary"


@pytest.mark.asyncio
async def test_update_competition_forbidden(
    client: AsyncClient, regular_user: User, admin_user: User
):
    admin_headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")
    admin_comp = await create_competition(
        client, admin_headers,
        {"sport_type": "triathlon", "competition_type": "olympic", "importance": "key",
         "date": str(date.today() + timedelta(days=90)), "name": "Admin Only"}
    )
    user_headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.patch(
        f"{BASE}/{admin_comp['id']}",
        json={"name": "Hacked"},
        headers=user_headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_competition_success(
    client: AsyncClient, regular_user: User, marathon_payload: dict
):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_competition(client, headers, marathon_payload)

    del_resp = await client.delete(f"{BASE}/{created['id']}", headers=headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"{BASE}/{created['id']}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_competition_forbidden(
    client: AsyncClient, regular_user: User, admin_user: User
):
    admin_headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")
    admin_comp = await create_competition(
        client, admin_headers,
        {"sport_type": "running", "competition_type": "run_5k", "importance": "secondary",
         "date": str(date.today() + timedelta(days=10)), "name": "Admin Race"}
    )
    user_headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.delete(f"{BASE}/{admin_comp['id']}", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_nonexistent_competition(client: AsyncClient, regular_user: User):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.delete(f"{BASE}/999999", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Result recording
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_result_with_time(
    client: AsyncClient, regular_user: User, marathon_payload: dict
):
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_competition(client, headers, marathon_payload)

    resp = await client.post(
        f"{BASE}/{created['id']}/result",
        json={
            "finish_time_seconds": 13500,  # 3:45:00
            "result_comment": "Great race, PB!",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_add_result_creates_workout(
    client: AsyncClient, regular_user: User, marathon_payload: dict
):
    """Recording a result should create a completed workout on race day."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_competition(client, headers, marathon_payload)
    race_date = created["date"]

    await client.post(
        f"{BASE}/{created['id']}/result",
        json={"finish_time_seconds": 14400},
        headers=headers,
    )

    # Check a completed workout exists on the race date
    workouts_resp = await client.get(
        "/api/v1/workouts",
        params={"date_from": race_date, "date_to": race_date, "is_completed": "true"},
        headers=headers,
    )
    assert workouts_resp.status_code == 200
    assert workouts_resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_add_result_no_time(
    client: AsyncClient, regular_user: User, marathon_payload: dict
):
    """Result without finish time is accepted (comment only)."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_competition(client, headers, marathon_payload)

    resp = await client.post(
        f"{BASE}/{created['id']}/result",
        json={"result_comment": "Did not finish (DNF)"},
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_add_result_empty_body(
    client: AsyncClient, regular_user: User, marathon_payload: dict
):
    """Empty result body is accepted (just marks the competition as 'done')."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    created = await create_competition(client, headers, marathon_payload)

    resp = await client.post(
        f"{BASE}/{created['id']}/result",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_add_result_forbidden(
    client: AsyncClient, regular_user: User, admin_user: User
):
    admin_headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")
    admin_comp = await create_competition(
        client, admin_headers,
        {"sport_type": "running", "competition_type": "marathon", "importance": "key",
         "date": str(date.today() + timedelta(days=90)), "name": "Admin Race"}
    )
    user_headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    resp = await client.post(
        f"{BASE}/{admin_comp['id']}/result",
        json={"finish_time_seconds": 10000},
        headers=user_headers,
    )
    assert resp.status_code == 403
