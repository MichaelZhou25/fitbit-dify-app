from __future__ import annotations

import unittest

import pandas as pd

from anxiety_monitor.experiments import FEATURE_SET_SPECS, run_loso_experiment, run_random_split_experiment


def make_feature_table() -> pd.DataFrame:
    rows = []
    for subject_idx, subject_id in enumerate(["S1", "S2", "S3"]):
        for label_name, label_value in [("low", 1), ("medium", 3), ("high", 2)]:
            for repeat in range(4):
                base = subject_idx * 0.1 + repeat * 0.01
                if label_name == "low":
                    hr_mean, rmssd_ms, scl, temp = 70 + base, 45 + base, 1.2 + base, 36.4 + base
                elif label_name == "medium":
                    hr_mean, rmssd_ms, scl, temp = 84 + base, 28 + base, 2.0 + base, 36.6 + base
                else:
                    hr_mean, rmssd_ms, scl, temp = 102 + base, 14 + base, 3.0 + base, 36.9 + base
                rows.append(
                    {
                        "subject_id": subject_id,
                        "window_start_s": repeat * 30.0,
                        "window_end_s": repeat * 30.0 + 60.0,
                        "label": label_value,
                        "label_name": label_name,
                        "hr_mean": hr_mean,
                        "rr_mean_ms": 60000.0 / hr_mean,
                        "rmssd_ms": rmssd_ms,
                        "sdnn_ms": rmssd_ms * 0.8,
                        "pnn50": 0.4 if label_name == "low" else 0.2 if label_name == "medium" else 0.05,
                        "eda_scl_mean": scl,
                        "eda_scr_count": 1 if label_name == "low" else 3 if label_name == "medium" else 6,
                        "eda_scr_amplitude_mean": 0.08 if label_name == "low" else 0.18 if label_name == "medium" else 0.28,
                        "eda_scr_density": 1.5 if label_name == "low" else 3.5 if label_name == "medium" else 6.5,
                        "eda_phasic_std": 0.01 if label_name == "low" else 0.03 if label_name == "medium" else 0.06,
                        "temp_mean": temp,
                        "temp_std": 0.04,
                        "temp_min": temp - 0.08,
                        "temp_max": temp + 0.08,
                        "temp_slope_per_min": 0.01 if label_name == "low" else 0.04 if label_name == "medium" else 0.08,
                        "ecg_quality_score": 0.95,
                        "eda_quality_score": 0.92,
                        "temperature_quality_score": 0.96,
                    }
                )
    return pd.DataFrame(rows)


class ExperimentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.feature_table = make_feature_table()
        self.feature_cols = FEATURE_SET_SPECS["ECG+EDA+TEMP"]

    def test_random_split_experiment_returns_expected_fields(self) -> None:
        result = run_random_split_experiment(self.feature_table, "LR", "ECG+EDA+TEMP", self.feature_cols)
        self.assertEqual(result["protocol"], "random_split")
        self.assertGreater(result["n_train_windows"], 0)
        self.assertGreater(result["n_test_windows"], 0)
        self.assertIn("classification_report", result)
        self.assertIn("macro_f1", result)

    def test_loso_uses_single_subject_for_each_test_fold(self) -> None:
        result = run_loso_experiment(self.feature_table, "RF", "ECG+EDA+TEMP", self.feature_cols)
        self.assertEqual(result["protocol"], "loso")
        self.assertEqual(len(result["fold_results"]), 3)
        for fold in result["fold_results"]:
            self.assertEqual(len(set([fold["test_subject"]])), 1)
            self.assertNotIn(fold["test_subject"], fold["train_subjects"])
            self.assertGreater(fold["n_test_windows"], 0)

    def test_loso_covers_all_subjects_once(self) -> None:
        result = run_loso_experiment(self.feature_table, "SVM", "ECG+EDA+TEMP", self.feature_cols)
        test_subjects = [fold["test_subject"] for fold in result["fold_results"]]
        self.assertEqual(sorted(test_subjects), ["S1", "S2", "S3"])


if __name__ == "__main__":
    unittest.main()
