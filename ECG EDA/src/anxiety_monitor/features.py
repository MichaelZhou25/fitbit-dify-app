from __future__ import annotations

import math

import numpy as np
from scipy import signal
from scipy.stats import kurtosis, skew

from .packets import FeaturePacket, QualityPacket, RawSignalWindow
from .preprocessing import (
    acc_magnitude,
    preprocess_acc,
    preprocess_ecg,
    preprocess_eda,
    preprocess_temperature,
)


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _nan_if_empty(values: np.ndarray, fn) -> float:
    if values.size == 0:
        return math.nan
    try:
        return float(fn(values))
    except Exception:
        return math.nan


def _zero_crossing_rate(values: np.ndarray) -> float:
    if values.size < 2:
        return math.nan
    signs = np.sign(values)
    signs[signs == 0] = 1
    return float(np.mean(signs[:-1] != signs[1:]))


def _spectral_summary(values: np.ndarray, fs: float) -> tuple[float, float]:
    if values.size < 4 or fs <= 0:
        return math.nan, math.nan
    freqs, psd = signal.welch(values, fs=fs, nperseg=min(len(values), 256))
    psd = np.asarray(psd, dtype=float)
    freqs = np.asarray(freqs, dtype=float)
    if psd.size == 0 or np.sum(psd) <= 0:
        return math.nan, math.nan
    p = psd / np.sum(psd)
    entropy = float(-np.sum(p * np.log2(p + 1e-12)))
    mean_frequency = float(np.sum(freqs * p))
    return entropy, mean_frequency


def _normalized_length_density(values: np.ndarray) -> float:
    if values.size < 2:
        return math.nan
    diff_sum = float(np.sum(np.abs(np.diff(values))))
    amp_range = float(np.max(values) - np.min(values))
    if amp_range <= 1e-12:
        return 0.0
    return diff_sum / (len(values) * amp_range)


def _band_power(freqs: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs < high)
    if not np.any(mask):
        return math.nan
    return float(np.trapezoid(psd[mask], freqs[mask]))


def _rr_frequency_features(rr_ms: np.ndarray) -> dict[str, float]:
    if rr_ms.size < 8:
        return {"lf_power": math.nan, "hf_power": math.nan, "lf_hf_ratio": math.nan}

    rr_s = rr_ms / 1000.0
    timestamps = np.cumsum(rr_s)
    timestamps -= timestamps[0]
    if timestamps[-1] <= 0:
        return {"lf_power": math.nan, "hf_power": math.nan, "lf_hf_ratio": math.nan}

    interp_fs = 4.0
    uniform_t = np.arange(0, timestamps[-1], 1.0 / interp_fs)
    if uniform_t.size < 8:
        return {"lf_power": math.nan, "hf_power": math.nan, "lf_hf_ratio": math.nan}

    rr_interp = np.interp(uniform_t, timestamps, rr_s)
    rr_interp = rr_interp - np.mean(rr_interp)
    freqs, psd = signal.welch(rr_interp, fs=interp_fs, nperseg=min(len(rr_interp), 256))
    lf = _band_power(freqs, psd, 0.04, 0.15)
    hf = _band_power(freqs, psd, 0.15, 0.4)
    ratio = float(lf / hf) if np.isfinite(lf) and np.isfinite(hf) and hf > 1e-12 else math.nan
    return {"lf_power": lf, "hf_power": hf, "lf_hf_ratio": ratio}


def _derive_ecg_quality(ecg: np.ndarray, peaks: np.ndarray, rr_ms: np.ndarray) -> tuple[float, list[str]]:
    notes: list[str] = []
    if ecg.size == 0:
        return 0.0, ["empty_ecg"]
    if peaks.size < 2:
        return 0.1, ["insufficient_r_peaks"]
    valid_ratio = float(rr_ms.size / max(peaks.size - 1, 1))
    amplitude_score = _clip01(np.std(ecg) / 0.15)
    rr_score = _clip01(valid_ratio)
    score = 0.55 * rr_score + 0.45 * amplitude_score
    if score < 0.4:
        notes.append("low_ecg_quality")
    return score, notes


