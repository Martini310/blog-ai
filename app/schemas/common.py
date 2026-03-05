"""
Shared schema primitives reused across the API surface.
"""
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard envelope for all API responses."""

    success: bool = True
    data: T
    message: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None


class IDResponse(BaseModel):
    """Returned after creating a resource."""
    id: UUID


# Base for all DB-backed response schemas (enables ORM mode)
class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
