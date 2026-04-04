from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import xgboost as xgb
except ImportError:  # pragma: no cover
    xgb = None

from app.core.config import get_settings


class Predictor:
    LABELS = ["fatigue_low", "fatigue_medium", "fatigue_high"]

    def __init__(self) -> None:
        self.settings = get_settings()
        self.booster = self._load_booster(self.settings.resolved_model_artifact_path)

    def _load_booster(self, artifact_path: Path) -> Any | None:
        if not xgb or not artifact_path.exists():
            return None
        booster = xgb.Booster()
        booster.load_model(str(artifact_path))
        return booster

    def predict(self, features: dict[str, Any], model_name: str, model_version: str) -> tuple[str, dict[str, float]]:
        if self.booster:
            probabilities = self._predict_with_xgboost(features)
        else:
            probabilities = self._heuristic_predict(features)

        top_label = max(probabilities, key=probabilities.get)
        return top_label, probabilities

    def _predict_with_xgboost(self, features: dict[str, Any]) -> dict[str, float]:
        feature_order = [
            "steps_sum",
            "calories_sum",
            "sleep_minutes",
            "sedentary_minutes",
            "active_minutes",
            "hr_mean",
            "hr_std",
            "hr_min",
            "hr_max",
            "hr_range",
        ]
        row = [[float(features.get(name, 0.0)) for name in feature_order]]
        matrix = xgb.DMatrix(row, feature_names=feature_order)
        prediction = self.booster.predict(matrix)[0]

        if isinstance(prediction, float):
            low = round(max(0.0, min(1.0, 1 - prediction)), 4)
            high = round(max(0.0, min(1.0, prediction)), 4)
            medium = round(max(0.0, 1 - low - high), 4)
            raw = [low, medium, high]
        else:
            raw = [round(float(value), 4) for value in prediction.tolist()]

        total = sum(raw) or 1.0
        normalized = [round(value / total, 4) for value in raw]
        return dict(zip(self.LABELS, normalized, strict=True))

    def _heuristic_predict(self, features: dict[str, Any]) -> dict[str, float]:
        fatigue_score = 0.0
        if features.get("sleep_minutes", 0) < 360:
            fatigue_score += 0.35
        if features.get("sedentary_minutes", 0) > 45:
            fatigue_score += 0.2
        if features.get("hr_std", 0) > 12:
            fatigue_score += 0.2
        if features.get("steps_sum", 0) < 500:
            fatigue_score += 0.25

        fatigue_high = min(0.9, max(0.05, round(fatigue_score, 4)))
        fatigue_low = min(0.9, max(0.05, round(1.0 - fatigue_high - 0.2, 4)))
        fatigue_medium = round(max(0.05, 1.0 - fatigue_low - fatigue_high), 4)

        raw = {
            "fatigue_low": fatigue_low,
            "fatigue_medium": fatigue_medium,
            "fatigue_high": fatigue_high,
        }
        total = sum(raw.values())
        normalized = {key: round(value / total, 4) for key, value in raw.items()}
        return json.loads(json.dumps(normalized))
