"""
Competition data access layer.
"""
from datetime import date
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import Competition
from app.repositories.base import BaseRepository
from app.utils.enums import CompetitionImportance, SportType


class CompetitionRepository(BaseRepository[Competition]):
    model = Competition

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_user(self, user_id: int) -> List[Competition]:
        """Fetch all competitions for a user ordered by date ascending."""
        result = await self.db.execute(
            select(Competition)
            .where(Competition.user_id == user_id)
            .order_by(Competition.date.asc())
        )
        return list(result.scalars().all())

    async def get_by_user_filtered(
        self,
        user_id: int,
        sport_type: Optional[SportType] = None,
        importance: Optional[CompetitionImportance] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Competition]:
        """Fetch competitions with optional filters."""
        conditions = [Competition.user_id == user_id]
        if sport_type:
            conditions.append(Competition.sport_type == sport_type)
        if importance:
            conditions.append(Competition.importance == importance)
        if date_from:
            conditions.append(Competition.date >= date_from)
        if date_to:
            conditions.append(Competition.date <= date_to)
        result = await self.db.execute(
            select(Competition)
            .where(and_(*conditions))
            .order_by(Competition.date.asc())
        )
        return list(result.scalars().all())

    async def get_future_key_competitions(
        self,
        user_id: int,
        from_date: date,
        sport_type: Optional[SportType] = None,
    ) -> List[Competition]:
        """
        Return upcoming KEY competitions for a user (used for plan generation).
        """
        conditions = [
            Competition.user_id == user_id,
            Competition.importance == CompetitionImportance.KEY,
            Competition.date >= from_date,
        ]
        if sport_type:
            conditions.append(Competition.sport_type == sport_type)
        result = await self.db.execute(
            select(Competition)
            .where(and_(*conditions))
            .order_by(Competition.date.asc())
        )
        return list(result.scalars().all())
