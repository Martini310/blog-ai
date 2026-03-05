"""
FastAPI dependency functions.

All route-level auth and DB session injection happens here.
Business logic never lives in dependencies.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import AuthError, TokenData, decode_token
from app.models.user import User
from sqlalchemy import select

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
) -> TokenData:
    """Extract and validate the Bearer token. Raises 401 on failure."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_token(credentials.credentials)
    except (JWTError, AuthError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Resolve token subject to a User DB row. Raises 401/403 if not found."""
    from uuid import UUID
    try:
        user_id = UUID(token.sub)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.") from exc

    user = await db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency that enforces admin role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


# ---------------------------------------------------------------------------
# Type aliases for clean route signatures
# ---------------------------------------------------------------------------
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
