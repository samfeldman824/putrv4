"""
Games API endpoints.

This module provides HTTP endpoints for managing game ledgers, including
file upload and import functionality for game data in CSV format.
"""

from pathlib import Path
import shutil
from typing import Annotated

from fastapi import APIRouter, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from src.core.db import engine
from src.services.import_service import ImportResult, import_single_ledger

router = APIRouter()


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


def _process_single_file(file: UploadFile) -> FileUploadResult:  # noqa: PLR0911
    """Process a single uploaded file. Returns result without raising exceptions."""
    if not file.filename:
        return FileUploadResult(
            filename="unknown",
            status="error",
            message="No filename provided",
        )

    filename = file.filename

    if not filename.endswith(".csv"):
        return FileUploadResult(
            filename=filename,
            status="error",
            message="File must be a CSV",
        )

    # Ensure ledgers directory exists
    ledgers_dir = Path("ledgers")
    ledgers_dir.mkdir(exist_ok=True)

    file_path = ledgers_dir / filename
    logger.info(f"Saving file to: {file_path}")

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.success(f"File saved successfully: {filename}")
    except OSError as e:
        logger.error(f"Failed to save file {filename}: {e!s}")
        return FileUploadResult(
            filename=filename,
            status="error",
            message=f"Failed to save file: {e!s}",
        )

    # Now import it
    logger.info(f"Starting import of {filename}...")
    try:
        with Session(engine) as session:
            result = import_single_ledger(session, file_path)
            session.commit()
        logger.success(f"Import completed for {filename} with result: {result}")
    except SQLAlchemyError as e:
        logger.error(f"Failed to import ledger {filename}: {e!s}")
        return FileUploadResult(
            filename=filename,
            status="error",
            message=f"Failed to import ledger: {e!s}",
        )

    if result == ImportResult.GAME_EXISTS:
        return FileUploadResult(
            filename=filename,
            status="skipped",
            message="Game already exists",
        )
    if result == ImportResult.MISSING_NICKNAMES:
        return FileUploadResult(
            filename=filename,
            status="error",
            message="Contains unknown player nicknames",
        )
    return FileUploadResult(
        filename=filename,
        status="success",
        message="Successfully imported",
    )


@router.post("/upload", response_model=BatchUploadResponse)
async def upload_game_ledgers(
    files: Annotated[list[UploadFile], "List of CSV ledger files to upload"],
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
        result = _process_single_file(file)
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
