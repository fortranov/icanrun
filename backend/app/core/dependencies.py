"""
Common FastAPI dependencies used across routers.
Provides current user resolution, subscription checks, and admin guard.
"""
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token

if TYPE_CHECKING:
    from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Resolve the current authenticated user from the JWT access token.
    Raises 401 if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Import here to avoid circular imports
    from app.repositories.user_repository import UserRepository
    repo = UserRepository(db)
    user = await repo.get_by_id(int(user_id))
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return user


async def get_current_admin(
    current_user=Depends(get_current_user),
):
    """
    Ensure the current user has admin role.
    Raises 403 if user is not an admin.
    """
    from app.utils.enums import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_subscription(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the active subscription for current user.
    Returns subscription or None if no active subscription.
    """
    from app.repositories.user_repository import UserRepository
    repo = UserRepository(db)
    subscription = await repo.get_active_subscription(current_user.id)
    return subscription


# Type aliases for cleaner router signatures
# Using Any here because forward-referencing the ORM User model causes circular imports.
# In router code, these resolve to the actual User ORM instance at runtime.
CurrentUser = Annotated[object, Depends(get_current_user)]
CurrentAdmin = Annotated[object, Depends(get_current_admin)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
