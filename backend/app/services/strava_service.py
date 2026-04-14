"""
Strava integration service.

Handles:
  - Building the OAuth2 authorization URL
  - Exchanging authorization code for tokens
  - Refreshing expired access tokens (tokens live 6 hours)
  - Syncing athlete activities → Workout rows
  - Fetching a single activity (used by webhook handler)
  - Disconnecting a user from Strava

Token persistence:
  Tokens are stored in the `users` table in the SQLite database, which lives on
  the mounted host volume /opt/icanrun/data/icanrun.db.  Redeploying the container
  does NOT wipe the volume, so tokens survive deploys without any extra work.
"""
import logging
import time
import urllib.parse
from datetime import date, datetime, timezone
from typing import Callable, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


def _http_client(**kwargs) -> httpx.AsyncClient:
    """
    Return an httpx.AsyncClient configured with the optional Strava proxy.
    Set STRAVA_PROXY_URL env var to route all Strava API traffic through a proxy.
    Example: STRAVA_PROXY_URL=socks5://user:pass@host:1080
    """
    if settings.strava_proxy_url:
        kwargs.setdefault("proxy", settings.strava_proxy_url)
    return httpx.AsyncClient(**kwargs)

from app.core.config import settings
from app.models.user import User
from app.models.workout import Workout
from app.repositories.user_repository import UserRepository
from app.repositories.workout_repository import WorkoutRepository
from app.utils.enums import SportType, WorkoutSource

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Strava API base URLs
# ---------------------------------------------------------------------------
_AUTH_URL = "https://www.strava.com/oauth/authorize"
_TOKEN_URL = "https://www.strava.com/oauth/token"
_DEAUTH_URL = "https://www.strava.com/oauth/deauthorize"
_API_BASE = "https://www.strava.com/api/v3"

# ---------------------------------------------------------------------------
# Strava sport_type → our SportType enum
# Unmapped types default to running (catch-all for unknown activities).
# ---------------------------------------------------------------------------
_SPORT_MAP: dict[str, SportType] = {
    # Running family
    "Run": SportType.RUNNING,
    "TrailRun": SportType.RUNNING,
    "VirtualRun": SportType.RUNNING,
    "Hike": SportType.RUNNING,
    "Walk": SportType.RUNNING,
    "BackcountrySkiing": SportType.RUNNING,
    "NordicSki": SportType.RUNNING,
    "Snowshoe": SportType.RUNNING,
    # Cycling family
    "Ride": SportType.CYCLING,
    "MountainBikeRide": SportType.CYCLING,
    "GravelRide": SportType.CYCLING,
    "VirtualRide": SportType.CYCLING,
    "EBikeRide": SportType.CYCLING,
    "EMountainBikeRide": SportType.CYCLING,
    "Velomobile": SportType.CYCLING,
    "HandCycle": SportType.CYCLING,
    # Swimming
    "Swim": SportType.SWIMMING,
    "OpenWaterSwim": SportType.SWIMMING,
    # Strength / cross-training
    "WeightTraining": SportType.STRENGTH,
    "Yoga": SportType.STRENGTH,
    "Crossfit": SportType.STRENGTH,
    "Elliptical": SportType.STRENGTH,
    "StairStepper": SportType.STRENGTH,
    "RockClimbing": SportType.STRENGTH,
    "Pilates": SportType.STRENGTH,
    "Rowing": SportType.STRENGTH,
    "Workout": SportType.STRENGTH,
    # Triathlon / multi-sport
    "Triathlon": SportType.TRIATHLON,
    "Duathlon": SportType.TRIATHLON,
    "MultiSport": SportType.TRIATHLON,
}


def _map_sport_type(strava_sport: str) -> SportType:
    return _SPORT_MAP.get(strava_sport, SportType.RUNNING)


def _proxy_candidates() -> list[str | None]:
    """
    Build ordered proxy candidates for Strava calls.
    If STRAVA_PROXY_URL is set, try it first, then known in-cluster fallbacks.
    """
    configured = (settings.strava_proxy_url or "").strip()
    candidates: list[str | None] = []
    if configured:
        candidates.append(configured)

        if configured.startswith("socks5://"):
            fallbacks = (
                "socks5://icanrun-wg-socks:1080",
                "socks5://wg-socks:1080",
                "socks5://10.0.1.1:1080",
            )
            for url in fallbacks:
                if url != configured and url not in candidates:
                    candidates.append(url)

    # Last resort for environments where Strava is reachable directly.
    candidates.append(None)
    return candidates


