from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.models.user_profile import UserProfile

settings = get_settings()


def build_analysis_payload(
    user_id: str,
    segment_id: str,
    profile: UserProfile,
    raw_payload: dict[str, Any],
    model_output: dict[str, Any],
    rolling_memory_summary: dict[str, Any],
    user_query: str,
) -> dict[str, Any]:
    feature_summary = _build_feature_summary(raw_payload)
    return {
        "inputs": {
            "user_id": user_id,
            "segment_id": segment_id,
            "profile_prompt_prefix": profile.system_prompt_prefix,
            "profile_json": json.dumps(profile.profile_json, ensure_ascii=False),
            "goals_json": json.dumps(profile.goals_json, ensure_ascii=False),
            "thresholds_json": json.dumps(profile.thresholds_json, ensure_ascii=False),
            "baseline_stats_json": json.dumps(profile.baseline_stats_json, ensure_ascii=False),
            "rolling_memory_summary": json.dumps(rolling_memory_summary, ensure_ascii=False),
            "feature_summary": feature_summary,
            "probability_json": json.dumps(model_output["probabilities"], ensure_ascii=False),
            "top_label": model_output["top_label"],
            "user_query": user_query,
        },
        "response_mode": settings.dify_response_mode,
        "user": user_id,
    }


def _build_feature_summary(raw_payload: dict[str, Any]) -> str:
    parts = [
        f"steps={raw_payload.get('steps', 0)}",
        f"calories={raw_payload.get('calories', 0)}",
        f"sleep_minutes={raw_payload.get('sleep_minutes', 0)}",
        f"sedentary_minutes={raw_payload.get('sedentary_minutes', 0)}",
        f"active_minutes={raw_payload.get('active_minutes', 0)}",
    ]
    hr_series = raw_payload.get("heart_rate_series", [])
    if hr_series:
        parts.append(f"heart_rate_series_length={len(hr_series)}")
        parts.append(f"heart_rate_mean={round(sum(hr_series) / len(hr_series), 2)}")
        parts.append(f"heart_rate_min={round(min(hr_series), 2)}")
        parts.append(f"heart_rate_max={round(max(hr_series), 2)}")
    return ", ".join(parts)


def build_local_fallback_output(
    raw_payload: dict[str, Any],
    model_output: dict[str, Any],
    memory_summary: dict[str, Any],
    *,
    status: str = "skipped",
    status_message: str | None = None,
) -> dict[str, Any]:
    fallback_reason = {
        "skipped": "当前还没有配置 Dify，系统返回本地回退说明。",
        "error": "Dify 请求失败，系统返回本地回退说明。",
    }.get(status, "系统返回本地回退说明。")

    if status_message:
        fallback_reason = f"{fallback_reason} 详情: {status_message}"

    return {
        "summary": f"当前片段的主要分类结果为 {model_output['top_label']}。",
        "explanation": (
            f"{fallback_reason}"
            f" steps={raw_payload.get('steps', 0)},"
            f" sleep_minutes={raw_payload.get('sleep_minutes', 0)},"
            f" avg_steps_recent={memory_summary.get('avg_steps')}."
        ),
        "personalized_advice": [
            "先补充 user_profiles 里的长期目标、阈值和基线信息。",
            "Dify 工作流上线后，再把解释语气和输出格式做个性化。",
        ],
        "probabilities": model_output["probabilities"],
        "confidence_note": "这是本地回退结果，不代表最终的 Dify 解释效果。",
    }
