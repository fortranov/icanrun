"""
Pydantic schemas for Subscription responses and payment-related operations.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.utils.enums import SubscriptionPlan


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    plan: SubscriptionPlan
    started_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

    model_config = {"from_attributes": True}


class PaymentCreateRequest(BaseModel):
    """Request to create a YooKassa payment for subscription upgrade."""
    plan: SubscriptionPlan


class PaymentResponse(BaseModel):
    payment_id: str
    confirmation_url: str
    amount: float
    plan: SubscriptionPlan
