"""
TrainingPlan ORM model.
"""
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.enums import SportType


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sport_type: Mapped[SportType] = mapped_column(
        SAEnum(SportType), nullable=False
    )
    # Optional: link to a key competition this plan builds toward
    competition_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("competitions.id", ondelete="SET NULL"), nullable=True
    )
    # Target date for plans not linked to a competition
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    weeks_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # JSON array of weekday numbers: [0=Mon, 1=Tue, ..., 6=Sun]
    preferred_days: Mapped[List[int]] = mapped_column(JSON, nullable=False, default=list)
    max_hours_per_week: Mapped[float] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="training_plans")
    competition: Mapped[Optional["Competition"]] = relationship(
        "Competition", back_populates="training_plans"
    )
    workouts: Mapped[List["Workout"]] = relationship(
        "Workout", back_populates="plan"
    )

    def __repr__(self) -> str:
        return (
            f"<TrainingPlan id={self.id} user_id={self.user_id} "
            f"sport={self.sport_type} weeks={self.weeks_count}>"
        )
