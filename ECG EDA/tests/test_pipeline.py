from __future__ import annotations

import unittest

import numpy as np

from anxiety_monitor.pipeline import AnxietyRiskPipeline
from anxiety_monitor.packets import RawSignalWindow


def synthetic_ecg(fs: int, duration_s: int, hr_bpm: float) -> np.ndarray:
    n = fs * duration_s
    t = np.arange(n) / fs
    rr = 60.0 / hr_bpm
    peaks = np.arange(0.5, duration_s, rr)
    values = 0.02 * np.sin(2 * np.pi * 1.0 * t)
    for peak in peaks:
        values += np.exp(-0.5 * ((t - peak) / 0.015) ** 2)
    return values


def synthetic_eda(fs: int, duration_s: int, base: float, responses: int) -> np.ndarray:
    n = fs * duration_s
    t = np.arange(n) / fs
    values = np.full(n, base, dtype=float)
    for trigger in np.linspace(5, duration_s - 5, responses):
        values += 0.25 * np.exp(-(t - trigger).clip(min=0) / 2.0) * (t >= trigger)
    return values


def synthetic_temperature(fs: int, duration_s: int, base: float, slope: float) -> np.ndarray:
    n = fs * duration_s
    t = np.arange(n) / fs
    return base + slope * t


def synthetic_acc(fs: int, duration_s: int, motion: float) -> np.ndarray:
    n = fs * duration_s
    t = np.arange(n) / fs
    x = motion * np.sin(2 * np.pi * 1.2 * t)
    y = motion * np.cos(2 * np.pi * 1.4 * t)
    z = 1.0 + 0.01 * np.sin(2 * np.pi * 0.1 * t)
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
        temperature=synthetic_temperature(4, duration_s, base=36.5, slope=temp_slope).tolist(),
        acc=synthetic_acc(32, duration_s, motion=motion).tolist(),
    )


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = AnxietyRiskPipeline()

    def test_extracts_core_features(self) -> None:
        window = make_window("test-low", hr=70, eda_base=1.2, eda_responses=1, temp_slope=0.0002, motion=0.01)
        result = self.pipeline.infer_request(window)
        self.assertIn("hr_mean", result.feature_packet.features)
        self.assertIn("eda_scl_mean", result.feature_packet.features)
        self.assertIn("temp_delta_baseline", result.feature_packet.features)
        self.assertTrue(result.feature_packet.quality.is_usable)

    def test_heuristic_risk_orders_low_and_high_windows(self) -> None:
        low_window = make_window("low", hr=68, eda_base=1.1, eda_responses=1, temp_slope=0.0001, motion=0.01)
        high_window = make_window("high", hr=110, eda_base=3.5, eda_responses=7, temp_slope=0.006, motion=0.03)
        low_result = self.pipeline.infer_request(low_window)
        high_result = self.pipeline.infer_request(high_window)
        self.assertLess(low_result.risk_packet.risk_score, high_result.risk_packet.risk_score)

    def test_low_quality_window_abstains(self) -> None:
        duration_s = 60
        bad_window = RawSignalWindow(
            subject_id="bad",
            window_start_s=0.0,
            window_end_s=float(duration_s),
            ecg_hz=250,
            eda_hz=4,
            temperature_hz=4,
            acc_hz=32,
            ecg=[0.0] * (250 * duration_s),
            eda=[0.0] * (4 * duration_s),
            temperature=[0.0] * (4 * duration_s),
            acc=[[0.0, 0.0, 0.0]] * (32 * duration_s),
        )
        result = self.pipeline.infer_request(bad_window)
        self.assertEqual(result.risk_packet.risk_level, "abstain")
        self.assertFalse(result.feature_packet.quality.is_usable)


if __name__ == "__main__":
    unittest.main()
