from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dify.client import DifyClient, extract_workflow_outputs
from app.dify.prompt_builder import build_analysis_payload, build_local_fallback_output
from app.models.dify_run import DifyRun
from app.schemas.segment import AnalyzeRequest, AnalyzeResponse, PredictionRequest, SavedAnalysisResponse
from app.services.memory_service import build_rolling_memory_summary
from app.services.prediction_service import predict_for_segment
from app.services.segment_service import get_segment_or_404
from app.services.user_service import get_profile_or_404

dify_client = DifyClient()


def analyze_segment(db: Session, segment_id: str, payload: AnalyzeRequest) -> AnalyzeResponse:
    segment = get_segment_or_404(db=db, segment_id=segment_id)
    profile = get_profile_or_404(db=db, user_id=segment.user_id)
    prediction = predict_for_segment(db=db, segment_id=segment_id, payload=PredictionRequest())
    memory_summary = build_rolling_memory_summary(db=db, user_id=segment.user_id)

    dify_payload = build_analysis_payload(
        user_id=segment.user_id,
        segment_id=segment.id,
        profile=profile,
        raw_payload=segment.raw_payload_json,
        model_output={
            "top_label": prediction.top_label,
            "probabilities": prediction.probabilities,
        },
        rolling_memory_summary=memory_summary,
        user_query=payload.user_query,
    )

    dify_result, status, workflow_run_id = dify_client.run_workflow(dify_payload)
    if status == "sent":
        llm_output = extract_workflow_outputs(dify_result)
        stored_dify_output = dify_result
    else:
        llm_output = build_local_fallback_output(
            raw_payload=segment.raw_payload_json,
            model_output={
                "top_label": prediction.top_label,
                "probabilities": prediction.probabilities,
            },
            memory_summary=memory_summary,
            status=status,
            status_message=dify_result.get("message"),
        )
        stored_dify_output = {
            **dify_result,
            "fallback_output": llm_output,
        }

    dify_run = DifyRun(
        user_id=segment.user_id,
        segment_id=segment.id,
        workflow_run_id=workflow_run_id,
        dify_inputs_json=dify_payload,
        dify_outputs_json=stored_dify_output,
        status=status,
    )
    db.add(dify_run)
    db.commit()

    return AnalyzeResponse(
        segment_id=segment.id,
        user_id=segment.user_id,
        model_output={
            "top_label": prediction.top_label,
            "probabilities": prediction.probabilities,
        },
        dify_payload=dify_payload,
        llm_output=llm_output,
        status=status,
    )


def get_latest_analysis_for_segment(db: Session, segment_id: str) -> SavedAnalysisResponse | None:
    segment = get_segment_or_404(db=db, segment_id=segment_id)
    run = db.scalar(
        select(DifyRun)
        .where(DifyRun.segment_id == segment.id)
        .order_by(DifyRun.created_at.desc())
        .limit(1)
    )
    if not run:
        return None
    return build_saved_analysis_response(run)


def build_saved_analysis_response(run: DifyRun) -> SavedAnalysisResponse:
    dify_payload = run.dify_inputs_json or {}
    raw_output = run.dify_outputs_json or {}
    llm_output = raw_output.get("fallback_output")
    if not isinstance(llm_output, dict):
        llm_output = extract_workflow_outputs(raw_output)
    return SavedAnalysisResponse(
        dify_run_id=run.id,
        workflow_run_id=run.workflow_run_id,
        created_at=run.created_at,
        segment_id=run.segment_id,
        user_id=run.user_id,
        model_output=_model_output_from_dify_payload(dify_payload),
        dify_payload=dify_payload,
        llm_output=llm_output,
        status=run.status,
        raw_dify_output=run.dify_outputs_json,
    )


def _model_output_from_dify_payload(dify_payload: dict) -> dict:
    inputs = dify_payload.get("inputs")
    if not isinstance(inputs, dict):
        return {}

    probabilities: dict | list | str | None = inputs.get("probability_json")
    if isinstance(probabilities, str):
        try:
            probabilities = json.loads(probabilities)
        except json.JSONDecodeError:
            probabilities = {"raw": probabilities}

    return {
        "top_label": inputs.get("top_label"),
        "probabilities": probabilities or {},
    }