def extract_ecg_features(ecg: np.ndarray, fs: float) -> tuple[dict[str, float], float, list[str]]:
    if ecg.size < max(int(fs * 5), 10):
        return {
            "hr_mean": math.nan,
            "hr_std": math.nan,
            "median_hr": math.nan,
            "rr_mean_ms": math.nan,
            "rr_std_ms": math.nan,
            "rr_min_ms": math.nan,
            "rr_max_ms": math.nan,
            "median_rr_ms": math.nan,
            "rmssd_ms": math.nan,
            "sdnn_ms": math.nan,
            "sdsd_ms": math.nan,
            "pnn20": math.nan,
            "pnn50": math.nan,
            "ecg_mean": math.nan,
            "ecg_std": math.nan,
            "ecg_skewness": math.nan,
            "ecg_kurtosis": math.nan,
            "ecg_fft_entropy": math.nan,
            "ecg_mean_frequency": math.nan,
            "ecg_zero_crossing_rate": math.nan,
            "lf_power": math.nan,
            "hf_power": math.nan,
            "lf_hf_ratio": math.nan,
        }, 0.0, ["ecg_too_short"]

    distance = max(int(fs * 0.33), 1)
    prominence = max(np.std(ecg) * 0.4, 0.05)
    peaks, _ = signal.find_peaks(ecg, distance=distance, prominence=prominence)
    rr_ms = np.diff(peaks) / fs * 1000.0
    rr_ms = rr_ms[(rr_ms >= 300.0) & (rr_ms <= 2000.0)]
    quality, notes = _derive_ecg_quality(ecg, peaks, rr_ms)

    if rr_ms.size < 2:
        notes.append("insufficient_valid_rr")
        return {
            "hr_mean": math.nan,
            "hr_std": math.nan,
            "median_hr": math.nan,
            "rr_mean_ms": math.nan,
            "rr_std_ms": math.nan,
            "rr_min_ms": math.nan,
            "rr_max_ms": math.nan,
            "median_rr_ms": math.nan,
            "rmssd_ms": math.nan,
            "sdnn_ms": math.nan,
            "sdsd_ms": math.nan,
            "pnn20": math.nan,
            "pnn50": math.nan,
            "ecg_mean": _nan_if_empty(ecg, np.mean),
            "ecg_std": _nan_if_empty(ecg, np.std),
            "ecg_skewness": _nan_if_empty(ecg, skew),
            "ecg_kurtosis": _nan_if_empty(ecg, kurtosis),
            "ecg_fft_entropy": math.nan,
            "ecg_mean_frequency": math.nan,
            "ecg_zero_crossing_rate": _zero_crossing_rate(ecg),
            "lf_power": math.nan,
            "hf_power": math.nan,
            "lf_hf_ratio": math.nan,
        }, quality, notes

    rr_diff = np.diff(rr_ms)
    rmssd = float(np.sqrt(np.mean(np.square(rr_diff)))) if rr_diff.size else 0.0
    sdnn = float(np.std(rr_ms, ddof=1)) if rr_ms.size > 1 else 0.0
    sdsd = float(np.std(rr_diff, ddof=1)) if rr_diff.size > 1 else 0.0
    pnn20 = float(np.mean(np.abs(rr_diff) > 20.0)) if rr_diff.size else 0.0
    pnn50 = float(np.mean(np.abs(rr_diff) > 50.0)) if rr_diff.size else 0.0
    hr_series = 60000.0 / rr_ms
    hr_mean = float(np.mean(hr_series))
    fft_entropy, mean_frequency = _spectral_summary(ecg, fs)
    freq_features = _rr_frequency_features(rr_ms)
    return {
        "hr_mean": hr_mean,
        "hr_std": float(np.std(hr_series, ddof=1)) if hr_series.size > 1 else 0.0,
        "median_hr": float(np.median(hr_series)),
        "rr_mean_ms": float(np.mean(rr_ms)),
        "rr_std_ms": float(np.std(rr_ms, ddof=1)) if rr_ms.size > 1 else 0.0,
        "rr_min_ms": float(np.min(rr_ms)),
        "rr_max_ms": float(np.max(rr_ms)),
        "median_rr_ms": float(np.median(rr_ms)),
        "rmssd_ms": rmssd,
        "sdnn_ms": sdnn,
        "sdsd_ms": sdsd,
        "pnn20": pnn20,
        "pnn50": pnn50,
        "ecg_mean": float(np.mean(ecg)),
        "ecg_std": float(np.std(ecg)),
        "ecg_skewness": _nan_if_empty(ecg, skew),
        "ecg_kurtosis": _nan_if_empty(ecg, kurtosis),
        "ecg_fft_entropy": fft_entropy,
        "ecg_mean_frequency": mean_frequency,
        "ecg_zero_crossing_rate": _zero_crossing_rate(ecg),
        **freq_features,
    }, quality, notes


