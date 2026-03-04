"""
Generic base repository with common CRUD operations.
All model-specific repositories inherit from this class.
"""
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository providing standard CRUD methods for SQLAlchemy models.
    Subclass and set `model` to the target ORM model class.
    """

    model: Type[ModelType]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, record_id: int) -> Optional[ModelType]:
        """Fetch a single record by primary key."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Fetch all records with optional pagination."""
        result = await self.db.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, instance: ModelType) -> ModelType:
        """Persist a new model instance."""
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Delete a model instance from the database."""
        await self.db.delete(instance)
        await self.db.flush()

    async def save(self, instance: ModelType) -> ModelType:
        """Flush pending changes and refresh the instance."""
        await self.db.flush()
        await self.db.refresh(instance)
        return instance
