"""Tests for Strava OAuth and activity import hardening."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.user import User
from app.models.workout import Workout
from app.services import strava_service
from app.utils.enums import SportType, UserRole, WorkoutSource

async def _make_user(db_session: AsyncSession, prefix: str = "strava") -> User:
    user = User(
        email=f"{prefix}-{uuid4().hex}@example.com",
        hashed_password="not-used",
        name="Strava Test User",
        role=UserRole.USER,
        is_active=True,
        email_confirmed=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def test_build_auth_url_includes_user_bound_state(monkeypatch):
    """OAuth auth URL should include an opaque state bound to the current user."""
    monkeypatch.setattr(strava_service.settings, "strava_client_id", "client-id")
    monkeypatch.setattr(strava_service.settings, "strava_redirect_uri", "https://example.com/strava/callback")
    auth_url = strava_service.build_auth_url(user_id=42)
    params = parse_qs(urlparse(auth_url).query)

    assert params["client_id"]
    assert params["state"]
    assert strava_service.validate_oauth_state(params["state"][0], user_id=42) is True
    assert strava_service.validate_oauth_state(params["state"][0], user_id=43) is False


async def test_callback_rejects_invalid_state(client: AsyncClient, db_session: AsyncSession):
    user = await _make_user(db_session, "callback")
    headers = _auth_headers(user)

    response = await client.post(
        "/api/v1/strava/callback",
        json={"code": "auth-code", "state": "invalid-state"},
        headers=headers,
    )

    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()


async def test_connect_user_rejects_missing_activity_scope(monkeypatch, db_session: AsyncSession):
    async def fake_exchange_code(code: str):
        return {
            "athlete": {"id": 123, "firstname": "Test", "lastname": "Athlete"},
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_at": 9999999999,
            "scope": "profile:read_all",
        }

    monkeypatch.setattr(strava_service, "exchange_code", fake_exchange_code)

    with pytest.raises(HTTPException) as exc:
        user = await _make_user(db_session, "scope")
        await strava_service.connect_user(user, "auth-code", db_session)

    assert exc.value.status_code == 400
    assert "activity:read_all" in exc.value.detail


async def test_sync_activities_raises_on_strava_error(monkeypatch, db_session: AsyncSession):
    regular_user = await _make_user(db_session, "sync-error")
    regular_user.strava_connected = True
    regular_user.strava_access_token = "access-token"
    regular_user.strava_refresh_token = "refresh-token"
    regular_user.strava_token_expires_at = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    await db_session.flush()

    async def fake_request(method, url, timeout, retry_on_status=(), **kwargs):
        return SimpleNamespace(status_code=429, text="rate limited", json=lambda: {"message": "Rate Limit Exceeded"})

    monkeypatch.setattr(strava_service, "_request_with_proxy_failover", fake_request)

    with pytest.raises(HTTPException) as exc:
        await strava_service.sync_activities(regular_user, db_session, days=30)

    assert exc.value.status_code == 429
    assert "Rate Limit" in exc.value.detail


async def test_sync_activities_uses_proxy_failover_and_dedupes_per_user(monkeypatch, db_session: AsyncSession):
    regular_user = await _make_user(db_session, "sync")
    regular_user.strava_connected = True
    regular_user.strava_access_token = "access-token"
    regular_user.strava_refresh_token = "refresh-token"
    regular_user.strava_token_expires_at = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())

    other_user = User(
        email=f"other-strava-{uuid4().hex}@example.com",
        hashed_password="x",
        name="Other",
        is_active=True,
        email_confirmed=True,
    )
    db_session.add(other_user)
    await db_session.flush()
    db_session.add(Workout(
        user_id=other_user.id,
        sport_type=SportType.RUNNING,
        source=WorkoutSource.STRAVA,
        date=datetime.now(timezone.utc).date(),
        duration_minutes=20,
        is_completed=True,
        strava_activity_id=777,
    ))
    await db_session.flush()

    calls = []
    pages = {
        1: [{
            "id": 777,
            "sport_type": "Ride",
            "moving_time": 3600,
            "start_date_local": "2026-07-13T08:00:00Z",
            "name": "Shared Activity ID",
        }],
        2: [],
    }

    async def fake_request(method, url, timeout, retry_on_status=(), **kwargs):
        calls.append((method, url, kwargs))
        page = kwargs["params"]["page"]
        return SimpleNamespace(status_code=200, text="ok", json=lambda: pages[page])

    monkeypatch.setattr(strava_service, "_request_with_proxy_failover", fake_request)

    result = await strava_service.sync_activities(regular_user, db_session, days=30)

    assert result == {"synced": 1, "skipped": 0}
    assert calls and calls[0][0] == "GET"
    rows = (await db_session.execute(
        select(Workout).where(Workout.user_id == regular_user.id, Workout.strava_activity_id == 777)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].sport_type == SportType.CYCLING


async def test_fetch_and_save_activity_uses_proxy_failover(monkeypatch, db_session: AsyncSession):
    regular_user = await _make_user(db_session, "fetch")
    regular_user.strava_connected = True
    regular_user.strava_access_token = "access-token"
    regular_user.strava_refresh_token = "refresh-token"
    regular_user.strava_token_expires_at = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    await db_session.flush()

    calls = []

    async def fake_request(method, url, timeout, retry_on_status=(), **kwargs):
        calls.append((method, url, kwargs))
        return SimpleNamespace(
            status_code=200,
            text="ok",
            json=lambda: {
                "id": 888,
                "sport_type": "Swim",
                "moving_time": 1800,
                "start_date_local": "2026-07-13T09:00:00Z",
                "name": "Pool Swim",
            },
        )

    monkeypatch.setattr(strava_service, "_request_with_proxy_failover", fake_request)

    workout = await strava_service.fetch_and_save_activity(888, regular_user, db_session)

    assert workout is not None
    assert calls and calls[0][0] == "GET"
    assert workout.sport_type == SportType.SWIMMING


def test_unknown_strava_sport_maps_to_strength_instead_of_running():
    assert strava_service._map_sport_type("AlpineSki") == SportType.STRENGTH
    assert strava_service._map_sport_type("UnknownSport") == SportType.STRENGTH
