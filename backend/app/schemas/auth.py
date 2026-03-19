"""
Pydantic schemas for authentication endpoints.
"""
from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str


class GoogleCallbackRequest(BaseModel):
    """Body for POST /auth/google/callback."""
    code: str
    redirect_uri: str


class GoogleCallbackResponse(BaseModel):
    """
    Response for POST /auth/google/callback.

    For existing users: access_token + refresh_token are set, requires_terms_acceptance=False.
    For new users: requires_terms_acceptance=True + pending_token (short-lived JWT) + name + email.
    """
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    requires_terms_acceptance: bool = False
    pending_token: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None


class GoogleCompleteRequest(BaseModel):
    """Body for POST /auth/google/complete — finalize Google sign-up after terms acceptance."""
    pending_token: str


class AuthSettingsResponse(BaseModel):
    """Public auth settings — returned without authentication."""
    google_oauth_enabled: bool
