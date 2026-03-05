"""
Authentication routes.

Architecture rule: routes validate input shape (via Pydantic) and
call the service layer. Zero business logic here.
"""
from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DBSession
from app.core.security import AuthError
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DBSession) -> UserOut:
    """
    Register a new user account.
    Returns the created user (without sensitive fields).
    """
    try:
        user = await AuthService(db).register(payload)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DBSession) -> TokenResponse:
    """Exchange email + password for a JWT access/refresh token pair."""
    try:
        return await AuthService(db).login(payload)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: DBSession) -> TokenResponse:
    """Issue a new access token from a valid refresh token."""
    try:
        return await AuthService(db).refresh(payload.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser) -> UserOut:
    """Return the authenticated user's profile."""
    return UserOut.model_validate(current_user)
