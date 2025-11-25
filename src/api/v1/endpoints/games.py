from pathlib import Path
import shutil

from fastapi import APIRouter, HTTPException, UploadFile
from loguru import logger
from sqlmodel import Session

from src.core.db import engine
from src.services.import_service import import_single_ledger_strict

router = APIRouter()


@router.post("/upload")
async def upload_game_ledger(file: UploadFile) -> dict[str, str]:
    """
    Upload a CSV ledger file for a game.
    The file will be saved to the 'ledgers' directory and then imported.
    """
    logger.info(f"Received game ledger upload request: {file.filename}")

    if not file.filename:
        logger.warning("Upload rejected: No filename provided")
        raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.endswith(".csv"):
        logger.warning(f"Upload rejected: {file.filename} is not a CSV file")
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Ensure ledgers directory exists
    ledgers_dir = Path("ledgers")
    ledgers_dir.mkdir(exist_ok=True)  # noqa: ASYNC240
    logger.debug(f"Ledgers directory ready: {ledgers_dir}")

    file_path = ledgers_dir / file.filename
    logger.info(f"Saving file to: {file_path}")

    # Check if file already exists to avoid accidental overwrites?
    # The requirement didn't specify, but strict mode in import service handles duplicates logic somewhat.
    # However, overwriting the file on disk is probably fine if they want to re-upload.

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.success(f"File saved successfully: {file.filename}")
    except Exception as e:
        logger.error(f"Failed to save file {file.filename}: {e!s}")
        raise HTTPException(
            status_code=500, detail=f"Failed to save file: {e!s}"
        ) from e

    # Now import it
    logger.info(f"Starting import of {file.filename}...")
    try:
        with Session(engine) as session:
            import_single_ledger_strict(session, file_path)
            session.commit()
        logger.success(f"Successfully imported game from {file.filename}")
    except Exception as e:
        # If import fails, maybe we should delete the file?
        # For now let's leave it for debugging or manual fix.
        logger.error(f"Failed to import ledger {file.filename}: {e!s}")
        raise HTTPException(
            status_code=500, detail=f"Failed to import ledger: {e!s}"
        ) from e

    return {"message": f"Successfully imported game from {file.filename}"}
