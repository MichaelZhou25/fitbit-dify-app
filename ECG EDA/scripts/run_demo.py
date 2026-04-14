from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from anxiety_monitor.pipeline import AnxietyRiskPipeline
from anxiety_monitor.packets import RawSignalWindow


def synthetic_ecg(fs: int, duration_s: int, hr_bpm: float, noise: float = 0.02) -> np.ndarray:
    n = fs * duration_s
    t = np.arange(n) / fs
    rr = 60.0 / hr_bpm
    peaks = np.arange(0.5, duration_s, rr)
    values = 0.02 * np.sin(2 * np.pi * 1.3 * t)
    for peak in peaks:
        values += np.exp(-0.5 * ((t - peak) / 0.015) ** 2) * 1.0
    values += noise * np.random.default_rng(42).normal(size=n)
    return values


def synthetic_eda(fs: int, duration_s: int, base: float, responses: int) -> np.ndarray:
    n = fs * duration_s
    t = np.arange(n) / fs
    values = np.full(n, base, dtype=float)
    trigger_times = np.linspace(5, duration_s - 5, responses) if responses else np.array([])
    for trigger in trigger_times:
        values += 0.35 * np.exp(-(t - trigger).clip(min=0) / 2.0) * (t >= trigger)
    values += 0.03 * np.sin(2 * np.pi * 0.03 * t)
    return values


def synthetic_temperature(fs: int, duration_s: int, baseline: float, slope: float) -> np.ndarray:
    n = fs * duration_s
    t = np.arange(n) / fs
    return baseline + slope * t + 0.02 * np.sin(2 * np.pi * 0.01 * t)


def synthetic_acc(fs: int, duration_s: int, motion: float) -> np.ndarray:
    n = fs * duration_s
    t = np.arange(n) / fs
    x = 0.02 * np.sin(2 * np.pi * 0.2 * t) + motion * np.sin(2 * np.pi * 1.7 * t)
    y = 0.02 * np.cos(2 * np.pi * 0.15 * t) + motion * np.sin(2 * np.pi * 1.1 * t)
    z = 1.0 + 0.02 * np.sin(2 * np.pi * 0.17 * t)
    return np.stack([x, y, z], axis=1)


def make_window(subject_id: str, hr: float, eda_base: float, eda_responses: int, temp_slope: float, motion: float) -> RawSignalWindow:
    duration_s = 60
    return RawSignalWindow(
        subject_id=subject_id,
        window_start_s=0.0,
        window_end_s=float(duration_s),
        ecg_hz=250,
        eda_hz=4,
        temperature_hz=4,
        acc_hz=32,
        ecg=synthetic_ecg(250, duration_s, hr_bpm=hr).tolist(),
        eda=synthetic_eda(4, duration_s, base=eda_base, responses=eda_responses).tolist(),
        temperature=synthetic_temperature(4, duration_s, baseline=36.5, slope=temp_slope).tolist(),
        acc=synthetic_acc(32, duration_s, motion=motion).tolist(),
    )


def main() -> None:
    pipeline = AnxietyRiskPipeline()
    windows = [
        ("low-demo", make_window("low-demo", hr=68, eda_base=1.2, eda_responses=1, temp_slope=0.0002, motion=0.01)),
        ("high-demo", make_window("high-demo", hr=108, eda_base=3.4, eda_responses=7, temp_slope=0.006, motion=0.03)),
    ]
    output_dir = Path("demo_output")
    output_dir.mkdir(exist_ok=True)
    for name, window in windows:
        result = pipeline.infer_request(window)
        output_path = output_dir / f"{name}.json"
        output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(f"\n=== {name} ===")
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        print(f"saved to {output_path}")


if __name__ == "__main__":
    main()

