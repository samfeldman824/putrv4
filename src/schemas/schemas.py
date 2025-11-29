"""Pydantic request/response schemas for API endpoints."""

from pydantic import BaseModel


class FileUploadResult(BaseModel):
    """Result of a single file upload."""

    filename: str
    status: str
    message: str


class BatchUploadResponse(BaseModel):
    """Response for batch upload operation."""

    total: int
    successful: int
    failed: int
    skipped: int
    results: list[FileUploadResult]
