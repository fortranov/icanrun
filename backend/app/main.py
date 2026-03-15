"""
FastAPI application factory.
Configures middleware, routers, startup/shutdown events, and CORS.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import create_tables

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    - On startup: ensure DB tables exist and seed default admin user.
    - On shutdown: clean up resources.
    """
    logger.info("Starting up ICanRun application...")
    # Create all tables (idempotent — safe to run on every startup)
    await create_tables()
    # Seed default admin user
    await seed_admin()
    logger.info("Application startup complete.")
    yield
    logger.info("Application shutting down.")


async def seed_admin() -> None:
    """
    Create the default admin user if it does not already exist.
    Admin credentials are read from application settings.
    """
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.subscription import Subscription
    from app.models.user import User
    from app.repositories.user_repository import UserRepository
    from app.utils.enums import SubscriptionPlan, UserRole
    from datetime import datetime, timedelta, timezone

    async with AsyncSessionLocal() as db:
        try:
            repo = UserRepository(db)
            existing = await repo.get_by_email(settings.admin_email)
            if existing is None:
                admin = User(
                    email=settings.admin_email.lower(),
                    hashed_password=hash_password(settings.admin_password),
                    name="Admin",
                    role=UserRole.ADMIN,
                    is_active=True,
                    email_confirmed=True,
                )
                db.add(admin)
                await db.flush()
                # Give admin a perpetual Pro subscription
                subscription = Subscription(
                    user_id=admin.id,
                    plan=SubscriptionPlan.PRO,
                    is_active=True,
                    expires_at=None,  # Never expires for admin
                )
                db.add(subscription)
                await db.commit()
                logger.info(f"Default admin user created: {settings.admin_email}")
            else:
                # Ensure existing admin has email confirmed (retroactive fix)
                if not existing.email_confirmed:
                    existing.email_confirmed = True
                    await db.commit()
                    logger.info("Admin email_confirmed flag updated.")
                logger.info("Admin user already exists, skipping seed.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to seed admin user: {e}")


def create_app() -> FastAPI:
    """
    FastAPI application factory.
    Returns a configured FastAPI instance.
    """
    app = FastAPI(
        title=settings.app_name,
        description="Triathlon training platform — track, plan, and analyze your endurance training.",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # CORS middleware — allow frontend origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API v1 router
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


# Application instance used by uvicorn
app = create_app()
