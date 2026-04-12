"""
User and Subscription data access layer.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Find a user by email address (case-insensitive)."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_strava_athlete_id(self, strava_athlete_id: int) -> Optional[User]:
        """Find a user by their Strava athlete ID (used by webhook handler)."""
        result = await self.db.execute(
            select(User).where(User.strava_athlete_id == strava_athlete_id)
        )
        return result.scalar_one_or_none()

    async def get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """Return the user's currently active subscription, if any."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
                (Subscription.expires_at == None) | (Subscription.expires_at > now),
            )
            .order_by(Subscription.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
