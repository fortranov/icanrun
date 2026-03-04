"""
Tests for admin endpoints:
  - GET  /admin/users         — list users (admin only)
  - PATCH /admin/users/{id}   — update user role / subscription
  - GET  /admin/settings      — get app settings
  - PATCH /admin/settings     — update app settings
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.conftest import get_auth_headers


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    return await get_auth_headers(client, "admin@example.com", "adminpassword123")


@pytest.fixture
async def user_headers(client: AsyncClient, regular_user: User) -> dict:
    return await get_auth_headers(client, "testuser@example.com", "testpassword123")


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

async def test_list_users_admin_success(client: AsyncClient, admin_headers: dict, regular_user: User):
    """Admin can retrieve the full list of users with subscription info."""
    resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # Both admin and regular_user were created; list should contain them
    assert len(body) >= 2

    # Each item must have expected fields
    for item in body:
        assert "id" in item
        assert "email" in item
        assert "role" in item
        assert "subscription" in item  # May be None or dict


async def test_list_users_non_admin_forbidden(client: AsyncClient, user_headers: dict):
    """Non-admin users receive 403 when accessing /admin/users."""
    resp = await client.get("/api/v1/admin/users", headers=user_headers)
    assert resp.status_code == 403


async def test_list_users_unauthenticated(client: AsyncClient):
    """Unauthenticated requests to /admin/users receive 401."""
    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /admin/users/{id}
# ---------------------------------------------------------------------------

async def test_update_user_role_to_admin(
    client: AsyncClient,
    admin_headers: dict,
    regular_user: User,
    db_session: AsyncSession,
):
    """Admin can promote a regular user to admin role."""
    resp = await client.patch(
        f"/api/v1/admin/users/{regular_user.id}",
        headers=admin_headers,
        json={"role": "admin"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "admin"
    assert body["id"] == regular_user.id


async def test_update_user_subscription_plan(
    client: AsyncClient,
    admin_headers: dict,
    regular_user: User,
):
    """Admin can change a user's subscription plan."""
    resp = await client.patch(
        f"/api/v1/admin/users/{regular_user.id}",
        headers=admin_headers,
        json={"subscription_plan": "pro"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Subscription should reflect the new plan
    assert body["subscription"] is not None
    assert body["subscription"]["plan"] == "pro"


async def test_update_user_deactivate(
    client: AsyncClient,
    admin_headers: dict,
    regular_user: User,
):
    """Admin can deactivate a user account."""
    resp = await client.patch(
        f"/api/v1/admin/users/{regular_user.id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_update_user_not_found(client: AsyncClient, admin_headers: dict):
    """Returns 404 when target user does not exist."""
    resp = await client.patch(
        "/api/v1/admin/users/999999",
        headers=admin_headers,
        json={"role": "user"},
    )
    assert resp.status_code == 404


async def test_admin_cannot_demote_self(client: AsyncClient, admin_headers: dict, admin_user: User):
    """Admin cannot remove their own admin role to prevent lockout."""
    resp = await client.patch(
        f"/api/v1/admin/users/{admin_user.id}",
        headers=admin_headers,
        json={"role": "user"},
    )
    assert resp.status_code == 400
    assert "admin" in resp.json()["detail"].lower()


async def test_update_user_non_admin_forbidden(
    client: AsyncClient,
    user_headers: dict,
    admin_user: User,
):
    """Non-admin users cannot access the user update endpoint."""
    resp = await client.patch(
        f"/api/v1/admin/users/{admin_user.id}",
        headers=user_headers,
        json={"role": "user"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /admin/settings
# ---------------------------------------------------------------------------

async def test_get_settings_admin(client: AsyncClient, admin_headers: dict):
    """Admin can retrieve application settings."""
    resp = await client.get("/api/v1/admin/settings", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "google_oauth_enabled" in body
    assert "maintenance_mode" in body
    assert "registration_open" in body
    # Secret must never be exposed
    assert body.get("google_client_secret", "") == ""


async def test_get_settings_non_admin_forbidden(client: AsyncClient, user_headers: dict):
    """Non-admin users cannot access the settings endpoint."""
    resp = await client.get("/api/v1/admin/settings", headers=user_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /admin/settings
# ---------------------------------------------------------------------------

async def test_update_settings_toggle_google_oauth(client: AsyncClient, admin_headers: dict):
    """Admin can toggle Google OAuth on and off."""
    # Get initial state
    initial = await client.get("/api/v1/admin/settings", headers=admin_headers)
    original_value = initial.json()["google_oauth_enabled"]

    # Toggle
    resp = await client.patch(
        "/api/v1/admin/settings",
        headers=admin_headers,
        json={"google_oauth_enabled": not original_value},
    )
    assert resp.status_code == 200
    assert resp.json()["google_oauth_enabled"] == (not original_value)

    # Restore original state
    await client.patch(
        "/api/v1/admin/settings",
        headers=admin_headers,
        json={"google_oauth_enabled": original_value},
    )


async def test_update_settings_set_client_id(client: AsyncClient, admin_headers: dict):
    """Admin can set the Google OAuth client ID."""
    resp = await client.patch(
        "/api/v1/admin/settings",
        headers=admin_headers,
        json={"google_client_id": "test-client-id.apps.googleusercontent.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["google_client_id"] == "test-client-id.apps.googleusercontent.com"


async def test_update_settings_non_admin_forbidden(client: AsyncClient, user_headers: dict):
    """Non-admin users cannot update settings."""
    resp = await client.patch(
        "/api/v1/admin/settings",
        headers=user_headers,
        json={"google_oauth_enabled": True},
    )
    assert resp.status_code == 403
