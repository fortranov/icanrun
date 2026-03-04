"""
Competition ORM model.
"""
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.enums import CompetitionImportance, CompetitionType, SportType


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sport_type: Mapped[SportType] = mapped_column(
        SAEnum(SportType), nullable=False, index=True
    )
    competition_type: Mapped[CompetitionType] = mapped_column(
        SAEnum(CompetitionType), nullable=False
    )
    importance: Mapped[CompetitionImportance] = mapped_column(
        SAEnum(CompetitionImportance), default=CompetitionImportance.KEY, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Distance for open-ended competition types:
    # - swimming: distance in meters
    # - cycling: distance in km
    distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="competitions")
    training_plans: Mapped[list["TrainingPlan"]] = relationship(
        "TrainingPlan", back_populates="competition"
    )

    def __repr__(self) -> str:
        return f"<Competition id={self.id} name={self.name} date={self.date} type={self.competition_type}>"
