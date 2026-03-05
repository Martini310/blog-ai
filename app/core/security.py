"""
Security utilities: password hashing and JWT token management.

Roles are stored as a string field on the User model.
The 'admin' role bypasses standard permission checks.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


# ---------------------------------------------------------------------------
# Password hashing (bcrypt, work-factor 12)
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Return bcrypt hash of *plain* password."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored *hashed* password."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

class TokenData(BaseModel):
    sub: str          # user UUID as string
    role: str
    jti: str | None = None   # JWT ID – can be used for token revocation


def create_access_token(
    subject: str,
    role: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Mint a short-lived access token."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, role: str) -> str:
    """Mint a long-lived refresh token."""
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    return TokenData(sub=payload["sub"], role=payload["role"], jti=payload.get("jti"))


# ---------------------------------------------------------------------------
# FastAPI dependency helpers (used in api/dependencies.py)
# ---------------------------------------------------------------------------

class AuthError(Exception):
    """Raised when authentication or authorisation fails."""
