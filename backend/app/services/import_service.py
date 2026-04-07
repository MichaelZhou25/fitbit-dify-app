from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.importers.fitabase_merged import FitabaseImportResult, load_fitabase_merged_export
from app.importers.fitbit_export import FitbitImportResult, load_fitbit_export
from app.models.raw_segment import RawSegment
from app.models.user import User
from app.schemas.imports import FitbitImportResponse
from app.schemas.user import UserCreateRequest
from app.services.user_service import create_user


def import_fitbit_archive(
    db: Session,
    *,
    archive_bytes: bytes,
    filename: str,
    timezone: str,
    external_user_id: str | None,
    name: str | None,
) -> FitbitImportResponse:
    if not filename.lower().endswith(".zip"):
        raise ValueError("Only .zip archives are supported in the import API.")

    with tempfile.TemporaryDirectory() as temp_dir:
        archive_path = Path(temp_dir) / filename
        archive_path.write_bytes(archive_bytes)
        extract_dir = Path(temp_dir) / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            with ZipFile(archive_path) as archive:
                archive.extractall(extract_dir)
        except BadZipFile as exc:
            raise ValueError("Uploaded file is not a valid zip archive.") from exc

        mode = detect_export_mode(extract_dir)
        if mode == "fitabase_merged":
            result = load_fitabase_merged_export(export_path=extract_dir, timezone=timezone)
            return _persist_fitabase_result(db=db, result=result, timezone=timezone)

        if not external_user_id:
            raise ValueError("external_user_id is required for single-user Fitbit exports.")

        result = load_fitbit_export(export_path=extract_dir, timezone=timezone)
        return _persist_fitbit_result(
            db=db,
            result=result,
            timezone=timezone,
            external_user_id=external_user_id,
            name=name,
        )


def detect_export_mode(export_dir: Path) -> str:
    merged_paths = list(export_dir.rglob("*_merged.csv"))
    if merged_paths:
        return "fitabase_merged"
    return "fitbit_export"


def _persist_fitbit_result(
    *,
    db: Session,
    result: FitbitImportResult,
    timezone: str,
    external_user_id: str,
    name: str | None,
) -> FitbitImportResponse:
    if not result.segments:
        return FitbitImportResponse(
            mode="fitbit_export",
            discovered_sources=result.discovered_sources,
            processed_sources=result.processed_sources,
            skipped_sources=result.skipped_sources,
            generated_segments=0,
            inserted_users=0,
            inserted_segments=0,
            skipped_existing=0,
            metrics_detected=result.metrics_detected,
            warnings=result.warnings,
        )

    existing_user = db.scalar(select(User).where(User.external_user_id == external_user_id))
    user = create_user(
        db=db,
        payload=UserCreateRequest(
            external_user_id=external_user_id,
            name=name,
            timezone=timezone,
        ),
    )
    inserted_segments, skipped_existing = _persist_imported_segments(
        db=db,
        user_id=user.id,
        source_type="fitbit_export",
        segments=result.segments,
    )

    return FitbitImportResponse(
        mode="fitbit_export",
        affected_user_ids=[user.id],
        affected_external_user_ids=[user.external_user_id],
        discovered_sources=result.discovered_sources,
        processed_sources=result.processed_sources,
        skipped_sources=result.skipped_sources,
        generated_segments=len(result.segments),
        inserted_users=0 if existing_user else 1,
        inserted_segments=inserted_segments,
        skipped_existing=skipped_existing,
        metrics_detected=result.metrics_detected,
        warnings=result.warnings,
    )


def _persist_fitabase_result(
    *,
    db: Session,
    result: FitabaseImportResult,
    timezone: str,
) -> FitbitImportResponse:
    affected_user_ids: list[str] = []
    affected_external_ids: list[str] = []
    inserted_users = 0
    inserted_segments = 0
    skipped_existing = 0

    for source_user_id, segments in sorted(result.user_segments.items()):
        external_user_id = f"fitabase_{source_user_id}"
        existing_user = db.scalar(select(User).where(User.external_user_id == external_user_id))
        user = existing_user or create_user(
            db=db,
            payload=UserCreateRequest(
                external_user_id=external_user_id,
                name=f"Fitabase {source_user_id}",
                timezone=timezone,
            ),
        )
        if existing_user is None:
            inserted_users += 1

        inserted, skipped = _persist_imported_segments(
            db=db,
            user_id=user.id,
            source_type="fitabase_merged",
            segments=segments,
        )
        inserted_segments += inserted
        skipped_existing += skipped
        affected_user_ids.append(user.id)
        affected_external_ids.append(user.external_user_id)

    return FitbitImportResponse(
        mode="fitabase_merged",
        affected_user_ids=affected_user_ids,
        affected_external_user_ids=affected_external_ids,
        discovered_sources=result.discovered_sources,
        processed_sources=result.processed_sources,
        skipped_sources=result.skipped_sources,
        generated_segments=sum(len(items) for items in result.user_segments.values()),
        inserted_users=inserted_users,
        inserted_segments=inserted_segments,
        skipped_existing=skipped_existing,
        metrics_detected=result.metrics_detected,
        warnings=result.warnings,
    )


def _persist_imported_segments(*, db: Session, user_id: str, source_type: str, segments) -> tuple[int, int]:
    existing_keys = _load_existing_keys(db=db, user_id=user_id, source_type=source_type)
    inserted = 0
    skipped_existing = 0
    rows_to_insert: list[dict] = []

    for segment in segments:
        key = _segment_identity(segment.segment_start, source_type)
        if key in existing_keys:
            skipped_existing += 1
            continue

        rows_to_insert.append(
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "segment_start": segment.segment_start,
                "segment_end": segment.segment_end,
                "granularity": "1h",
                "source_type": source_type,
                "raw_payload_json": segment.raw_payload,
            }
        )
        existing_keys.add(key)
        inserted += 1

    for batch_start in range(0, len(rows_to_insert), 1000):
        batch = rows_to_insert[batch_start : batch_start + 1000]
        if batch:
            db.execute(insert(RawSegment), batch)

    db.commit()
    return inserted, skipped_existing


def _load_existing_keys(*, db: Session, user_id: str, source_type: str) -> set[str]:
    rows = db.execute(
        select(RawSegment.segment_start)
        .where(RawSegment.user_id == user_id)
        .where(RawSegment.source_type == source_type)
        .where(RawSegment.granularity == "1h")
    ).all()
    return {_segment_identity(row[0], source_type) for row in rows}


def _segment_identity(segment_start, source_type: str) -> str:
    normalized = segment_start
    if getattr(normalized, "tzinfo", None) is not None:
        normalized = normalized.replace(tzinfo=None)
    normalized = normalized.replace(minute=0, second=0, microsecond=0)
    return f"{source_type}:{normalized.isoformat()}"
