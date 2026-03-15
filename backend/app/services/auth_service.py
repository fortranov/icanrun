"""
Authentication service.

Handles user registration, login, JWT token lifecycle,
and in-memory refresh token blacklist (no Redis required).

Blacklist strategy:
  - On logout the refresh token's JTI (jti claim) is stored in a module-level set.
  - On refresh, the JTI is checked against the blacklist before issuing new tokens.
  - The blacklist also stores expiry time so a background sweep can prune it.
  - For multi-process deployments, swap the in-memory set for a Redis key/TTL.

Email confirmation flow:
  - If email_confirmation_enabled == true in DB settings, registration does NOT
    return tokens. Instead it sends a confirmation email and returns None tokens.
  - The confirmation JWT is a short-lived token (type="email_confirm").
  - On confirmation the user's email_confirmed flag is set to True and the token
    field is cleared.
  - Users with unconfirmed email are blocked from login (EMAIL_NOT_CONFIRMED 403).
"""
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy import select
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
# Email confirmation JWT helpers
# ---------------------------------------------------------------------------

def _create_email_confirm_token(user_id: int, expires_hours: int) -> str:
    """
    Create a short-lived JWT used as the email confirmation link token.

    Token type is "email_confirm" so it cannot be used as an access/refresh token.
    """
    from jose import jwt as _jwt

    expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "email_confirm",
        "jti": str(uuid.uuid4()),
    }
    return _jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


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

    async def register(
        self, data: UserCreate
    ) -> Tuple[User, Optional[str], Optional[str]]:
        """
        Register a new user and assign a 30-day Trial subscription.

        If email confirmation is enabled (DB setting), the user is created
        with email_confirmed=False and a confirmation email is queued.
        In that case access_token and refresh_token are both None — the caller
        should tell the client to check their inbox.

        If email confirmation is disabled, behaviour is unchanged: the user is
        immediately active and tokens are returned.

        Args:
            data: Validated registration payload (UserCreate schema).

        Returns:
            (user, access_token | None, refresh_token | None)

        Raises:
            HTTPException 400 if the email is already taken.
        """
        from app.services.settings_service import SettingsService

        email_lower = data.email.lower()

        existing = await self.user_repo.get_by_email(email_lower)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
                headers={"X-Error-Code": "EMAIL_TAKEN"},
            )

        svc = SettingsService(self.db)
        confirmation_enabled = await svc.email_confirmation_enabled()

        # Create user
        user = User(
            email=email_lower,
            hashed_password=hash_password(data.password),
            name=data.name,
            role=UserRole.USER,
            is_active=True,
            email_confirmed=not confirmation_enabled,  # confirmed immediately if feature off
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

        if confirmation_enabled:
            token_hours = await svc.confirmation_token_hours()
            confirm_token = _create_email_confirm_token(user.id, token_hours)
            user.email_confirmation_token = confirm_token
            user.email_confirmation_sent_at = datetime.now(timezone.utc)
            await self.db.flush()

            # Fire-and-forget email (errors are logged, not raised, to avoid
            # rolling back the registration transaction)
            await self._send_confirmation_email(user, confirm_token, svc, token_hours)

            logger.info(
                f"New user registered (pending confirmation): {email_lower} (id={user.id})"
            )
            return user, None, None

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

        # Block login if email confirmation is required but not yet done
        if not user.email_confirmed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not confirmed. Please check your inbox.",
                headers={"X-Error-Code": "EMAIL_NOT_CONFIRMED"},
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

    # ------------------------------------------------------------------
    # Email confirmation
    # ------------------------------------------------------------------

    async def confirm_email(self, token: str) -> User:
        """
        Validate the email confirmation JWT and activate the user account.

        Args:
            token: The raw JWT from the confirmation link query string.

        Returns:
            The activated User.

        Raises:
            HTTPException 400 for invalid/expired tokens.
            HTTPException 400 if already confirmed.
        """
        invalid_exc = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired confirmation link",
            headers={"X-Error-Code": "INVALID_CONFIRM_TOKEN"},
        )

        try:
            payload = decode_token(token)
        except JWTError:
            raise invalid_exc

        if payload.get("type") != "email_confirm":
            raise invalid_exc

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise invalid_exc

        user = await self.user_repo.get_by_id(int(user_id_str))
        if user is None:
            raise invalid_exc

        if user.email_confirmed:
            # Idempotent — already confirmed is not an error on the UI side,
            # but we return a distinct message.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already confirmed",
                headers={"X-Error-Code": "ALREADY_CONFIRMED"},
            )

        # Verify stored token matches (guards against re-use of old tokens)
        if user.email_confirmation_token != token:
            raise invalid_exc

        user.email_confirmed = True
        user.email_confirmation_token = None
        user.email_confirmation_sent_at = None
        await self.db.flush()

        logger.info(f"Email confirmed for user id={user.id}")
        return user

    async def resend_confirmation(self, email: str) -> None:
        """
        Re-send the confirmation email for a given address.

        Silently does nothing if confirmation is disabled, or if the user
        does not exist or is already confirmed (prevents email enumeration).

        Args:
            email: The email address to resend confirmation for.
        """
        from app.services.settings_service import SettingsService

        svc = SettingsService(self.db)
        if not await svc.email_confirmation_enabled():
            return

        user = await self.user_repo.get_by_email(email.lower())
        if user is None or user.email_confirmed:
            # Silent — do not reveal whether the email exists
            return

        token_hours = await svc.confirmation_token_hours()
        confirm_token = _create_email_confirm_token(user.id, token_hours)
        user.email_confirmation_token = confirm_token
        user.email_confirmation_sent_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self._send_confirmation_email(user, confirm_token, svc, token_hours)
        logger.info(f"Confirmation email resent to {user.email}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _send_confirmation_email(
        self,
        user: User,
        token: str,
        svc,
        token_hours: int,
    ) -> None:
        """
        Attempt to send the confirmation email.
        Errors are logged but NOT re-raised so the registration transaction
        is never rolled back due to SMTP issues.
        """
        from app.services.email_service import send_confirmation_email

        try:
            await send_confirmation_email(
                to_email=user.email,
                to_name=user.name,
                confirmation_token=token,
                smtp_host=await svc.smtp_host(),
                smtp_port=await svc.smtp_port(),
                smtp_user=await svc.smtp_user(),
                smtp_password=await svc.smtp_password(),
                from_email=await svc.smtp_from_email(),
                from_name=await svc.smtp_from_name(),
                token_hours=token_hours,
            )
        except Exception as exc:
            logger.error(
                f"Failed to send confirmation email to {user.email}: {exc}"
            )
