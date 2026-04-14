from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .dify import build_local_report
from .features import extract_feature_packet
from .model import RiskEngine
from .packets import (
    ConsultPacket,
    FeaturePacket,
    InferenceResponse,
    LocalConsultReport,
    MultimodalRecording,
    RawSignalWindow,
    RiskPacket,
)
from .preprocessing import segment_recording


@dataclass
class WindowInferenceBundle:
    feature_packet: FeaturePacket
    risk_packet: RiskPacket
    consult_packet: ConsultPacket
    local_report: LocalConsultReport


class AnxietyRiskPipeline:
    LABEL_MAP = {"1": "low", "2": "high", "3": "medium", "4": "low"}
    LABEL_ORDER = ["low", "medium", "high"]

    def __init__(self, window_sec: float = 60.0, step_sec: float = 30.0, risk_engine: RiskEngine | None = None) -> None:
        self.window_sec = window_sec
        self.step_sec = step_sec
        self.risk_engine = risk_engine or RiskEngine()

    def _temperature_baseline(self, recording: MultimodalRecording) -> float:
        arr = np.asarray(recording.temperature, dtype=float)
        take = max(int(recording.temperature_hz * 60), 1)
        return float(np.mean(arr[:take]))

    def extract_feature_packets(self, recording: MultimodalRecording) -> list[FeaturePacket]:
        windows = segment_recording(recording, window_sec=self.window_sec, step_sec=self.step_sec)
        baseline_temp = self._temperature_baseline(recording)
        return [extract_feature_packet(window, recording_temperature_baseline=baseline_temp) for window in windows]

    def _label_mapping(self, raw_label: str | None) -> str | None:
        if raw_label is None:
            return None
        return self.LABEL_MAP.get(str(raw_label))

    def prepare_training_set(self, recording: MultimodalRecording) -> tuple[list[FeaturePacket], list[str]]:
        packets = self.extract_feature_packets(recording)
        usable_packets: list[FeaturePacket] = []
        labels: list[str] = []
        for packet in packets:
            mapped = self._label_mapping(packet.label)
            if mapped is None or not packet.quality.is_usable:
                continue
            usable_packets.append(packet)
            labels.append(mapped)
        return usable_packets, labels

    def fit(self, packets: list[FeaturePacket], labels: list[str]) -> None:
        self.risk_engine.fit(packets, labels)

    def prepare_training_frame(self, recording: MultimodalRecording) -> pd.DataFrame:
        packets, labels = self.prepare_training_set(recording)
        rows = []
        for packet, label_name in zip(packets, labels):
            raw_label: str | int | None = packet.label
            if raw_label is not None and str(raw_label).isdigit():
                raw_label = int(str(raw_label))
            rows.append(
                {
                    "subject_id": packet.subject_id,
                    "window_start_s": packet.window_start_s,
                    "window_end_s": packet.window_end_s,
                    "label": raw_label,
                    "label_name": label_name,
                    "overall_quality": packet.quality.overall_quality,
                    "is_usable": packet.quality.is_usable,
                    **packet.features,
                }
            )
        return pd.DataFrame(rows)

    def _rule_triggers(self, feature_packet: FeaturePacket, risk_packet: RiskPacket) -> list[str]:
        features = feature_packet.features
        triggers: list[str] = []
        if features.get("hr_mean", 0.0) > 95.0:
            triggers.append("elevated_hr")
        if features.get("rmssd_ms", 999.0) < 20.0:
            triggers.append("low_hrv")
        if features.get("eda_scr_density", 0.0) > 5.0:
            triggers.append("high_eda_reactivity")
        if features.get("temp_delta_baseline", 0.0) > 0.3:
            triggers.append("temperature_above_baseline")
        if risk_packet.quality_flag == "low":
            triggers.append("low_quality")
        return triggers

    def _trend_from_history(self, risk_history: list[RiskPacket]) -> dict[str, float]:
        if len(risk_history) < 2:
            return {}
        current = risk_history[-1]
        previous = risk_history[-2]
        return {
            "risk_score_delta": float(current.risk_score - previous.risk_score),
            "uncertainty_delta": float(current.uncertainty - previous.uncertainty),
        }

    def infer_window(
        self,
        raw_window: RawSignalWindow,
        questionnaire: dict[str, float] | None = None,
        recent_risk_history: list[RiskPacket] | None = None,
        temperature_baseline: float | None = None,
    ) -> WindowInferenceBundle:
        feature_packet = extract_feature_packet(raw_window, recording_temperature_baseline=temperature_baseline)
        risk_packet = self.risk_engine.predict(feature_packet)
        consult_packet = ConsultPacket(
            subject_id=raw_window.subject_id,
            window_start_s=raw_window.window_start_s,
            window_end_s=raw_window.window_end_s,
            risk=risk_packet,
            quality=feature_packet.quality,
            feature_snapshot=feature_packet.features,
            recent_trend=self._trend_from_history(recent_risk_history or []),
            rule_triggers=self._rule_triggers(feature_packet, risk_packet),
            questionnaire=questionnaire,
        )
        return WindowInferenceBundle(
            feature_packet=feature_packet,
            risk_packet=risk_packet,
            consult_packet=consult_packet,
            local_report=build_local_report(consult_packet),
        )

    def infer_recording(self, recording: MultimodalRecording) -> list[WindowInferenceBundle]:
        windows = segment_recording(recording, window_sec=self.window_sec, step_sec=self.step_sec)
        baseline_temp = self._temperature_baseline(recording)
        risk_history: list[RiskPacket] = []
        bundles: list[WindowInferenceBundle] = []
        for window in windows:
            bundle = self.infer_window(
                raw_window=window,
                questionnaire=recording.questionnaire,
                recent_risk_history=risk_history,
                temperature_baseline=baseline_temp,
            )
            bundles.append(bundle)
            risk_history.append(bundle.risk_packet)
        return bundles

    def infer_request(self, raw_window: RawSignalWindow, questionnaire: dict[str, float] | None = None) -> InferenceResponse:
        bundle = self.infer_window(raw_window=raw_window, questionnaire=questionnaire)
        return InferenceResponse(
            feature_packet=bundle.feature_packet,
            risk_packet=bundle.risk_packet,
            consult_packet=bundle.consult_packet,
            local_report=bundle.local_report,
            metadata={
                "window_duration_s": raw_window.window_end_s - raw_window.window_start_s,
                "pipeline_window_s": self.window_sec,
                "pipeline_step_s": self.step_sec,
            },
        )

    @staticmethod
    def packets_to_frame(packets: list[FeaturePacket]) -> pd.DataFrame:
        rows = []
        for packet in packets:
            rows.append(
                {
                    "subject_id": packet.subject_id,
                    "window_start_s": packet.window_start_s,
                    "window_end_s": packet.window_end_s,
                    "label": packet.label,
                    "overall_quality": packet.quality.overall_quality,
                    "is_usable": packet.quality.is_usable,
                    **packet.features,
                }
            )
        return pd.DataFrame(rows)
