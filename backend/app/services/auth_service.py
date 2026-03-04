"""
Authentication service.

Handles user registration, login, JWT token lifecycle,
and in-memory refresh token blacklist (no Redis required).

Blacklist strategy:
  - On logout the refresh token's JTI (jti claim) is stored in a module-level set.
  - On refresh, the JTI is checked against the blacklist before issuing new tokens.
  - The blacklist also stores expiry time so a background sweep can prune it.
  - For multi-process deployments, swap the in-memory set for a Redis key/TTL.
"""
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.subscription import Subscription
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from app.utils.enums import SubscriptionPlan, UserRole

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory refresh token blacklist
# Stores {jti: expiry_unix_timestamp}. Pruned on every blacklist-check call.
# ---------------------------------------------------------------------------
_blacklisted_jtis: dict[str, float] = {}


def _prune_blacklist() -> None:
    """Remove expired JTIs from the blacklist to prevent unbounded growth."""
    now = time.time()
    expired = [jti for jti, exp in _blacklisted_jtis.items() if exp < now]
    for jti in expired:
        del _blacklisted_jtis[jti]


def _blacklist_token(jti: str, expires_at: datetime) -> None:
    """Add a JTI to the blacklist."""
    _prune_blacklist()
    _blacklisted_jtis[jti] = expires_at.timestamp()


def _is_blacklisted(jti: str) -> bool:
    """Return True if the JTI has been blacklisted (and is not yet expired)."""
    _prune_blacklist()
    return jti in _blacklisted_jtis


# ---------------------------------------------------------------------------
# JWT helpers with JTI support
# ---------------------------------------------------------------------------

def _create_refresh_token_with_jti(user_id: int) -> Tuple[str, str]:
    """
    Create a refresh token that embeds a unique jti claim.

    Returns:
        (encoded_token, jti) — caller needs jti to later blacklist the token.
    """
    from jose import jwt as _jwt

    jti = str(uuid.uuid4())
    expires_delta = timedelta(days=settings.refresh_token_expire_days)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "jti": jti,
    }
    token = _jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class AuthService:
    """
    Encapsulates all authentication business logic:
    registration, login, token refresh, and logout.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register(self, data: UserCreate) -> Tuple[User, str, str]:
        """
        Register a new user and assign a 30-day Trial subscription.

        Args:
            data: Validated registration payload (UserCreate schema).

        Returns:
            (user, access_token, refresh_token)

        Raises:
            HTTPException 400 if the email is already taken.
        """
        email_lower = data.email.lower()

        existing = await self.user_repo.get_by_email(email_lower)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
                headers={"X-Error-Code": "EMAIL_TAKEN"},
            )

        # Create user
        user = User(
            email=email_lower,
            hashed_password=hash_password(data.password),
            name=data.name,
            role=UserRole.USER,
            is_active=True,
            birth_year=data.birth_year,
            gender=data.gender,
            weight_kg=data.weight_kg,
            height_cm=data.height_cm,
        )
        self.db.add(user)
        await self.db.flush()  # get user.id without committing

        # Assign 30-day Trial subscription
        trial_subscription = Subscription(
            user_id=user.id,
            plan=SubscriptionPlan.TRIAL,
            is_active=True,
            started_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.db.add(trial_subscription)
        await self.db.flush()

        access_token = create_access_token(user.id)
        refresh_token, _ = _create_refresh_token_with_jti(user.id)

        logger.info(f"New user registered: {email_lower} (id={user.id})")
        return user, access_token, refresh_token

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(self, email: str, password: str) -> Tuple[User, str, str]:
        """
        Authenticate a user with email/password and return tokens.

        Args:
            email: User's email address.
            password: Plain text password.

        Returns:
            (user, access_token, refresh_token)

        Raises:
            HTTPException 401 for invalid credentials.
            HTTPException 400 for inactive accounts.
        """
        user = await self.user_repo.get_by_email(email.lower())

        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer", "X-Error-Code": "INVALID_CREDENTIALS"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is disabled",
                headers={"X-Error-Code": "ACCOUNT_DISABLED"},
            )

        access_token = create_access_token(user.id)
        refresh_token, _ = _create_refresh_token_with_jti(user.id)

        logger.info(f"User logged in: {user.email} (id={user.id})")
        return user, access_token, refresh_token

    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------

    async def refresh_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Validate a refresh token and issue a new access + refresh token pair.
        The old refresh token is blacklisted (rotation strategy).

        Args:
            refresh_token: The JWT refresh token from the client.

        Returns:
            (new_access_token, new_refresh_token)

        Raises:
            HTTPException 401 if token is invalid, expired, or blacklisted.
        """
        invalid_exc = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer", "X-Error-Code": "INVALID_REFRESH_TOKEN"},
        )

        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise invalid_exc

        # Verify token type
        if payload.get("type") != "refresh":
            raise invalid_exc

        # Check blacklist
        jti = payload.get("jti")
        if jti and _is_blacklisted(jti):
            logger.warning(f"Blacklisted refresh token used (jti={jti})")
            raise invalid_exc

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise invalid_exc

        user = await self.user_repo.get_by_id(int(user_id_str))
        if user is None or not user.is_active:
            raise invalid_exc

        # Blacklist the used refresh token (token rotation)
        if jti:
            exp_ts = payload.get("exp", 0)
            exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            _blacklist_token(jti, exp_dt)

        new_access_token = create_access_token(user.id)
        new_refresh_token, _ = _create_refresh_token_with_jti(user.id)

        logger.info(f"Tokens refreshed for user id={user.id}")
        return new_access_token, new_refresh_token

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def logout(self, refresh_token: Optional[str]) -> None:
        """
        Invalidate a refresh token by blacklisting its JTI.
        Silently succeeds even if the token is already invalid.

        Args:
            refresh_token: The refresh token to invalidate. May be None.
        """
        if not refresh_token:
            return

        try:
            payload = decode_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                exp_ts = payload.get("exp", 0)
                exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
                _blacklist_token(jti, exp_dt)
                logger.info(f"Refresh token blacklisted on logout (jti={jti})")
        except JWTError:
            # Token is already invalid — nothing to blacklist
            pass
