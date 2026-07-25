"""Common response envelopes and pagination schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    """Pagination metadata for list responses."""

    total: int
    limit: int
    offset: int


class DataEnvelope(BaseModel, Generic[T]):
    """Standard success response for single resources."""

    data: T


class ListEnvelope(BaseModel, Generic[T]):
    """Standard success response for list resources."""

    data: list[T]
    meta: Meta


class ErrorBody(BaseModel):
    """Standard error body."""

    code: str
    message: str


class ErrorEnvelope(BaseModel):
    """Standard error response."""

    error: ErrorBody


class PaginationParams(BaseModel):
    """Bounded offset pagination parameters."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

