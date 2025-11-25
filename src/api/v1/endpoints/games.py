from pathlib import Path
import shutil
from fastapi import APIRouter, UploadFile, HTTPException
from sqlmodel import Session

from src.core.db import engine
from src.services.import_service import import_single_ledger_strict

router = APIRouter()

@router.post("/upload")
async def upload_game_ledger(file: UploadFile):
    """
    Upload a CSV ledger file for a game.
    The file will be saved to the 'ledgers' directory and then imported.
    """
    if not file.filename:
         raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Ensure ledgers directory exists
    ledgers_dir = Path("ledgers")
    ledgers_dir.mkdir(exist_ok=True)

    file_path = ledgers_dir / file.filename
    
    # Check if file already exists to avoid accidental overwrites? 
    # The requirement didn't specify, but strict mode in import service handles duplicates logic somewhat.
    # However, overwriting the file on disk is probably fine if they want to re-upload.
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Now import it
    try:
        with Session(engine) as session:
            import_single_ledger_strict(session, file_path)
            session.commit()
    except Exception as e:
        # If import fails, maybe we should delete the file? 
        # For now let's leave it for debugging or manual fix.
        raise HTTPException(status_code=500, detail=f"Failed to import ledger: {str(e)}")

    return {"message": f"Successfully imported game from {file.filename}"}
