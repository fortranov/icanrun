"""
Tests for authentication endpoints.

Covers:
  - POST /api/v1/auth/register
  - POST /api/v1/auth/login
  - POST /api/v1/auth/refresh
  - POST /api/v1/auth/logout
  - GET  /api/v1/auth/me
  - GET  /api/v1/users/me
  - PATCH /api/v1/users/me
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.conftest import get_auth_headers

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, db_session: AsyncSession):
    """Successful registration returns 201 with both tokens."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepass123",
            "name": "New User",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20
    assert len(body["refresh_token"]) > 20


@pytest.mark.asyncio
async def test_register_with_profile_fields(client: AsyncClient):
    """Registration with optional profile fields succeeds."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "athlete@example.com",
            "password": "securepass123",
            "name": "Athlete One",
            "birth_year": 1990,
            "gender": "male",
            "weight_kg": 75.5,
            "height_cm": 180.0,
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, regular_user: User):
    """Registration with an already-taken email returns 400."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",  # same as regular_user fixture
            "password": "anotherpass123",
            "name": "Duplicate User",
        },
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_email_case_insensitive(client: AsyncClient, regular_user: User):
    """Email comparison is case-insensitive during registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "TESTUSER@EXAMPLE.COM",
            "password": "anotherpass123",
            "name": "Upper User",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_password_too_short(client: AsyncClient):
    """Passwords shorter than 8 characters are rejected with 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "short@example.com",
            "password": "abc",
            "name": "Short Pass",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Invalid email format is rejected with 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "securepass123",
            "name": "Bad Email",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_creates_trial_subscription(client: AsyncClient):
    """New user gets a Trial subscription automatically."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "trialsub@example.com",
            "password": "securepass123",
            "name": "Trial Sub",
        },
    )
    assert reg_resp.status_code == 201
    access_token = reg_resp.json()["access_token"]

    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    me_body = me_resp.json()
    assert me_body["subscription"] is not None
    assert me_body["subscription"]["plan"] == "trial"
    assert me_body["subscription"]["is_active"] is True


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, regular_user: User):
    """Valid credentials return access and refresh tokens."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, regular_user: User):
    """Wrong password returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    """Unknown email returns 401 (same error as wrong password — no user enumeration)."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "somepassword123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_email_case_insensitive(client: AsyncClient, regular_user: User):
    """Login email comparison is case-insensitive."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "TESTUSER@EXAMPLE.COM", "password": "testpassword123"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session: AsyncSession):
    """Disabled accounts cannot log in."""
    from app.core.security import hash_password
    from app.models.user import User as UserModel
    from app.utils.enums import UserRole

    inactive = UserModel(
        email="inactive@example.com",
        hashed_password=hash_password("password123"),
        name="Inactive",
        role=UserRole.USER,
        is_active=False,
    )
    db_session.add(inactive)
    await db_session.flush()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "password123"},
    )
    assert response.status_code == 400
    assert "disabled" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient, regular_user: User):
    """Valid refresh token returns new token pair."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "testpassword123"},
    )
    refresh_token = login_resp.json()["refresh_token"]
    old_access = login_resp.json()["access_token"]

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    body = refresh_resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    # New tokens should differ from old ones
    assert body["access_token"] != old_access
    assert body["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient, regular_user: User):
    """After refresh, the old refresh token must not work again (rotation)."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "testpassword123"},
    )
    old_refresh = login_resp.json()["refresh_token"]

    # Use the refresh token once
    await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )

    # Reuse the old token — should fail
    reuse_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert reuse_resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient, regular_user: User):
    """Using an access token as a refresh token must be rejected."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "testpassword123"},
    )
    access_token = login_resp.json()["access_token"]

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_garbage_token(client: AsyncClient):
    """Completely invalid token string returns 401."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "this.is.garbage"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, regular_user: User):
    """Logout returns 204 and invalidates the refresh token."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "testpassword123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 204

    # After logout, refresh token should be blacklisted
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_without_token(client: AsyncClient):
    """Logout without a refresh token body returns 204 (idempotent)."""
    response = await client.post("/api/v1/auth/logout", json={"refresh_token": ""})
    # Empty string is falsy — treated as no token
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_logout_with_invalid_token(client: AsyncClient):
    """Logout with an already-expired or invalid token still returns 204."""
    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_me_success(client: AsyncClient, regular_user: User):
    """Authenticated request to /auth/me returns user profile."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "testuser@example.com"
    assert body["name"] == "Test User"
    assert body["role"] == "user"
    assert "subscription" in body


@pytest.mark.asyncio
async def test_auth_me_with_subscription(client: AsyncClient, regular_user: User):
    """Response includes subscription info with plan and expiry."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    sub = response.json()["subscription"]
    assert sub is not None
    assert sub["plan"] == "trial"
    assert sub["is_active"] is True
    assert sub["expires_at"] is not None


@pytest.mark.asyncio
async def test_auth_me_no_token(client: AsyncClient):
    """Request without Authorization header returns 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_invalid_token(client: AsyncClient):
    """Request with invalid token returns 401."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_expired_access_token(client: AsyncClient, regular_user: User):
    """Expired access token returns 401."""
    from datetime import timedelta
    from app.core.security import create_access_token

    # Create a token that's already expired
    expired_token = create_access_token(
        subject=regular_user.id,
        expires_delta=timedelta(seconds=-1),
    )
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_users_me_success(client: AsyncClient, regular_user: User):
    """GET /users/me returns the same profile as /auth/me."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "testuser@example.com"
    assert "subscription" in body


# ---------------------------------------------------------------------------
# PATCH /users/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_profile_name(client: AsyncClient, regular_user: User):
    """User can update their display name."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    response = await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_profile_athlete_fields(client: AsyncClient, regular_user: User):
    """User can update birth_year, gender, weight_kg, height_cm."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    response = await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "birth_year": 1988,
            "gender": "male",
            "weight_kg": 70.0,
            "height_cm": 175.0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["birth_year"] == 1988
    assert body["gender"] == "male"
    assert body["weight_kg"] == 70.0
    assert body["height_cm"] == 175.0


@pytest.mark.asyncio
async def test_update_profile_email_duplicate(
    client: AsyncClient,
    regular_user: User,
    admin_user: User,
):
    """Updating email to one already taken returns 400."""
    headers = await get_auth_headers(client, "testuser@example.com", "testpassword123")
    response = await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"email": "admin@example.com"},  # admin_user's email
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_profile_unauthenticated(client: AsyncClient):
    """Unauthenticated PATCH /users/me returns 401."""
    response = await client.patch(
        "/api/v1/users/me",
        json={"name": "Hacker"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Admin user fixture sanity checks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_login(client: AsyncClient, admin_user: User):
    """Admin user can log in and /auth/me returns role=admin."""
    headers = await get_auth_headers(client, "admin@example.com", "adminpassword123")
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["subscription"]["plan"] == "pro"


# ---------------------------------------------------------------------------
# Health check (sanity)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Health check endpoint is reachable without auth."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
