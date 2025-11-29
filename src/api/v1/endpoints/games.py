"""
Games API endpoints.

This module provides HTTP endpoints for managing game ledgers, including
file upload and import functionality for game data in CSV format.
"""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from src.schemas.schemas import BatchUploadResponse
from src.services.game_service import process_uploaded_file

if TYPE_CHECKING:
    from src.schemas.schemas import FileUploadResult

router = APIRouter()


@router.post("/upload", response_model=BatchUploadResponse)
async def upload_game_ledgers(
    files: Annotated[list[UploadFile], File(description="CSV ledger files to upload")],
) -> BatchUploadResponse:
    """
    Upload one or more CSV ledger files for games.
    Files will be saved to the 'ledgers' directory and then imported.
    """
    logger.info(f"Received batch upload request with {len(files)} file(s)")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results: list[FileUploadResult] = []
    for file in files:
        result = process_uploaded_file(file)
        results.append(result)

    successful = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "error")
    skipped = sum(1 for r in results if r.status == "skipped")

    logger.info(
        f"Batch upload complete: {successful} successful, {failed} failed, {skipped} skipped"
    )

    return BatchUploadResponse(
        total=len(files),
        successful=successful,
        failed=failed,
        skipped=skipped,
        results=results,
    )
