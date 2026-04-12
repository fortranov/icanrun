"""
User ORM model.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), default=UserRole.USER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    google_oauth_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Athlete profile fields (optional)
    birth_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "male" | "female" | "other"
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Google OAuth — stores the unique Google user ID ("sub" claim)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)

    # Strava OAuth — tokens are persisted in DB (survive redeployments via mounted volume)
    strava_athlete_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    strava_athlete_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    strava_access_token: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    strava_refresh_token: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    strava_token_expires_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    strava_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    strava_scope: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Email confirmation
    email_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_confirmation_token: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    email_confirmation_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    workouts: Mapped[List["Workout"]] = relationship(
        "Workout", back_populates="user", cascade="all, delete-orphan"
    )
    competitions: Mapped[List["Competition"]] = relationship(
        "Competition", back_populates="user", cascade="all, delete-orphan"
    )
    training_plans: Mapped[List["TrainingPlan"]] = relationship(
        "TrainingPlan", back_populates="user", cascade="all, delete-orphan"
    )
    skips: Mapped[List["Skip"]] = relationship(
        "Skip", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