async def _request_with_proxy_failover(
    method: str,
    url: str,
    timeout: float,
    retry_on_status: tuple[int, ...] = (),
    should_retry_response: Callable[[httpx.Response], bool] | None = None,
    **kwargs,
) -> httpx.Response:
    """
    Perform request against Strava, trying configured proxy and fallbacks.
    Raises HTTPException(503) only after all candidates fail to connect.
    """
    last_error: Exception | None = None
    last_response: httpx.Response | None = None
    for proxy_url in _proxy_candidates():
        try:
            async with _http_client(timeout=timeout, proxy=proxy_url) as client:
                resp = await client.request(method, url, **kwargs)
                needs_retry = resp.status_code in retry_on_status
                if should_retry_response is not None and should_retry_response(resp):
                    needs_retry = True
                if needs_retry:
                    last_response = resp
                    target = proxy_url or "direct connection"
                    logger.warning(
                        "Strava request via %s returned %s, trying next candidate",
                        target,
                        resp.status_code,
                    )
                    continue
                return resp
        except (httpx.ConnectError, httpx.ProxyError, httpx.ConnectTimeout) as exc:
            last_error = exc
            target = proxy_url or "direct connection"
            logger.warning("Strava request via %s failed: %s", target, exc)

    if last_response is not None:
        return last_response

    logger.error("Strava API unreachable through all proxy candidates: %s", last_error)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Cannot reach Strava API (proxy unavailable). Try again later.",
    )


def _looks_like_strava_oauth_error(resp: httpx.Response) -> bool:
    """
    Strava OAuth errors are typically JSON with message/errors fields.
    If response doesn't match this shape, it's likely a proxy/gateway error page.
    """
    try:
        payload = resp.json()
    except Exception:
        return False
    return isinstance(payload, dict) and ("message" in payload or "errors" in payload)


# ---------------------------------------------------------------------------
# OAuth helpers
# ---------------------------------------------------------------------------

def build_auth_url() -> str:
    """Return the Strava OAuth2 authorization URL."""
    if not settings.strava_client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strava integration is not configured on this server",
        )
    params = {
        "client_id": settings.strava_client_id,
        "redirect_uri": settings.strava_redirect_uri,
        "response_type": "code",
        "scope": "activity:read_all,profile:read_all",
        "approval_prompt": "auto",
    }
    return _AUTH_URL + "?" + urllib.parse.urlencode(params)


