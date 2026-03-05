"""
User-facing schemas (never expose hashed_password).
"""
from datetime import datetime
from uuid import UUID

from pydantic import EmailStr

from app.schemas.common import ORMBase


class UserOut(ORMBase):
    id: UUID
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
