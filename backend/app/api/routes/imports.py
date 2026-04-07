from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.imports import FitbitImportResponse
from app.services.import_service import import_fitbit_archive

router = APIRouter()


@router.post("/fitbit", response_model=FitbitImportResponse, status_code=status.HTTP_201_CREATED)
async def import_fitbit_endpoint(
    archive: UploadFile = File(...),
    external_user_id: str | None = Form(default=None),
    timezone: str = Form(default="Asia/Shanghai"),
    name: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> FitbitImportResponse:
    try:
        return import_fitbit_archive(
            db=db,
            archive_bytes=await archive.read(),
            filename=archive.filename or "fitbit-export.zip",
            timezone=timezone,
            external_user_id=external_user_id,
            name=name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
