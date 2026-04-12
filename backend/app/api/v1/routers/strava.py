"""
Strava integration router.

Endpoints:
  GET  /strava/auth                — return Strava OAuth2 authorization URL
  POST /strava/callback            — exchange code for tokens, connect account
  POST /strava/disconnect          — revoke Strava access and clear tokens
  POST /strava/sync                — manually sync recent activities
  GET  /strava/status              — connection status for current user
  GET  /strava/webhook             — Strava webhook verification (hub challenge)
  POST /strava/webhook             — receive Strava webhook events (new/updated activities)
  POST /strava/webhook/register    — (admin) register the webhook subscription with Strava
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import CurrentAdmin, CurrentUser, DatabaseSession
from app.repositories.user_repository import UserRepository
from app.services import strava_service

router = APIRouter(prefix="/strava", tags=["strava"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StravaAuthUrlResponse(BaseModel):
    auth_url: str


class StravaCallbackRequest(BaseModel):
    code: str


class StravaCallbackResponse(BaseModel):
    athlete_id: int
    athlete_name: str


class StravaSyncResponse(BaseModel):
    synced: int
    skipped: int


class StravaStatusResponse(BaseModel):
    connected: bool
    athlete_id: int | None = None
    athlete_name: str | None = None


# ---------------------------------------------------------------------------
# GET /strava/auth  — get authorization URL (requires login)
# ---------------------------------------------------------------------------

@router.get(
    "/auth",
    response_model=StravaAuthUrlResponse,
    summary="Get Strava OAuth2 authorization URL",
)
async def get_strava_auth_url(current_user: CurrentUser) -> StravaAuthUrlResponse:
    """
    Return the URL the user should be redirected to in order to authorize Strava.
    The redirect_uri must be registered in your Strava API application settings.
    """
    auth_url = strava_service.build_auth_url()
    return StravaAuthUrlResponse(auth_url=auth_url)


# ---------------------------------------------------------------------------
# POST /strava/callback  — exchange OAuth code, save tokens (requires login)
# ---------------------------------------------------------------------------

@router.post(
    "/callback",
    response_model=StravaCallbackResponse,
    summary="Exchange Strava OAuth code and connect the account",
)
async def strava_callback(
    data: StravaCallbackRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> StravaCallbackResponse:
    """
    Called by the frontend after Strava redirects back with `?code=...`.
    Exchanges the code for tokens and stores them in the database.
    Tokens persist across container restarts because the DB lives on a mounted volume.
    """
    result = await strava_service.connect_user(current_user, data.code, db)
    return StravaCallbackResponse(
        athlete_id=result["athlete_id"],
        athlete_name=result["athlete_name"] or "",
    )


# ---------------------------------------------------------------------------
# GET /strava/status  — connection status
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    response_model=StravaStatusResponse,
    summary="Get Strava connection status for current user",
)
async def strava_status(current_user: CurrentUser) -> StravaStatusResponse:
    return StravaStatusResponse(
        connected=current_user.strava_connected,
        athlete_id=current_user.strava_athlete_id,
        athlete_name=current_user.strava_athlete_name,
    )


# ---------------------------------------------------------------------------
# POST /strava/disconnect  — revoke access
# ---------------------------------------------------------------------------

@router.post(
    "/disconnect",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect Strava from this account",
)
async def strava_disconnect(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> None:
    """Revoke Strava tokens and clear all stored credentials."""
    await strava_service.disconnect_user(current_user, db)


# ---------------------------------------------------------------------------
# POST /strava/sync  — manual sync
# ---------------------------------------------------------------------------

@router.post(
    "/sync",
    response_model=StravaSyncResponse,
    summary="Manually sync Strava activities (last 30 days)",
)
async def strava_sync(
    current_user: CurrentUser,
    db: DatabaseSession,
    days: int = Query(30, ge=1, le=365, description="How many days back to sync"),
) -> StravaSyncResponse:
    """
    Fetch the user's recent Strava activities and import them as workouts.
    Already-imported activities are skipped (deduplicated by strava_activity_id).
    """
    result = await strava_service.sync_activities(current_user, db, days=days)
    return StravaSyncResponse(synced=result["synced"], skipped=result["skipped"])


# ---------------------------------------------------------------------------
# GET /strava/webhook  — Strava subscription verification handshake
# ---------------------------------------------------------------------------

@router.get(
    "/webhook",
    summary="Strava webhook verification (do not call manually)",
)
async def strava_webhook_verify(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    """
    Strava sends a GET request with hub.challenge when registering the webhook.
    We must echo back {"hub.challenge": value} within 2 seconds.
    """
    if hub_mode != "subscribe" or hub_verify_token != settings.strava_webhook_verify_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook verification token",
        )
    return {"hub.challenge": hub_challenge}


# ---------------------------------------------------------------------------
# POST /strava/webhook  — receive activity events
# ---------------------------------------------------------------------------

class _WebhookEvent(BaseModel):
    object_type: str          # "activity" | "athlete"
    object_id: int            # activity_id or athlete_id
    aspect_type: str          # "create" | "update" | "delete"
    owner_id: int             # Strava athlete ID of the owner
    subscription_id: int
    event_time: int


async def _process_webhook_event(event: _WebhookEvent) -> None:
    """
    Background task: fetch the activity and save it if it doesn't already exist.
    Runs after the 200 response is already sent to Strava.
    """
    if event.object_type != "activity" or event.aspect_type != "create":
        return  # We only handle new activity events

    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            repo = UserRepository(db)
            user = await repo.get_by_strava_athlete_id(event.owner_id)
            if user is None:
                logger.warning("Webhook: no user found for Strava athlete_id=%s", event.owner_id)
                return

            workout = await strava_service.fetch_and_save_activity(
                event.object_id, user, db
            )
            if workout:
                logger.info(
                    "Webhook: saved activity %s for user %s", event.object_id, user.id
                )
        except Exception as exc:
            logger.error("Webhook processing error: %s", exc, exc_info=True)


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Receive Strava webhook events (new/updated activities)",
)
async def strava_webhook_event(
    event: _WebhookEvent,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Strava posts here when an athlete creates, updates, or deletes an activity.
    We respond immediately with 200 and process asynchronously to stay within the
    2-second response window.
    """
    background_tasks.add_task(_process_webhook_event, event)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /strava/webhook/register  — admin: register webhook subscription
# ---------------------------------------------------------------------------

@router.post(
    "/webhook/register",
    summary="(Admin) Register the webhook subscription with Strava",
)
async def register_webhook(current_admin: CurrentAdmin) -> dict:
    """
    One-time registration of the push_subscription endpoint with Strava.
    Each app may have only one subscription; calling this again replaces the old one.
    """
    import httpx

    callback_url = f"{settings.frontend_url.rstrip('/')}/api/v1/strava/webhook"
    # The callback URL must be publicly reachable from Strava's servers.
    # Use the backend URL directly if running behind a reverse proxy without /api/v1 prefix.
    # Adjust this to point directly to the backend if needed.
    backend_base = settings.frontend_url.rstrip("/")
    # Prefer explicit backend URL if available; fall back to frontend_url + /api/v1
    callback_url = f"{backend_base}/api/v1/strava/webhook"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://www.strava.com/api/v3/push_subscriptions",
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "callback_url": callback_url,
                "verify_token": settings.strava_webhook_verify_token,
            },
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Strava webhook registration failed: {resp.text}",
        )
    return resp.json()
