"""Game-related business logic."""

from pathlib import Path
import shutil

from fastapi import UploadFile
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from src.core.db import engine
from src.core.exceptions import AppError
from src.schemas.schemas import FileUploadResult
from src.services.import_service import ImportResult, import_single_ledger


def process_uploaded_file(file: UploadFile) -> FileUploadResult:  # noqa: PLR0911
    """Process a single uploaded file. Returns result without raising exceptions."""
    if not file.filename:
        return FileUploadResult(
            filename="unknown",
            status="error",
            message="No filename provided",
        )

    # Sanitize filename to prevent path traversal attacks (S2083)
    # Extract only the base name, removing any directory components
    filename = Path(file.filename).name

    if not filename.endswith(".csv"):
        return FileUploadResult(
            filename=filename,
            status="error",
            message="File must be a CSV",
        )

    # Ensure ledgers directory exists
    ledgers_dir = Path("ledgers").resolve()
    ledgers_dir.mkdir(exist_ok=True)

    file_path = (ledgers_dir / filename).resolve()

    # Verify the resolved path is within the ledgers directory (defense in depth)
    if not file_path.is_relative_to(ledgers_dir):
        logger.warning(f"Path traversal attempt detected: {file.filename}")
        return FileUploadResult(
            filename=filename,
            status="error",
            message="Invalid filename",
        )
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
    except AppError as e:
        logger.error(f"Application error importing {filename}: {e.message}")
        return FileUploadResult(
            filename=filename,
            status="error",
            message=e.message,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception(f"Unexpected error processing {filename}: {e}")
        return FileUploadResult(
            filename=filename,
            status="error",
            message="Unexpected error during import",
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
