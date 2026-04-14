from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from scipy import signal

from .packets import MultimodalRecording, RawSignalWindow


def ensure_1d(values: Iterable[float]) -> np.ndarray:
    return np.asarray(list(values), dtype=float).reshape(-1)


def ensure_2d(values: Iterable[Iterable[float]] | Iterable[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 1:
        return arr.reshape(-1, 1)
    return arr


def interpolate_nan(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float).copy()
    if arr.size == 0:
        return arr
    mask = np.isfinite(arr)
    if mask.all():
        return arr
    if not mask.any():
        return np.zeros_like(arr)
    x = np.arange(arr.size)
    arr[~mask] = np.interp(x[~mask], x[mask], arr[mask])
    return arr


def _safe_filtfilt(b: np.ndarray, a: np.ndarray, values: np.ndarray) -> np.ndarray:
    if values.size < max(len(a), len(b)) * 3:
        return values
    return signal.filtfilt(b, a, values)


def bandpass_filter(values: np.ndarray, fs: float, low_hz: float, high_hz: float, order: int = 4) -> np.ndarray:
    if fs <= 0 or values.size == 0:
        return values
    nyquist = fs / 2.0
    low = max(low_hz / nyquist, 1e-4)
    high = min(high_hz / nyquist, 0.999)
    if low >= high:
        return values
    b, a = signal.butter(order, [low, high], btype="bandpass")
    return _safe_filtfilt(b, a, values)


def lowpass_filter(values: np.ndarray, fs: float, cutoff_hz: float, order: int = 4) -> np.ndarray:
    if fs <= 0 or values.size == 0:
        return values
    nyquist = fs / 2.0
    cutoff = min(cutoff_hz / nyquist, 0.999)
    if cutoff <= 0:
        return values
    b, a = signal.butter(order, cutoff, btype="lowpass")
    return _safe_filtfilt(b, a, values)


def notch_filter(values: np.ndarray, fs: float, notch_hz: float = 50.0, q: float = 30.0) -> np.ndarray:
    if fs <= notch_hz * 2 or values.size == 0:
        return values
    b, a = signal.iirnotch(notch_hz, q, fs)
    return _safe_filtfilt(b, a, values)


def moving_average(values: np.ndarray, window_samples: int) -> np.ndarray:
    if values.size == 0:
        return values
    window_samples = max(int(window_samples), 1)
    pad_left = window_samples // 2
    pad_right = window_samples - 1 - pad_left
    padded = np.pad(values, (pad_left, pad_right), mode="edge")
    kernel = np.ones(window_samples, dtype=float) / window_samples
    return np.convolve(padded, kernel, mode="valid")


def preprocess_ecg(ecg: Iterable[float], fs: float) -> np.ndarray:
    arr = interpolate_nan(ensure_1d(ecg))
    arr = signal.detrend(arr, type="constant")
    arr = bandpass_filter(arr, fs, low_hz=0.5, high_hz=40.0)
    arr = notch_filter(arr, fs, notch_hz=50.0)
    return arr


def preprocess_eda(eda: Iterable[float], fs: float) -> np.ndarray:
    arr = interpolate_nan(ensure_1d(eda))
    return lowpass_filter(arr, fs, cutoff_hz=1.0)


def preprocess_temperature(values: Iterable[float], fs: float) -> np.ndarray:
    arr = interpolate_nan(ensure_1d(values))
    return moving_average(arr, max(int(fs * 5), 1))


def preprocess_acc(acc: Iterable[Iterable[float]] | Iterable[float]) -> np.ndarray:
    return interpolate_nan(ensure_2d(acc))


def acc_magnitude(acc: np.ndarray) -> np.ndarray:
    if acc.ndim == 1 or acc.shape[1] == 1:
        return acc.reshape(-1)
    return np.linalg.norm(acc, axis=1)


def slice_signal(values: np.ndarray, fs: float, start_s: float, end_s: float) -> np.ndarray:
    start = max(int(round(start_s * fs)), 0)
    end = max(int(round(end_s * fs)), start)
    return values[start:end]


def segment_recording(recording: MultimodalRecording, window_sec: float = 60.0, step_sec: float = 30.0) -> list[RawSignalWindow]:
    durations = [
        len(recording.ecg) / recording.ecg_hz,
        len(recording.eda) / recording.eda_hz,
        len(recording.temperature) / recording.temperature_hz,
        len(recording.acc) / recording.acc_hz,
    ]
    total_duration = float(min(durations))
    if total_duration < window_sec:
        return []

    windows: list[RawSignalWindow] = []
    start_s = 0.0
    label_arr = np.asarray(recording.label_samples) if recording.label_samples is not None else None
    label_hz = recording.label_hz or 0.0

    while start_s + window_sec <= total_duration + 1e-8:
        end_s = start_s + window_sec
        label = None
        if label_arr is not None and label_hz > 0:
            start_idx = int(start_s * label_hz)
            end_idx = int(end_s * label_hz)
            label_window = label_arr[start_idx:end_idx]
            if label_window.size:
                uniques, counts = np.unique(label_window, return_counts=True)
                label = str(uniques[np.argmax(counts)])

        windows.append(
            RawSignalWindow(
                subject_id=recording.subject_id,
                window_start_s=start_s,
                window_end_s=end_s,
                ecg_hz=recording.ecg_hz,
                eda_hz=recording.eda_hz,
                temperature_hz=recording.temperature_hz,
                acc_hz=recording.acc_hz,
                ecg=slice_signal(np.asarray(recording.ecg, dtype=float), recording.ecg_hz, start_s, end_s).tolist(),
                eda=slice_signal(np.asarray(recording.eda, dtype=float), recording.eda_hz, start_s, end_s).tolist(),
                temperature=slice_signal(
                    np.asarray(recording.temperature, dtype=float), recording.temperature_hz, start_s, end_s
                ).tolist(),
                acc=slice_signal(np.asarray(recording.acc, dtype=float), recording.acc_hz, start_s, end_s).tolist(),
                label=label,
            )
        )
        start_s += step_sec
    return windows
