from __future__ import annotations

from fastapi import FastAPI

from .packets import InferenceRequest, InferenceResponse
from .pipeline import AnxietyRiskPipeline

app = FastAPI(title="Anxiety Monitor V0", version="0.1.0")
pipeline = AnxietyRiskPipeline()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/infer/window", response_model=InferenceResponse)
def infer_window(request: InferenceRequest) -> InferenceResponse:
    return pipeline.infer_request(request.to_window(), questionnaire=request.questionnaire)
