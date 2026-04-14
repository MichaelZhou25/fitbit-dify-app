from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC

LABEL_ORDER = ["low", "medium", "high"]

BASELINE_FEATURE_SET_SPECS: dict[str, list[str]] = {
    "ECG-only": ["hr_mean", "rr_mean_ms", "rmssd_ms", "sdnn_ms", "pnn50", "ecg_quality_score"],
    "EDA-only": [
        "eda_scl_mean",
        "eda_scr_count",
        "eda_scr_amplitude_mean",
        "eda_scr_density",
        "eda_phasic_std",
        "eda_quality_score",
    ],
    "TEMP-only": [
        "temp_mean",
        "temp_std",
        "temp_min",
        "temp_max",
        "temp_slope_per_min",
        "temperature_quality_score",
    ],
    "ECG+EDA+TEMP": [
        "hr_mean",
        "rr_mean_ms",
        "rmssd_ms",
        "sdnn_ms",
        "pnn50",
        "eda_scl_mean",
        "eda_scr_count",
        "eda_scr_amplitude_mean",
        "eda_scr_density",
        "eda_phasic_std",
        "temp_mean",
        "temp_std",
        "temp_min",
        "temp_max",
        "temp_slope_per_min",
        "ecg_quality_score",
        "eda_quality_score",
        "temperature_quality_score",
    ],
}

EXPANDED_FEATURE_SET_SPECS: dict[str, list[str]] = {
    "ECG-only-expanded": [
        "hr_mean",
        "hr_std",
        "median_hr",
        "rr_mean_ms",
        "rr_std_ms",
        "rr_min_ms",
        "rr_max_ms",
        "median_rr_ms",
        "rmssd_ms",
        "sdnn_ms",
        "sdsd_ms",
        "pnn20",
        "pnn50",
        "ecg_mean",
        "ecg_std",
        "ecg_skewness",
        "ecg_kurtosis",
        "ecg_fft_entropy",
        "ecg_mean_frequency",
        "ecg_zero_crossing_rate",
        "lf_power",
        "hf_power",
        "lf_hf_ratio",
        "ecg_quality_score",
    ],
    "EDA-only-expanded": [
        "eda_scl_mean",
        "eda_tonic_std",
        "eda_tonic_slope",
        "eda_scr_count",
        "eda_scr_amplitude_mean",
        "eda_scr_amplitude_std",
        "eda_scr_amplitude_max",
        "eda_scr_area",
        "eda_scr_density",
        "eda_phasic_mean",
        "eda_phasic_std",
        "eda_phasic_max",
        "eda_phasic_skewness",
        "eda_phasic_kurtosis",
        "eda_fft_entropy",
        "eda_mean_frequency",
        "eda_zero_crossing_rate",
        "eda_nld",
        "eda_quality_score",
    ],
    "ECG+EDA+TEMP-expanded": [
        "hr_mean",
        "hr_std",
        "median_hr",
        "rr_mean_ms",
        "rr_std_ms",
        "rr_min_ms",
        "rr_max_ms",
        "median_rr_ms",
        "rmssd_ms",
        "sdnn_ms",
        "sdsd_ms",
        "pnn20",
        "pnn50",
        "ecg_mean",
        "ecg_std",
        "ecg_skewness",
        "ecg_kurtosis",
        "ecg_fft_entropy",
        "ecg_mean_frequency",
        "ecg_zero_crossing_rate",
        "lf_power",
        "hf_power",
        "lf_hf_ratio",
        "eda_scl_mean",
        "eda_tonic_std",
        "eda_tonic_slope",
        "eda_scr_count",
        "eda_scr_amplitude_mean",
        "eda_scr_amplitude_std",
        "eda_scr_amplitude_max",
        "eda_scr_area",
        "eda_scr_density",
        "eda_phasic_mean",
        "eda_phasic_std",
        "eda_phasic_max",
        "eda_phasic_skewness",
        "eda_phasic_kurtosis",
        "eda_fft_entropy",
        "eda_mean_frequency",
        "eda_zero_crossing_rate",
        "eda_nld",
        "temp_mean",
        "temp_std",
        "temp_min",
        "temp_max",
        "temp_slope_per_min",
        "ecg_quality_score",
        "eda_quality_score",
        "temperature_quality_score",
    ],
}

FEATURE_SET_SPECS: dict[str, list[str]] = {
    **BASELINE_FEATURE_SET_SPECS,
    **EXPANDED_FEATURE_SET_SPECS,
}


