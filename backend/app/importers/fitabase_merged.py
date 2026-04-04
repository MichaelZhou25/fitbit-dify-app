from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from zoneinfo import ZoneInfo

from app.importers.fitbit_export import ImportedSegment


@dataclass(slots=True)
class FitabaseImportResult:
    user_segments: dict[str, list[ImportedSegment]]
    discovered_sources: int
    processed_sources: int
    skipped_sources: int
    metrics_detected: dict[str, int]
    warnings: list[str]


@dataclass(slots=True)
class _HourlyBucket:
    steps: float = 0.0
    calories: float = 0.0
    heart_rate_series: list[float] = field(default_factory=list)
    sleep_minutes: float = 0.0
    active_minutes: float = 0.0
    sedentary_minutes: float = 0.0
    inferred_hourly_intensity: float = 0.0
    explicit_active_minutes: bool = False
    explicit_sedentary_minutes: bool = False


def load_fitabase_merged_export(
    export_path: str | Path,
    timezone: str,
    *,
    steps_per_active_minute: float = 50.0,
) -> FitabaseImportResult:
    parser = _FitabaseMergedParser(
        timezone=timezone,
        steps_per_active_minute=steps_per_active_minute,
    )
    return parser.parse(Path(export_path))


class _FitabaseMergedParser:
    def __init__(self, *, timezone: str, steps_per_active_minute: float) -> None:
        self.zone = ZoneInfo(timezone)
        self.steps_per_active_minute = max(1.0, steps_per_active_minute)
        self._user_buckets: dict[str, dict[datetime, _HourlyBucket]] = defaultdict(lambda: defaultdict(_HourlyBucket))
        self._warnings: list[str] = []
        self._metrics_detected: Counter[str] = Counter()
        self._discovered_sources = 0
        self._processed_sources = 0
        self._skipped_sources = 0

    def parse(self, export_path: Path) -> FitabaseImportResult:
        if not export_path.exists():
            raise FileNotFoundError(f"Fitabase export path not found: {export_path}")

        for path in sorted(export_path.rglob("*.csv")):
            metric = _detect_fitabase_metric(path.name)
            if not metric:
                continue

            self._discovered_sources += 1
            processed = self._parse_csv(path=path, metric=metric)
            if processed:
                self._processed_sources += 1
                self._metrics_detected[metric] += 1
            else:
                self._skipped_sources += 1

        user_segments = self._build_segments()
        return FitabaseImportResult(
            user_segments=user_segments,
            discovered_sources=self._discovered_sources,
            processed_sources=self._processed_sources,
            skipped_sources=self._skipped_sources,
            metrics_detected=dict(sorted(self._metrics_detected.items())),
            warnings=self._warnings,
        )

    def _parse_csv(self, *, path: Path, metric: str) -> bool:
        processed_rows = 0
        with path.open(newline="", encoding="utf-8-sig") as file_obj:
            reader = csv.DictReader(file_obj)
            if not reader.fieldnames:
                return False

            for row in reader:
                source_user_id = str(row.get("Id", "")).strip()
                if not source_user_id:
                    continue

                if metric == "steps":
                    timestamp = _parse_datetime(row.get("ActivityHour"), self.zone)
                    value = _to_float(row.get("StepTotal"))
                    if timestamp and value is not None:
                        self._bucket_for(source_user_id, timestamp).steps += value
                        processed_rows += 1
                    continue

                if metric == "calories":
                    timestamp = _parse_datetime(row.get("ActivityHour"), self.zone)
                    value = _to_float(row.get("Calories"))
                    if timestamp and value is not None:
                        self._bucket_for(source_user_id, timestamp).calories += value
                        processed_rows += 1
                    continue

                if metric == "hourly_intensity":
                    timestamp = _parse_datetime(row.get("ActivityHour"), self.zone)
                    value = _to_float(row.get("TotalIntensity"))
                    if timestamp and value is not None:
                        self._bucket_for(source_user_id, timestamp).inferred_hourly_intensity += value
                        processed_rows += 1
                    continue

                if metric == "minute_intensity":
                    timestamp = _parse_datetime(row.get("ActivityMinute"), self.zone)
                    value = _to_float(row.get("Intensity"))
                    if timestamp and value is not None:
                        bucket = self._bucket_for(source_user_id, timestamp)
                        if value > 0:
                            bucket.active_minutes += 1
                        else:
                            bucket.sedentary_minutes += 1
                        bucket.explicit_active_minutes = True
                        bucket.explicit_sedentary_minutes = True
                        processed_rows += 1
                    continue

                if metric == "heart_rate":
                    timestamp = _parse_datetime(row.get("Time"), self.zone)
                    value = _to_float(row.get("Value"))
                    if timestamp and value is not None and value > 0:
                        self._bucket_for(source_user_id, timestamp).heart_rate_series.append(round(value, 4))
                        processed_rows += 1
                    continue

                if metric == "sleep":
                    timestamp = _parse_datetime(row.get("date"), self.zone)
                    value = _to_float(row.get("value"))
                    if timestamp and value is not None and value > 0:
                        self._bucket_for(source_user_id, timestamp).sleep_minutes += 1
                        processed_rows += 1

        if processed_rows == 0:
            self._warnings.append(f"{path}: no usable rows for metric {metric}")
        return processed_rows > 0

    def _bucket_for(self, source_user_id: str, timestamp: datetime) -> _HourlyBucket:
        bucket_start = timestamp.replace(minute=0, second=0, microsecond=0)
        return self._user_buckets[source_user_id][bucket_start]

    def _build_segments(self) -> dict[str, list[ImportedSegment]]:
        result: dict[str, list[ImportedSegment]] = {}

        for source_user_id, buckets in self._user_buckets.items():
            segments: list[ImportedSegment] = []
            for segment_start in sorted(buckets):
                bucket = buckets[segment_start]
                if not self._bucket_has_signal(bucket):
                    continue

                sleep_minutes = min(60.0, round(bucket.sleep_minutes, 4))
                active_minutes = bucket.active_minutes
                sedentary_minutes = bucket.sedentary_minutes

                if not bucket.explicit_active_minutes and bucket.inferred_hourly_intensity > 0:
                    active_minutes = max(active_minutes, min(60.0, round(bucket.inferred_hourly_intensity, 4)))

                if active_minutes == 0 and bucket.steps > 0:
                    active_minutes = min(60.0, round(bucket.steps / self.steps_per_active_minute, 4))

                if not bucket.explicit_sedentary_minutes:
                    sedentary_minutes = max(sedentary_minutes, max(0.0, 60.0 - sleep_minutes - active_minutes))
                else:
                    sedentary_minutes = max(0.0, sedentary_minutes - sleep_minutes)

                segments.append(
                    ImportedSegment(
                        segment_start=segment_start,
                        segment_end=segment_start + timedelta(hours=1),
                        raw_payload={
                            "steps": round(bucket.steps, 4),
                            "calories": round(bucket.calories, 4),
                            "heart_rate_series": [round(value, 4) for value in bucket.heart_rate_series],
                            "sleep_minutes": round(sleep_minutes, 4),
                            "sedentary_minutes": round(min(60.0, sedentary_minutes), 4),
                            "active_minutes": round(min(60.0, active_minutes), 4),
                        },
                    )
                )

            if segments:
                result[source_user_id] = segments

        return result

    def _bucket_has_signal(self, bucket: _HourlyBucket) -> bool:
        return any(
            (
                bucket.steps,
                bucket.calories,
                bucket.heart_rate_series,
                bucket.sleep_minutes,
                bucket.active_minutes,
                bucket.sedentary_minutes,
                bucket.inferred_hourly_intensity,
            )
        )


def _detect_fitabase_metric(filename: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", "_", filename.lower()).strip("_")
    mapping = {
        "hourlysteps_merged_csv": "steps",
        "hourlycalories_merged_csv": "calories",
        "hourlyintensities_merged_csv": "hourly_intensity",
        "minuteintensitiesnarrow_merged_csv": "minute_intensity",
        "heartrate_seconds_merged_csv": "heart_rate",
        "minutesleep_merged_csv": "sleep",
    }
    return mapping.get(normalized)


def _parse_datetime(value: str | None, zone: ZoneInfo) -> datetime | None:
    if not value:
        return None

    text = str(value).strip()
    formats = (
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %I:%M:%S.%f %p",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=zone)
    return None


def _to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None
