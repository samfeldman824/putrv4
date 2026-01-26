"""Error response schemas for API documentation."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Standard error detail structure."""

    code: str
    message: str
    details: dict[
        str, str | int | float | bool | list[str] | list[dict[str, str | int]] | None
    ] = {}


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""

    error: ErrorDetail
