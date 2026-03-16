"""
Pydantic schemas for User-related requests and responses.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from app.utils.enums import UserRole

GenderType = Literal["male", "female", "other"]


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    birth_year: Optional[int] = Field(None, ge=1900, le=2020)
    gender: Optional[GenderType] = None
    weight_kg: Optional[float] = Field(None, gt=20, le=300)
    height_cm: Optional[float] = Field(None, gt=100, le=250)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    birth_year: Optional[int] = Field(None, ge=1900, le=2020)
    gender: Optional[GenderType] = None
    weight_kg: Optional[float] = Field(None, gt=20, le=300)
    height_cm: Optional[float] = Field(None, gt=100, le=250)


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    google_oauth_enabled: bool
    email_confirmed: bool
    birth_year: Optional[int]
    gender: Optional[str]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    last_login_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class UserAdminUpdate(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
