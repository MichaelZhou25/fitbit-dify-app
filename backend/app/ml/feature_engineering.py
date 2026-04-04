from __future__ import annotations

from statistics import mean, pstdev
from typing import Any


def _safe_mean(values: list[float]) -> float:
    return round(mean(values), 4) if values else 0.0


def _safe_std(values: list[float]) -> float:
    return round(pstdev(values), 4) if len(values) > 1 else 0.0


def build_feature_vector(raw_payload: dict[str, Any]) -> dict[str, Any]:
    heart_rate_series = [float(value) for value in raw_payload.get("heart_rate_series", [])]
    steps = float(raw_payload.get("steps", 0))
    calories = float(raw_payload.get("calories", 0))
    sleep_minutes = float(raw_payload.get("sleep_minutes", 0))
    sedentary_minutes = float(raw_payload.get("sedentary_minutes", 0))
    active_minutes = float(raw_payload.get("active_minutes", 0))

    return {
        "steps_sum": round(steps, 4),
        "calories_sum": round(calories, 4),
        "sleep_minutes": round(sleep_minutes, 4),
        "sedentary_minutes": round(sedentary_minutes, 4),
        "active_minutes": round(active_minutes, 4),
        "hr_mean": _safe_mean(heart_rate_series),
        "hr_std": _safe_std(heart_rate_series),
        "hr_min": round(min(heart_rate_series), 4) if heart_rate_series else 0.0,
        "hr_max": round(max(heart_rate_series), 4) if heart_rate_series else 0.0,
        "hr_range": round(max(heart_rate_series) - min(heart_rate_series), 4) if heart_rate_series else 0.0,
    }