async def exchange_code(code: str) -> dict:
    """
    Exchange an authorization code for tokens.
    Returns the full token response dict from Strava.
    """
    resp = await _request_with_proxy_failover(
        "POST",
        _TOKEN_URL,
        timeout=15.0,
        data={
            "client_id": settings.strava_client_id,
            "client_secret": settings.strava_client_secret,
            "code": code,
            # Must match the redirect_uri used when obtaining the authorization code.
            # Some OAuth providers may reject code exchange with 400/invalid_grant
            # when this parameter is missing or does not match.
            "redirect_uri": settings.strava_redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    if resp.status_code != 200:
        error_detail = "Failed to exchange Strava authorization code"
        try:
            payload = resp.json()
            message = payload.get("message") or payload.get("errors")
            if message:
                error_detail = f"{error_detail}: {message}"
        except Exception:
            pass
        logger.error("Strava token exchange failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
                if resp.status_code >= 500 or resp.status_code == 429
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=error_detail,
        )
    return resp.json()


async def _refresh_token(user: User) -> str:
    """
    Refresh the Strava access token for a user.
    Saves the new tokens to the user row and returns the new access token.
    NOTE: caller must commit the session after this call.
    """
    resp = await _request_with_proxy_failover(
        "POST",
        _TOKEN_URL,
        timeout=15.0,
        data={
            "client_id": settings.strava_client_id,
            "client_secret": settings.strava_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": user.strava_refresh_token,
        },
    )
    if resp.status_code != 200:
        logger.error("Strava token refresh failed for user %s: %s", user.id, resp.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to refresh Strava token",
        )
    data = resp.json()
    user.strava_access_token = data["access_token"]
    user.strava_refresh_token = data["refresh_token"]
    user.strava_token_expires_at = data["expires_at"]
    return data["access_token"]


async def get_valid_access_token(user: User, db: AsyncSession) -> str:
    """
    Return a valid Strava access token for the user, refreshing if necessary.
    Strava tokens expire 6 h after creation; we refresh if within 5 min of expiry.
    """
    if not user.strava_connected or not user.strava_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strava account not connected",
        )
    if user.strava_token_expires_at and user.strava_token_expires_at < int(time.time()) + 300:
        token = await _refresh_token(user)
        await db.commit()
        return token
    return user.strava_access_token


# ---------------------------------------------------------------------------
# Activity sync
# ---------------------------------------------------------------------------

def _map_activity_to_workout(activity: dict, user_id: int) -> Workout:
    """Convert a Strava SummaryActivity dict into a Workout ORM instance."""
    moving_time_sec: int = activity.get("moving_time") or activity.get("elapsed_time") or 0
    duration_minutes = max(1, round(moving_time_sec / 60))

    # Parse the start date (ISO 8601 with Z suffix)
    start_str: str = activity.get("start_date_local") or activity.get("start_date", "")
    try:
        activity_date = datetime.fromisoformat(start_str.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        activity_date = date.today()

    sport_str: str = activity.get("sport_type") or activity.get("type") or "Run"
    sport = _map_sport_type(sport_str)

    return Workout(
        user_id=user_id,
        sport_type=sport,
        source=WorkoutSource.STRAVA,
        date=activity_date,
        duration_minutes=duration_minutes,
        is_completed=True,
        strava_activity_id=activity["id"],
        comment=activity.get("name") or None,
    )


async def sync_activities(user: User, db: AsyncSession, days: int = 30) -> dict:
    """
    Fetch recent activities from Strava and upsert them as Workouts.
    Returns {"synced": int, "skipped": int}.
    """
    token = await get_valid_access_token(user, db)
    repo = WorkoutRepository(db)

    # epoch timestamp for `after` filter
    after_ts = int(time.time()) - days * 86400
    synced = 0
    skipped = 0
    page = 1

    async with _http_client(timeout=30.0) as client:
        while True:
            resp = await client.get(
                f"{_API_BASE}/athlete/activities",
                headers={"Authorization": f"Bearer {token}"},
                params={"after": after_ts, "per_page": 100, "page": page},
            )
            if resp.status_code != 200:
                logger.error("Strava activities fetch failed: %s %s", resp.status_code, resp.text)
                break

            activities = resp.json()
            if not activities:
                break

            for activity in activities:
                existing = await repo.get_by_strava_id(activity["id"])
                if existing:
                    skipped += 1
                    continue
                workout = _map_activity_to_workout(activity, user.id)
                db.add(workout)
                synced += 1

            await db.flush()
            if len(activities) < 100:
                break
            page += 1

    await db.commit()
    logger.info("Strava sync for user %s: synced=%s skipped=%s", user.id, synced, skipped)
    return {"synced": synced, "skipped": skipped}


async def fetch_and_save_activity(
    strava_activity_id: int, user: User, db: AsyncSession
) -> Optional[Workout]:
    """
    Fetch a single activity from Strava by ID and save it if not already present.
    Used by the webhook handler when a new activity is created.
    Returns the saved Workout or None if it already existed.
    """
    token = await get_valid_access_token(user, db)
    repo = WorkoutRepository(db)

    existing = await repo.get_by_strava_id(strava_activity_id)
    if existing:
        return None

    async with _http_client(timeout=15.0) as client:
        resp = await client.get(
            f"{_API_BASE}/activities/{strava_activity_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code != 200:
        logger.error(
            "Failed to fetch Strava activity %s for user %s: %s",
            strava_activity_id, user.id, resp.text,
        )
        return None

    activity = resp.json()
    workout = _map_activity_to_workout(activity, user.id)
    db.add(workout)
    await db.commit()
    return workout


# ---------------------------------------------------------------------------
# Connect / Disconnect
# ---------------------------------------------------------------------------

async def connect_user(user: User, code: str, db: AsyncSession) -> dict:
    """
    Complete the Strava OAuth flow for an existing user:
    exchange the code, persist tokens, return athlete info.
    """
    try:
        token_data = await exchange_code(code)
    except HTTPException as exc:
        # OAuth authorization codes are one-time. If frontend/user retries the
        # callback request with the same code after a successful connect, Strava
        # returns 400. Treat that as success when account is already connected.
        if exc.status_code == status.HTTP_400_BAD_REQUEST and user.strava_connected:
            logger.info(
                "Strava callback returned 400 for already connected user %s; "
                "assuming repeated/expired OAuth code",
                user.id,
            )
            return {
                "athlete_id": user.strava_athlete_id,
                "athlete_name": user.strava_athlete_name,
            }
        raise

    athlete = token_data.get("athlete", {})
    user.strava_athlete_id = athlete.get("id")
    user.strava_athlete_name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip() or None
    user.strava_access_token = token_data["access_token"]
    user.strava_refresh_token = token_data["refresh_token"]
    user.strava_token_expires_at = token_data["expires_at"]
    user.strava_connected = True
    user.strava_scope = token_data.get("scope") or "activity:read_all,profile:read_all"

    await db.commit()
    logger.info("User %s connected Strava (athlete_id=%s)", user.id, user.strava_athlete_id)

    return {
        "athlete_id": user.strava_athlete_id,
        "athlete_name": user.strava_athlete_name,
    }


async def disconnect_user(user: User, db: AsyncSession) -> None:
    """
    Revoke Strava access and clear all stored tokens.
    """
    if user.strava_access_token:
        try:
            async with _http_client(timeout=10.0) as client:
                await client.post(
                    _DEAUTH_URL,
                    data={"access_token": user.strava_access_token},
                )
        except Exception as exc:
            logger.warning("Strava deauth request failed (ignoring): %s", exc)

    user.strava_athlete_id = None
    user.strava_athlete_name = None
    user.strava_access_token = None
    user.strava_refresh_token = None
    user.strava_token_expires_at = None
    user.strava_connected = False
    user.strava_scope = None
    await db.commit()
    logger.info("User %s disconnected from Strava", user.id)
