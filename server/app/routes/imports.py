from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import importer

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/preview")
async def preview(file: UploadFile = File(...)):
    """Parse an uploaded file and return the normalized rows (no DB write)."""
    content = await file.read()
    try:
        rows = importer.parse(file.filename or "upload", content)
    except Exception as exc:
        raise HTTPException(400, f"Could not parse file: {exc}")
    return {"filename": file.filename, "count": len(rows), "rows": rows[:50]}


@router.post("/patients")
async def import_patients(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Parse and import patient records into the database."""
    content = await file.read()
    try:
        rows = importer.parse(file.filename or "upload", content)
    except Exception as exc:
        raise HTTPException(400, f"Could not parse file: {exc}")
    if not rows:
        raise HTTPException(400, "No records found in file")
    return importer.import_patients(db, rows)
