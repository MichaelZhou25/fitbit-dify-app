from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from .packets import FeaturePacket, RiskPacket

DEFAULT_FEATURE_ORDER = [
    "hr_mean",
    "hr_std",
    "median_hr",
    "rr_mean_ms",
    "rr_std_ms",
    "rr_min_ms",
    "rr_max_ms",
    "median_rr_ms",
    "rmssd_ms",
    "sdnn_ms",
    "sdsd_ms",
    "pnn20",
    "pnn50",
    "ecg_mean",
    "ecg_std",
    "ecg_skewness",
    "ecg_kurtosis",
    "ecg_fft_entropy",
    "ecg_mean_frequency",
    "ecg_zero_crossing_rate",
    "lf_power",
    "hf_power",
    "lf_hf_ratio",
    "eda_scl_mean",
    "eda_tonic_std",
    "eda_tonic_slope",
    "eda_scr_count",
    "eda_scr_amplitude_mean",
    "eda_scr_amplitude_std",
    "eda_scr_amplitude_max",
    "eda_scr_area",
    "eda_scr_density",
    "eda_phasic_mean",
    "eda_phasic_std",
    "eda_phasic_max",
    "eda_phasic_skewness",
    "eda_phasic_kurtosis",
    "eda_fft_entropy",
    "eda_mean_frequency",
    "eda_zero_crossing_rate",
    "eda_nld",
    "temp_mean",
    "temp_min",
    "temp_max",
    "temp_slope_per_min",
    "temp_delta_baseline",
    "temp_std",
    "acc_mean",
    "acc_std",
    "motion_ratio",
    "ecg_quality_score",
    "eda_quality_score",
    "temperature_quality_score",
    "acc_quality_score",
    "quality_overall",
]


class RiskEngine:
    def __init__(self, feature_order: list[str] | None = None) -> None:
        self.feature_order = feature_order or DEFAULT_FEATURE_ORDER.copy()
        self.label_encoder = LabelEncoder()
        self.pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        multi_class="auto",
                        random_state=42,
                    ),
                ),
            ]
        )
        self.is_fitted = False

    def _frame_from_packets(self, packets: list[FeaturePacket]) -> pd.DataFrame:
        return pd.DataFrame(
            [{name: float(packet.features.get(name, np.nan)) for name in self.feature_order} for packet in packets],
            columns=self.feature_order,
        )

    def fit(self, packets: list[FeaturePacket], labels: list[str]) -> "RiskEngine":
        frame = self._frame_from_packets(packets)
        y = self.label_encoder.fit_transform(labels)
        self.pipeline.fit(frame, y)
        self.is_fitted = True
        return self

    def save(self, path: str | Path) -> None:
        payload = {
            "feature_order": self.feature_order,
            "label_encoder": self.label_encoder,
            "pipeline": self.pipeline,
            "is_fitted": self.is_fitted,
        }
        with Path(path).open("wb") as f:
            pickle.dump(payload, f)

    @classmethod
    def load(cls, path: str | Path) -> "RiskEngine":
        with Path(path).open("rb") as f:
            payload = pickle.load(f)
        engine = cls(feature_order=payload["feature_order"])
        engine.label_encoder = payload["label_encoder"]
        engine.pipeline = payload["pipeline"]
        engine.is_fitted = payload["is_fitted"]
        return engine

    def _heuristic_score(self, feature_packet: FeaturePacket) -> tuple[float, list[str]]:
        f = feature_packet.features
        score = 0.0
        top_features: list[tuple[str, float]] = []

        def add(name: str, contribution: float) -> None:
            nonlocal score
            score += contribution
            top_features.append((name, abs(contribution)))

        hr = f.get("hr_mean", np.nan)
        rmssd = f.get("rmssd_ms", np.nan)
        sdnn = f.get("sdnn_ms", np.nan)
        scr_density = f.get("eda_scr_density", np.nan)
        scl = f.get("eda_scl_mean", np.nan)
        temp_delta = f.get("temp_delta_baseline", np.nan)
        motion = f.get("motion_ratio", np.nan)
        quality = feature_packet.quality.overall_quality

        if np.isfinite(hr):
            add("hr_mean", np.clip((hr - 72.0) / 45.0, 0.0, 1.2))
        if np.isfinite(rmssd):
            add("rmssd_ms", np.clip((45.0 - rmssd) / 45.0, 0.0, 1.0))
        if np.isfinite(sdnn):
            add("sdnn_ms", np.clip((55.0 - sdnn) / 55.0, 0.0, 1.0))
        if np.isfinite(scr_density):
            add("eda_scr_density", np.clip(scr_density / 6.0, 0.0, 1.0))
        if np.isfinite(scl):
            add("eda_scl_mean", np.clip((scl - 1.5) / 4.0, 0.0, 1.0))
        if np.isfinite(temp_delta):
            add("temp_delta_baseline", np.clip(temp_delta / 0.6, -0.5, 1.0))
        if np.isfinite(motion):
            add("motion_ratio", np.clip(motion / 2.0, 0.0, 0.5))

        score = np.clip(score / 5.5, 0.0, 1.0)
        score *= 0.4 + 0.6 * quality
        sorted_features = [name for name, _ in sorted(top_features, key=lambda item: item[1], reverse=True)[:4]]
        return float(score), sorted_features

    def predict(self, feature_packet: FeaturePacket) -> RiskPacket:
        if not feature_packet.quality.is_usable:
            return RiskPacket(
                risk_score=0.0,
                risk_level="abstain",
                uncertainty=1.0,
                quality_flag="low",
                model_name="quality-gate",
                top_features=["overall_quality"],
            )

        if not self.is_fitted:
            score, top_features = self._heuristic_score(feature_packet)
            level = "low" if score < 0.33 else "medium" if score < 0.66 else "high"
            return RiskPacket(
                risk_score=float(score),
                risk_level=level,
                uncertainty=float(max(0.05, 1.0 - abs(score - 0.5) * 1.7)),
                quality_flag="ok",
                model_name="heuristic-v0",
                top_features=top_features,
            )

        frame = self._frame_from_packets([feature_packet])
        probabilities = self.pipeline.predict_proba(frame)[0]
        pred_idx = int(np.argmax(probabilities))
        pred_label = str(self.label_encoder.inverse_transform([pred_idx])[0])
        pred_prob = float(probabilities[pred_idx])
        uncertainty = float(1.0 - pred_prob)

        scaler: StandardScaler = self.pipeline.named_steps["scaler"]
        imputer: SimpleImputer = self.pipeline.named_steps["imputer"]
        clf: LogisticRegression = self.pipeline.named_steps["clf"]
        x_imputed = imputer.transform(frame)
        x_scaled = scaler.transform(x_imputed)[0]
        coef = clf.coef_[pred_idx if clf.coef_.shape[0] > 1 else 0]
        contributions = x_scaled * coef
        order = np.argsort(np.abs(contributions))[::-1][:4]
        top_features = [self.feature_order[idx] for idx in order]

        return RiskPacket(
            risk_score=pred_prob,
            risk_level=pred_label,
            uncertainty=uncertainty,
            quality_flag="ok",
            model_name="logistic-regression-v0",
            top_features=top_features,
        )
