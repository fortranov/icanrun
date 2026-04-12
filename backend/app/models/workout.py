"""
Workout ORM model.
"""
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.enums import SportType, WorkoutSource, WorkoutType


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sport_type: Mapped[SportType] = mapped_column(
        SAEnum(SportType), nullable=False, index=True
    )
    workout_type: Mapped[Optional[WorkoutType]] = mapped_column(
        SAEnum(WorkoutType), nullable=True
    )
    source: Mapped[WorkoutSource] = mapped_column(
        SAEnum(WorkoutSource), default=WorkoutSource.MANUAL, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign key to training plan (nullable — workout may not belong to a plan)
    plan_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("training_plans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Garmin activity deduplication.
    # We intentionally do NOT add unique=True here because SQLite treats multiple
    # NULL values as distinct, which would allow duplicates anyway. The application
    # layer (WorkoutRepository.get_by_garmin_id) enforces uniqueness before insert.
    garmin_activity_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )

    # Strava activity deduplication (same reasoning as garmin_activity_id).
    strava_activity_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="workouts")
    plan: Mapped[Optional["TrainingPlan"]] = relationship("TrainingPlan", back_populates="workouts")

    def __repr__(self) -> str:
        return (
            f"<Workout id={self.id} user_id={self.user_id} "
            f"sport={self.sport_type} date={self.date} duration={self.duration_minutes}m>"
        )
