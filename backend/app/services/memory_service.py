from __future__ import annotations

from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feature_vector import FeatureVector
from app.models.memory_snapshot import MemorySnapshot
from app.models.model_prediction import ModelPrediction
from app.models.raw_segment import RawSegment
from app.models.user import User
from app.schemas.user import TimelineItem, TimelineResponse


def build_rolling_memory_summary(db: Session, user_id: str, limit: int = 7) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    segments = list(
        db.scalars(
            select(RawSegment)
            .where(RawSegment.user_id == user_id)
            .order_by(RawSegment.segment_start.desc())
            .limit(limit)
        )
    )

    if not segments:
        return {"message": "No historical segments yet."}

    steps_values = [segment.raw_payload_json.get("steps", 0) for segment in segments]
    sleep_values = [segment.raw_payload_json.get("sleep_minutes", 0) for segment in segments]
    hr_values = []
    for segment in segments:
        hr_series = segment.raw_payload_json.get("heart_rate_series", [])
        if hr_series:
            hr_values.extend(hr_series)

    summary = {
        "window_type": f"last_{len(segments)}_segments",
        "segment_count": len(segments),
        "avg_steps": round(mean(steps_values), 2),
        "avg_sleep_minutes": round(mean(sleep_values), 2),
        "avg_heart_rate": round(mean(hr_values), 2) if hr_values else None,
    }

    latest_segment = segments[0]
    snapshot = MemorySnapshot(
        user_id=user_id,
        window_type=summary["window_type"],
        window_start=segments[-1].segment_start,
        window_end=latest_segment.segment_end,
        summary_json=summary,
    )
    db.add(snapshot)
    db.commit()
    return summary


def build_user_timeline(db: Session, user_id: str, limit: int = 20) -> TimelineResponse:
    user = db.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    segments = list(
        db.scalars(
            select(RawSegment)
            .where(RawSegment.user_id == user_id)
            .order_by(RawSegment.segment_start.desc())
            .limit(limit)
        )
    )

    items: list[TimelineItem] = []
    for segment in segments:
        prediction = db.scalar(
            select(ModelPrediction)
            .join(FeatureVector, FeatureVector.id == ModelPrediction.feature_vector_id)
            .where(FeatureVector.segment_id == segment.id)
            .order_by(ModelPrediction.created_at.desc())
        )
        items.append(
            TimelineItem(
                segment_id=segment.id,
                segment_start=segment.segment_start,
                segment_end=segment.segment_end,
                granularity=segment.granularity,
                top_label=prediction.top_label if prediction else None,
                probabilities=prediction.probabilities_json if prediction else None,
            )
        )
    return TimelineResponse(user_id=user_id, items=items)