def get_feature_set_specs(mode: str = "all", *, window_sec: float | None = None) -> dict[str, list[str]]:
    selected_mode = mode.lower()
    if selected_mode == "baseline":
        return BASELINE_FEATURE_SET_SPECS
    if selected_mode == "expanded":
        specs = dict(EXPANDED_FEATURE_SET_SPECS)
        if window_sec is not None and window_sec <= 10.0:
            short_ecg = [
                col
                for col in specs["ECG-only-expanded"]
                if col not in {"lf_power", "hf_power", "lf_hf_ratio"}
            ]
            short_fusion = [
                col
                for col in specs["ECG+EDA+TEMP-expanded"]
                if col not in {"lf_power", "hf_power", "lf_hf_ratio"}
            ]
            specs["ECG-only-expanded"] = short_ecg
            specs["ECG+EDA+TEMP-expanded"] = short_fusion
        return specs
    if selected_mode == "all":
        specs = dict(BASELINE_FEATURE_SET_SPECS)
        specs.update(get_feature_set_specs("expanded", window_sec=window_sec))
        return specs
    raise ValueError(f"Unsupported feature set mode: {mode}")


def build_estimator(model_name: str) -> Pipeline:
    name = model_name.upper()
    if name == "LR":
        classifier = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)
        preprocessor = ColumnTransformer([("scale", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), slice(0, None))])
    elif name == "SVM":
        classifier = SVC(kernel="rbf", class_weight="balanced", gamma="scale", random_state=42)
        preprocessor = ColumnTransformer([("scale", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), slice(0, None))])
    elif name == "RF":
        classifier = RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            class_weight="balanced",
            random_state=42,
        )
        preprocessor = ColumnTransformer([("impute", SimpleImputer(strategy="median"), slice(0, None))])
    elif name in {"BOOSTING", "GB", "GBDT"}:
        classifier = GradientBoostingClassifier(random_state=42)
        preprocessor = ColumnTransformer([("impute", SimpleImputer(strategy="median"), slice(0, None))])
    else:
        raise ValueError(f"Unsupported model_name={model_name}")
    return Pipeline([("preprocessor", preprocessor), ("classifier", classifier)])


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray, label_order: list[str] | None = None) -> dict[str, Any]:
    labels = label_order or LABEL_ORDER
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "classification_report": classification_report(y_true, y_pred, labels=labels, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def run_random_split_experiment(
    df_features: pd.DataFrame,
    model_name: str,
    feature_set_name: str,
    feature_cols: list[str],
    *,
    label_col: str = "label_name",
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, Any]:
    from sklearn.model_selection import train_test_split

    frame = df_features.dropna(subset=[label_col]).copy()
    X = frame[feature_cols]
    y = frame[label_col].astype(str)

    X_train, X_test, y_train, y_test, train_idx, test_idx = train_test_split(
        X,
        y,
        frame.index.to_numpy(),
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    model = build_estimator(model_name)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    metrics = evaluate_predictions(y_test.to_numpy(), y_pred)

    train_subjects = sorted(frame.loc[train_idx, "subject_id"].astype(str).unique().tolist())
    test_subjects = sorted(frame.loc[test_idx, "subject_id"].astype(str).unique().tolist())
    return {
        "protocol": "random_split",
        "model_name": model_name,
        "feature_set_name": feature_set_name,
        "feature_cols": feature_cols,
        "n_train_windows": int(len(X_train)),
        "n_test_windows": int(len(X_test)),
        "train_subjects": train_subjects,
        "test_subjects": test_subjects,
        **metrics,
    }


def run_loso_experiment(
    df_features: pd.DataFrame,
    model_name: str,
    feature_set_name: str,
    feature_cols: list[str],
    *,
    subject_col: str = "subject_id",
    label_col: str = "label_name",
) -> dict[str, Any]:
    frame = df_features.dropna(subset=[label_col]).copy()
    subjects = sorted(frame[subject_col].astype(str).unique().tolist())
    if len(subjects) < 2:
        raise ValueError("LOSO requires at least two subjects.")

    fold_results: list[dict[str, Any]] = []
    y_true_all: list[str] = []
    y_pred_all: list[str] = []

    for test_subject in subjects:
        train_df = frame[frame[subject_col].astype(str) != test_subject]
        test_df = frame[frame[subject_col].astype(str) == test_subject]
        if train_df.empty or test_df.empty:
            continue

        model = build_estimator(model_name)
        model.fit(train_df[feature_cols], train_df[label_col].astype(str))
        y_true = test_df[label_col].astype(str).to_numpy()
        y_pred = model.predict(test_df[feature_cols])

        y_true_all.extend(y_true.tolist())
        y_pred_all.extend(y_pred.tolist())
        fold_metrics = evaluate_predictions(y_true, y_pred)
        fold_results.append(
            {
                "test_subject": test_subject,
                "train_subjects": sorted(train_df[subject_col].astype(str).unique().tolist()),
                "n_train_windows": int(len(train_df)),
                "n_test_windows": int(len(test_df)),
                "accuracy": fold_metrics["accuracy"],
                "macro_f1": fold_metrics["macro_f1"],
                "classification_report": fold_metrics["classification_report"],
                "confusion_matrix": fold_metrics["confusion_matrix"],
            }
        )

    metrics = evaluate_predictions(np.asarray(y_true_all), np.asarray(y_pred_all))
    fold_macro_f1 = np.asarray([fold["macro_f1"] for fold in fold_results], dtype=float)
    fold_accuracy = np.asarray([fold["accuracy"] for fold in fold_results], dtype=float)

    return {
        "protocol": "loso",
        "model_name": model_name,
        "feature_set_name": feature_set_name,
        "feature_cols": feature_cols,
        "subjects": subjects,
        "fold_results": fold_results,
        "subject_level_summary": {
            "fold_count": len(fold_results),
            "accuracy_mean": float(np.mean(fold_accuracy)),
            "accuracy_std": float(np.std(fold_accuracy)),
            "macro_f1_mean": float(np.mean(fold_macro_f1)),
            "macro_f1_std": float(np.std(fold_macro_f1)),
        },
        **metrics,
    }


def save_json(data: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def maybe_save_plots(
    results_df: pd.DataFrame,
    best_result: dict[str, Any],
    feature_importance_frame: pd.DataFrame | None,
    output_dir: str | Path,
) -> list[Path]:
    output_paths: list[Path] = []
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return output_paths

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pivot = results_df.pivot(index="model_name", columns="feature_set_name", values="macro_f1")
    fig, ax = plt.subplots(figsize=(10, 6))
    pivot.plot(kind="bar", ax=ax)
    ax.set_title("LOSO Macro-F1 by model and feature set")
    ax.set_ylabel("Macro-F1")
    ax.set_xlabel("Model")
    fig.tight_layout()
    bar_path = out_dir / "loso_macro_f1.png"
    fig.savefig(bar_path, dpi=150)
    plt.close(fig)
    output_paths.append(bar_path)

    cm = np.asarray(best_result["confusion_matrix"])
    fig, ax = plt.subplots(figsize=(5, 5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_title(f"Best LOSO confusion matrix\n{best_result['model_name']} + {best_result['feature_set_name']}")
    ax.set_xticks(range(len(LABEL_ORDER)), LABEL_ORDER)
    ax.set_yticks(range(len(LABEL_ORDER)), LABEL_ORDER)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    cm_path = out_dir / "best_loso_confusion_matrix.png"
    fig.savefig(cm_path, dpi=150)
    plt.close(fig)
    output_paths.append(cm_path)

    if feature_importance_frame is not None and not feature_importance_frame.empty:
        top = feature_importance_frame.head(15).sort_values("importance", ascending=True)
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.barh(top["feature"], top["importance"])
        ax.set_title("Best tree model feature importance")
        ax.set_xlabel("Importance")
        fig.tight_layout()
        fi_path = out_dir / "best_tree_feature_importance.png"
        fig.savefig(fi_path, dpi=150)
        plt.close(fig)
        output_paths.append(fi_path)

    return output_paths


def extract_feature_importance(model_name: str, estimator: Pipeline, feature_cols: list[str]) -> pd.DataFrame | None:
    if model_name.upper() not in {"RF", "BOOSTING", "GB", "GBDT"}:
        return None
    classifier = estimator.named_steps["classifier"]
    if not hasattr(classifier, "feature_importances_"):
        return None
    importances = np.asarray(classifier.feature_importances_, dtype=float)
    return pd.DataFrame({"feature": feature_cols, "importance": importances}).sort_values("importance", ascending=False)


def fit_final_model(df_features: pd.DataFrame, model_name: str, feature_cols: list[str], *, label_col: str = "label_name") -> tuple[Pipeline, LabelEncoder]:
    frame = df_features.dropna(subset=[label_col]).copy()
    encoder = LabelEncoder()
    y = encoder.fit_transform(frame[label_col].astype(str))
    estimator = build_estimator(model_name)
    estimator.fit(frame[feature_cols], encoder.inverse_transform(y))
    return estimator, encoder
