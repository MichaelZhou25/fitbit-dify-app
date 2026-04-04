from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SegmentIngestRequest(BaseModel):
    user_id: str
    segment_start: datetime
    segment_end: datetime
    granularity: str
    source_type: str
    raw_payload: dict[str, Any]


class SegmentIngestResponse(BaseModel):
    segment_id: str
    user_id: str
    status: str = "stored"


class FeatureExtractionResponse(BaseModel):
    feature_vector_id: str
    segment_id: str
    feature_version: str
    features: dict[str, Any]


class PredictionRequest(BaseModel):
    model_name: str = "xgboost-fatigue"
    model_version: str = "v1"


class PredictionResponse(BaseModel):
    prediction_id: str
    segment_id: str
    model_name: str
    model_version: str
    top_label: str
    probabilities: dict[str, float]


class AnalyzeRequest(BaseModel):
    user_query: str = "请解释这一段 Fitbit 数据，并给出个性化建议。"


class AnalyzeResponse(BaseModel):
    segment_id: str
    user_id: str
    model_output: dict[str, Any]
    dify_payload: dict[str, Any]
    llm_output: dict[str, Any]
    status: str


class SavedAnalysisResponse(BaseModel):
    dify_run_id: str
    workflow_run_id: str | None = None
    created_at: datetime
    segment_id: str
    user_id: str
    model_output: dict[str, Any]
    dify_payload: dict[str, Any]
    llm_output: dict[str, Any]
    status: str
    raw_dify_output: dict[str, Any] | None = None


class SegmentDetailResponse(BaseModel):
    id: str
    user_id: str
    segment_start: datetime
    segment_end: datetime
    granularity: str
    source_type: str
    raw_payload_json: dict[str, Any]
    feature_vectors: list[dict[str, Any]] = Field(default_factory=list)
    predictions: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
