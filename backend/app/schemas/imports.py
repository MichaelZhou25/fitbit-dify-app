from __future__ import annotations

from pydantic import BaseModel, Field


class FitbitImportResponse(BaseModel):
    mode: str
    affected_user_ids: list[str] = Field(default_factory=list)
    affected_external_user_ids: list[str] = Field(default_factory=list)
    discovered_sources: int
    processed_sources: int
    skipped_sources: int
    generated_segments: int
    inserted_users: int
    inserted_segments: int
    skipped_existing: int
    metrics_detected: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
