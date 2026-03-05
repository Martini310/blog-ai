"""
Authentication service.

Owns all business logic for user registration and login.
Routes must not call DB directly – they call this service.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import (
    AuthError,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    decode_token,
    settings,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def register(self, payload: RegisterRequest) -> User:
        """
        Create a new user. Raises AuthError if the email already exists.
        Password is hashed before storage.
        """
        existing = await self._db.scalar(
            select(User).where(User.email == payload.email)
        )
        if existing:
            raise AuthError("Email already registered.")

        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role="user",
        )
        self._db.add(user)
        await self._db.flush()   # populate user.id without committing

        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return user

    async def login(self, payload: LoginRequest) -> TokenResponse:
        """
        Validate credentials and return JWT pair.
        Raises AuthError on any failure (deliberately vague message to clients).
        """
        user = await self._db.scalar(
            select(User).where(User.email == payload.email)
        )

        if not user or not verify_password(payload.password, user.hashed_password):
            raise AuthError("Invalid email or password.")

        if not user.is_active:
            raise AuthError("Account is disabled.")

        access_token = create_access_token(subject=str(user.id), role=user.role)
        refresh_token = create_refresh_token(subject=str(user.id), role=user.role)

        logger.info("user_login", user_id=str(user.id))
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Issue a new access token from a valid refresh token."""
        try:
            token_data = decode_token(refresh_token)
        except Exception as exc:
            raise AuthError("Invalid or expired refresh token.") from exc

        user = await self._db.get(User, token_data.sub)
        if not user or not user.is_active:
            raise AuthError("User not found or inactive.")

        access_token = create_access_token(subject=str(user.id), role=user.role)
        new_refresh = create_refresh_token(subject=str(user.id), role=user.role)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
