"""
TrainingPlan data access layer.
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import TrainingPlan
from app.repositories.base import BaseRepository
from app.utils.enums import SportType


class PlanRepository(BaseRepository[TrainingPlan]):
    model = TrainingPlan

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_active_by_user(self, user_id: int) -> List[TrainingPlan]:
        """Return all active training plans for a user."""
        result = await self.db.execute(
            select(TrainingPlan).where(
                TrainingPlan.user_id == user_id,
                TrainingPlan.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def get_active_by_user_and_sport(
        self, user_id: int, sport_type: SportType
    ) -> Optional[TrainingPlan]:
        """Return the active plan for a specific user/sport combination."""
        result = await self.db.execute(
            select(TrainingPlan).where(
                TrainingPlan.user_id == user_id,
                TrainingPlan.sport_type == sport_type,
                TrainingPlan.is_active == True,
            ).limit(1)
        )
        return result.scalar_one_or_none()
