from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RawSignalWindow(BaseModel):
    subject_id: str
    window_start_s: float
    window_end_s: float
    ecg_hz: float
    eda_hz: float
    temperature_hz: float
    acc_hz: float
    ecg: list[float] = Field(default_factory=list)
    eda: list[float] = Field(default_factory=list)
    temperature: list[float] = Field(default_factory=list)
    acc: list[list[float]] | list[float] = Field(default_factory=list)
    label: str | None = None


class MultimodalRecording(BaseModel):
    subject_id: str
    ecg_hz: float
    eda_hz: float
    temperature_hz: float
    acc_hz: float
    ecg: list[float]
    eda: list[float]
    temperature: list[float]
    acc: list[list[float]] | list[float]
    label_samples: list[int] | list[str] | None = None
    label_hz: float | None = None
    questionnaire: dict[str, float] | None = None


class QualityPacket(BaseModel):
    ecg_quality: float
    eda_quality: float
    temperature_quality: float
    acc_quality: float
    overall_quality: float
    motion_artifact_ratio: float
    is_worn: bool
    is_usable: bool
    notes: list[str] = Field(default_factory=list)


class FeaturePacket(BaseModel):
    subject_id: str
    window_start_s: float
    window_end_s: float
    label: str | None = None
    quality: QualityPacket
    features: dict[str, float]


class RiskPacket(BaseModel):
    risk_score: float
    risk_level: str
    uncertainty: float
    quality_flag: str
    model_name: str
    top_features: list[str] = Field(default_factory=list)


class ConsultPacket(BaseModel):
    subject_id: str
    window_start_s: float
    window_end_s: float
    risk: RiskPacket
    quality: QualityPacket
    feature_snapshot: dict[str, float]
    recent_trend: dict[str, float] = Field(default_factory=dict)
    rule_triggers: list[str] = Field(default_factory=list)
    questionnaire: dict[str, float] | None = None


class LocalConsultReport(BaseModel):
    user_summary: str
    clinician_summary: str
    next_actions: list[str]
    evidence_sufficiency: str


class InferenceRequest(BaseModel):
    subject_id: str
    window_start_s: float = 0.0
    window_end_s: float = 60.0
    ecg_hz: float
    eda_hz: float
    temperature_hz: float
    acc_hz: float
    ecg: list[float]
    eda: list[float]
    temperature: list[float]
    acc: list[list[float]] | list[float]
    questionnaire: dict[str, float] | None = None

    def to_window(self) -> RawSignalWindow:
        return RawSignalWindow(
            subject_id=self.subject_id,
            window_start_s=self.window_start_s,
            window_end_s=self.window_end_s,
            ecg_hz=self.ecg_hz,
            eda_hz=self.eda_hz,
            temperature_hz=self.temperature_hz,
            acc_hz=self.acc_hz,
            ecg=self.ecg,
            eda=self.eda,
            temperature=self.temperature,
            acc=self.acc,
        )


class InferenceResponse(BaseModel):
    feature_packet: FeaturePacket
    risk_packet: RiskPacket
    consult_packet: ConsultPacket
    local_report: LocalConsultReport
    metadata: dict[str, Any] = Field(default_factory=dict)

