from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..packets import MultimodalRecording


@dataclass
class WESADSubjectBundle:
    subject_id: str
    recording: MultimodalRecording
    raw_label_samples: np.ndarray


def discover_wesad_pickles(root: str | Path) -> list[Path]:
    root_path = Path(root)
    nested = sorted(root_path.glob("S*/S*.pkl"))
    flat = sorted(root_path.glob("S*.pkl"))
    return nested or flat


def load_wesad_subject(path: str | Path) -> WESADSubjectBundle:
    file_path = Path(path)
    with file_path.open("rb") as f:
        payload = pickle.load(f, encoding="latin1")

    signal_block = payload["signal"]
    chest = signal_block["chest"]
    wrist = signal_block["wrist"]

    ecg = np.asarray(chest["ECG"], dtype=float).reshape(-1)
    eda = np.asarray(wrist["EDA"], dtype=float).reshape(-1)
    temperature = np.asarray(wrist["TEMP"], dtype=float).reshape(-1)
    acc = np.asarray(wrist["ACC"], dtype=float)
    labels = np.asarray(payload["label"]).reshape(-1)
    subject_id = str(payload.get("subject", file_path.stem))

    recording = MultimodalRecording(
        subject_id=subject_id,
        ecg_hz=700.0,
        eda_hz=4.0,
        temperature_hz=4.0,
        acc_hz=32.0,
        ecg=ecg.tolist(),
        eda=eda.tolist(),
        temperature=temperature.tolist(),
        acc=acc.tolist(),
        label_samples=labels.astype(int).tolist(),
        label_hz=700.0,
    )
    return WESADSubjectBundle(subject_id=subject_id, recording=recording, raw_label_samples=labels)

