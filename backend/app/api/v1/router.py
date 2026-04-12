"""
Main API v1 router — aggregates all sub-routers.
Add new routers here as features are implemented.
"""
from fastapi import APIRouter

from app.api.v1.routers.admin import router as admin_router
from app.api.v1.routers.analytics import router as analytics_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.competitions import router as competitions_router
from app.api.v1.routers.plans import router as plans_router
from app.api.v1.routers.strava import router as strava_router
from app.api.v1.routers.subscriptions import router as subscriptions_router
from app.api.v1.routers.users import router as users_router
from app.api.v1.routers.workouts import router as workouts_router

api_router = APIRouter()

# Health check
@api_router.get("/health", tags=["health"])
async def health_check():
    """API health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}


# Feature routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(workouts_router)
api_router.include_router(competitions_router)
api_router.include_router(plans_router)
api_router.include_router(analytics_router)
api_router.include_router(subscriptions_router)
api_router.include_router(strava_router)
api_router.include_router(admin_router)
