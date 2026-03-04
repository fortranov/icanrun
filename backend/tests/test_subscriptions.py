"""
Tests for subscription endpoints:
  - GET /subscriptions/current  — get active subscription for current user

Also validates subscription-based permission enforcement across plan types.
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.user import User
from app.utils.enums import SubscriptionPlan
from tests.conftest import get_auth_headers


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def user_headers(client: AsyncClient, regular_user: User) -> dict:
    return await get_auth_headers(client, "testuser@example.com", "testpassword123")


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    return await get_auth_headers(client, "admin@example.com", "adminpassword123")


# ---------------------------------------------------------------------------
# GET /subscriptions/current
# ---------------------------------------------------------------------------

async def test_get_current_subscription_trial(client: AsyncClient, user_headers: dict):
    """Regular user (with trial sub) can retrieve their current subscription."""
    resp = await client.get("/api/v1/subscriptions/current", headers=user_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert body["plan"] == "trial"
    assert body["is_active"] is True
    assert body["expires_at"] is not None  # Trial has an expiry date


async def test_get_current_subscription_pro(client: AsyncClient, admin_headers: dict):
    """Admin user (with Pro sub) sees Pro plan with no expiry."""
    resp = await client.get("/api/v1/subscriptions/current", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "pro"
    assert body["is_active"] is True
    assert body["expires_at"] is None  # Pro admin sub never expires


async def test_get_current_subscription_unauthenticated(client: AsyncClient):
    """Unauthenticated requests are rejected with 401."""
    resp = await client.get("/api/v1/subscriptions/current")
    assert resp.status_code == 401


async def test_get_current_subscription_no_sub(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """User with no active subscription receives null response."""
    from app.core.security import hash_password
    from app.utils.enums import UserRole

    # Create a user with no subscription
    bare_user = User(
        email="nosub@example.com",
        hashed_password=hash_password("password123"),
        name="No Sub User",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(bare_user)
    await db_session.flush()

    headers = await get_auth_headers(client, "nosub@example.com", "password123")
    resp = await client.get("/api/v1/subscriptions/current", headers=headers)
    assert resp.status_code == 200
    # FastAPI returns null as JSON null
    assert resp.json() is None


async def test_get_current_subscription_expired_sub(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """User with an expired subscription receives null (no active sub)."""
    from app.core.security import hash_password
    from app.utils.enums import UserRole

    # Create a user with an expired trial
    expired_user = User(
        email="expired@example.com",
        hashed_password=hash_password("password123"),
        name="Expired User",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(expired_user)
    await db_session.flush()

    # Create an expired subscription
    expired_sub = Subscription(
        user_id=expired_user.id,
        plan=SubscriptionPlan.TRIAL,
        is_active=False,  # Deactivated
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(expired_sub)
    await db_session.flush()

    headers = await get_auth_headers(client, "expired@example.com", "password123")
    resp = await client.get("/api/v1/subscriptions/current", headers=headers)
    assert resp.status_code == 200
    # No active subscription
    assert resp.json() is None


# ---------------------------------------------------------------------------
# Subscription permission enforcement
# ---------------------------------------------------------------------------

async def test_basic_plan_cannot_generate_training_plan(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Users on the Basic plan should not be able to generate training plans.
    Verifies the subscription permission check in /plans/generate.
    """
    from app.core.security import hash_password
    from app.utils.enums import UserRole

    # Create a user with Basic subscription
    basic_user = User(
        email="basic@example.com",
        hashed_password=hash_password("password123"),
        name="Basic User",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(basic_user)
    await db_session.flush()

    basic_sub = Subscription(
        user_id=basic_user.id,
        plan=SubscriptionPlan.BASIC,
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(basic_sub)
    await db_session.flush()

    headers = await get_auth_headers(client, "basic@example.com", "password123")
    resp = await client.post(
        "/api/v1/plans/generate",
        headers=headers,
        json={
            "sport_type": "running",
            "preferred_days": [1, 3, 5],
            "max_hours_per_week": 8,
        },
    )
    # Basic plan cannot generate training plans
    assert resp.status_code == 403


async def test_trial_plan_can_generate_training_plan(
    client: AsyncClient,
    regular_user: User,
    user_headers: dict,
):
    """Users on the Trial plan can generate training plans (all features enabled)."""
    resp = await client.post(
        "/api/v1/plans/generate",
        headers=user_headers,
        json={
            "sport_type": "running",
            "preferred_days": [1, 3, 5],
            "max_hours_per_week": 8,
        },
    )
    # Trial has full access — expect 201 Created
    assert resp.status_code == 201


async def test_pro_plan_can_generate_training_plan(
    client: AsyncClient,
    admin_user: User,
    admin_headers: dict,
):
    """Users on the Pro plan can generate training plans."""
    resp = await client.post(
        "/api/v1/plans/generate",
        headers=admin_headers,
        json={
            "sport_type": "running",
            "preferred_days": [0, 2, 4],
            "max_hours_per_week": 10,
        },
    )
    assert resp.status_code == 201


async def test_new_user_registration_gets_trial(client: AsyncClient, db_session: AsyncSession):
    """Newly registered users automatically receive a 30-day Trial subscription."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser_sub@example.com",
            "password": "password123",
            "name": "New User",
        },
    )
    assert resp.status_code == 201

    # Login and check subscription
    headers = await get_auth_headers(client, "newuser_sub@example.com", "password123")
    sub_resp = await client.get("/api/v1/subscriptions/current", headers=headers)
    assert sub_resp.status_code == 200
    body = sub_resp.json()
    assert body is not None
    assert body["plan"] == "trial"
    assert body["is_active"] is True
