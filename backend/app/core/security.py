"""
Security utilities: JWT token creation/verification, password hashing.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: Any,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject (usually user_id) to encode in the token.
        expires_delta: Optional custom expiry. Defaults to settings value.

    Returns:
        Encoded JWT token string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
        # Include a unique jti so two tokens created in the same second are distinct.
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: Any,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token with longer expiry.

    Args:
        subject: The subject (usually user_id) to encode in the token.
        expires_delta: Optional custom expiry. Defaults to settings value.

    Returns:
        Encoded JWT refresh token string.
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)

    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string to decode.

    Returns:
        Decoded payload dict.

    Raises:
        JWTError: If token is invalid or expired.
    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def get_token_subject(token: str) -> Optional[str]:
    """
    Extract the subject (user_id) from a JWT token.

    Returns:
        Subject string or None if token is invalid.
    """
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except JWTError:
        return None