def extract_eda_features(eda: np.ndarray, fs: float) -> tuple[dict[str, float], float, list[str]]:
    if eda.size == 0:
        return {
            "eda_scl_mean": math.nan,
            "eda_tonic_std": math.nan,
            "eda_tonic_slope": math.nan,
            "eda_scr_count": math.nan,
            "eda_scr_amplitude_mean": math.nan,
            "eda_scr_amplitude_std": math.nan,
            "eda_scr_amplitude_max": math.nan,
            "eda_scr_area": math.nan,
            "eda_scr_density": math.nan,
            "eda_phasic_mean": math.nan,
            "eda_phasic_std": math.nan,
            "eda_phasic_max": math.nan,
            "eda_phasic_skewness": math.nan,
            "eda_phasic_kurtosis": math.nan,
            "eda_fft_entropy": math.nan,
            "eda_mean_frequency": math.nan,
            "eda_zero_crossing_rate": math.nan,
            "eda_nld": math.nan,
        }, 0.0, ["empty_eda"]

    if eda.size >= 5:
        win = max(5, int(fs * 5) // 2 * 2 + 1)
        if win >= eda.size:
            win = eda.size - 1 if eda.size % 2 == 0 else eda.size
            win = max(win, 5)
        tonic = signal.savgol_filter(eda, window_length=win, polyorder=2)
    else:
        tonic = eda
    phasic = eda - tonic
    prominence = max(np.std(phasic) * 0.35, 0.02)
    distance = max(int(fs), 1)
    peaks, props = signal.find_peaks(phasic, prominence=prominence, distance=distance)
    amplitudes = props.get("prominences", np.array([], dtype=float))
    tonic_times = np.arange(len(tonic)) / max(fs, 1e-6)
    tonic_slope = np.polyfit(tonic_times, tonic, 1)[0] if tonic.size > 1 else 0.0
    fft_entropy, mean_frequency = _spectral_summary(phasic, fs)
    flatline = float(np.std(eda) < 1e-4)
    finite_score = float(np.isfinite(eda).mean())
    dynamic_score = 1.0 - flatline
    quality = _clip01(0.7 * finite_score + 0.3 * dynamic_score)
    notes: list[str] = []
    if flatline:
        notes.append("eda_flatline")
    return {
        "eda_scl_mean": float(np.mean(tonic)),
        "eda_tonic_std": float(np.std(tonic)),
        "eda_tonic_slope": float(tonic_slope),
        "eda_scr_count": float(peaks.size),
        "eda_scr_amplitude_mean": float(np.mean(amplitudes)) if amplitudes.size else 0.0,
        "eda_scr_amplitude_std": float(np.std(amplitudes, ddof=1)) if amplitudes.size > 1 else 0.0,
        "eda_scr_amplitude_max": float(np.max(amplitudes)) if amplitudes.size else 0.0,
        "eda_scr_area": float(np.sum(np.clip(phasic, 0.0, None)) / max(fs, 1e-6)),
        "eda_scr_density": float(peaks.size / max(len(eda) / fs / 60.0, 1e-6)),
        "eda_phasic_mean": float(np.mean(phasic)),
        "eda_phasic_std": float(np.std(phasic)),
        "eda_phasic_max": float(np.max(phasic)),
        "eda_phasic_skewness": _nan_if_empty(phasic, skew),
        "eda_phasic_kurtosis": _nan_if_empty(phasic, kurtosis),
        "eda_fft_entropy": fft_entropy,
        "eda_mean_frequency": mean_frequency,
        "eda_zero_crossing_rate": _zero_crossing_rate(phasic),
        "eda_nld": _normalized_length_density(phasic),
    }, quality, notes


def extract_temperature_features(temperature: np.ndarray, fs: float, baseline: float | None = None) -> tuple[dict[str, float], float, list[str]]:
    if temperature.size == 0:
        return {
            "temp_mean": math.nan,
            "temp_min": math.nan,
            "temp_max": math.nan,
            "temp_slope_per_min": math.nan,
            "temp_delta_baseline": math.nan,
            "temp_std": math.nan,
        }, 0.0, ["empty_temperature"]
    times = np.arange(temperature.size) / max(fs, 1e-6)
    slope_per_s = np.polyfit(times, temperature, 1)[0] if temperature.size > 1 else 0.0
    mean_temp = float(np.mean(temperature))
    baseline_value = float(np.mean(temperature[: max(int(fs * 10), 1)])) if baseline is None else baseline
    jumps = np.abs(np.diff(temperature))
    jump_score = 1.0 - float(np.mean(jumps > 0.2)) if jumps.size else 1.0
    range_score = 1.0 if 30.0 <= mean_temp <= 40.0 else 0.0
    quality = _clip01(0.6 * jump_score + 0.4 * range_score)
    notes: list[str] = []
    if quality < 0.5:
        notes.append("temperature_spiky")
    return {
        "temp_mean": mean_temp,
        "temp_min": float(np.min(temperature)),
        "temp_max": float(np.max(temperature)),
        "temp_slope_per_min": float(slope_per_s * 60.0),
        "temp_delta_baseline": float(mean_temp - baseline_value),
        "temp_std": float(np.std(temperature)),
    }, quality, notes


def extract_acc_features(acc: np.ndarray) -> tuple[dict[str, float], float, float, list[str]]:
    if acc.size == 0:
        return {
            "acc_mean": math.nan,
            "acc_std": math.nan,
            "motion_ratio": math.nan,
        }, 0.0, 1.0, ["empty_acc"]
    magnitude = acc_magnitude(acc)
    centered = magnitude - np.median(magnitude)
    motion_ratio = float(np.mean(np.abs(centered) > 0.15))
    finite_score = float(np.isfinite(magnitude).mean())
    wear_score = _clip01(float(np.mean(magnitude)) / 0.5)
    quality = _clip01(0.6 * finite_score + 0.4 * wear_score)
    notes: list[str] = []
    if motion_ratio > 0.4:
        notes.append("high_motion")
    return {
        "acc_mean": float(np.mean(magnitude)),
        "acc_std": float(np.std(magnitude)),
        "motion_ratio": motion_ratio,
    }, quality, motion_ratio, notes


def combine_quality(
    ecg_quality: float,
    eda_quality: float,
    temperature_quality: float,
    acc_quality: float,
    motion_ratio: float,
    notes: list[str],
) -> QualityPacket:
    overall = float(np.mean([ecg_quality, eda_quality, temperature_quality, acc_quality]))
    is_worn = temperature_quality > 0.3 and acc_quality > 0.5
    essential_modalities_ok = ecg_quality >= 0.4 and eda_quality >= 0.4
    is_usable = overall >= 0.45 and motion_ratio <= 0.7 and is_worn and essential_modalities_ok
    if not is_worn:
        notes.append("possible_non_wear")
    if not essential_modalities_ok:
        notes.append("core_modalities_unreliable")
    if not is_usable:
        notes.append("low_overall_quality")
    return QualityPacket(
        ecg_quality=ecg_quality,
        eda_quality=eda_quality,
        temperature_quality=temperature_quality,
        acc_quality=acc_quality,
        overall_quality=overall,
        motion_artifact_ratio=motion_ratio,
        is_worn=is_worn,
        is_usable=is_usable,
        notes=notes,
    )


def extract_feature_packet(window: RawSignalWindow, recording_temperature_baseline: float | None = None) -> FeaturePacket:
    ecg = preprocess_ecg(window.ecg, window.ecg_hz)
    eda = preprocess_eda(window.eda, window.eda_hz)
    temperature = preprocess_temperature(window.temperature, window.temperature_hz)
    acc = preprocess_acc(window.acc)

    ecg_features, ecg_quality, ecg_notes = extract_ecg_features(ecg, window.ecg_hz)
    eda_features, eda_quality, eda_notes = extract_eda_features(eda, window.eda_hz)
    temp_features, temp_quality, temp_notes = extract_temperature_features(
        temperature, window.temperature_hz, baseline=recording_temperature_baseline
    )
    acc_features, acc_quality, motion_ratio, acc_notes = extract_acc_features(acc)

    quality = combine_quality(
        ecg_quality=ecg_quality,
        eda_quality=eda_quality,
        temperature_quality=temp_quality,
        acc_quality=acc_quality,
        motion_ratio=motion_ratio,
        notes=ecg_notes + eda_notes + temp_notes + acc_notes,
    )

    feature_map = {
        **ecg_features,
        **eda_features,
        **temp_features,
        **acc_features,
        "ecg_quality_score": ecg_quality,
        "eda_quality_score": eda_quality,
        "temperature_quality_score": temp_quality,
        "acc_quality_score": acc_quality,
        "window_duration_s": float(window.window_end_s - window.window_start_s),
        "quality_overall": quality.overall_quality,
    }
    return FeaturePacket(
        subject_id=window.subject_id,
        window_start_s=window.window_start_s,
        window_end_s=window.window_end_s,
        label=window.label,
        quality=quality,
        features=feature_map,
    )
