from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import pandas as pd

from anxiety_monitor.datasets import discover_wesad_pickles, load_wesad_subject
from anxiety_monitor.experiments import (
    BASELINE_FEATURE_SET_SPECS,
    EXPANDED_FEATURE_SET_SPECS,
    extract_feature_importance,
    fit_final_model,
    get_feature_set_specs,
    maybe_save_plots,
    run_loso_experiment,
    run_random_split_experiment,
    save_json,
)
from anxiety_monitor.pipeline import AnxietyRiskPipeline

MODEL_SPECS = {
    "LR": "Logistic Regression",
    "SVM": "Support Vector Machine",
    "RF": "Random Forest",
    "Boosting": "Gradient Boosting",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-subject WESAD experiments with random split and LOSO.")
    parser.add_argument("--wesad-root", type=Path, required=True, help="Root directory containing WESAD subject pickle files.")
    parser.add_argument("--window-sec", type=float, default=60.0)
    parser.add_argument("--step-sec", type=float, default=30.0)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/wesad_experiments"))
    parser.add_argument(
        "--feature-set-mode",
        choices=["baseline", "expanded", "all"],
        default="all",
        help="Choose which feature set families to evaluate.",
    )
    parser.add_argument("--save-final-model", action="store_true", help="Fit and save a final model using the best LOSO setup.")
    return parser.parse_args()


def collect_feature_table(wesad_root: Path, pipeline: AnxietyRiskPipeline) -> pd.DataFrame:
    subject_paths = discover_wesad_pickles(wesad_root)
    if not subject_paths:
        raise FileNotFoundError(f"No WESAD pickle files found under {wesad_root}")

    subject_frames: list[pd.DataFrame] = []
    for path in subject_paths:
        subject = load_wesad_subject(path)
        frame = pipeline.prepare_training_frame(subject.recording)
        if frame.empty:
            print(f"{subject.subject_id}: usable windows=0")
            continue
        subject_frames.append(frame)
        print(f"{subject.subject_id}: usable windows={len(frame)}")

    if not subject_frames:
        raise RuntimeError("No usable windows extracted from WESAD.")
    return pd.concat(subject_frames, ignore_index=True)


def print_dataset_summary(feature_table: pd.DataFrame) -> None:
    subject_counts = feature_table.groupby("subject_id").size().to_dict()
    label_counts = feature_table["label_name"].value_counts().to_dict()
    print("\nDataset summary:")
    print(f"Subjects: {len(subject_counts)}")
    print(f"Windows : {len(feature_table)}")
    print(f"Per subject windows: {subject_counts}")
    print(f"Label distribution : {label_counts}")


def main() -> None:
    args = parse_args()
    pipeline = AnxietyRiskPipeline(window_sec=args.window_sec, step_sec=args.step_sec)
    feature_table = collect_feature_table(args.wesad_root, pipeline)
    print_dataset_summary(feature_table)
    selected_feature_sets = get_feature_set_specs(args.feature_set_mode, window_sec=args.window_sec)
    print(f"\nUsing feature set mode: {args.feature_set_mode}")
    print(f"Feature sets: {list(selected_feature_sets.keys())}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    feature_table.to_csv(args.output_dir / "feature_table.csv", index=False)

    random_results: list[dict] = []
    loso_results: list[dict] = []

    for model_name in MODEL_SPECS:
        for feature_set_name, feature_cols in selected_feature_sets.items():
            print(f"\nRunning {model_name} + {feature_set_name}")
            random_result = run_random_split_experiment(feature_table, model_name, feature_set_name, feature_cols)
            loso_result = run_loso_experiment(feature_table, model_name, feature_set_name, feature_cols)
            random_results.append(random_result)
            loso_results.append(loso_result)
            print(
                f"  random_split macro-F1={random_result['macro_f1']:.4f} "
                f"| LOSO macro-F1={loso_result['subject_level_summary']['macro_f1_mean']:.4f} "
                f"(std={loso_result['subject_level_summary']['macro_f1_std']:.4f})"
            )

    random_summary = pd.DataFrame(
        [
            {
                "model_name": item["model_name"],
                "feature_set_name": item["feature_set_name"],
                "accuracy": item["accuracy"],
                "macro_f1": item["macro_f1"],
                "n_train_windows": item["n_train_windows"],
                "n_test_windows": item["n_test_windows"],
            }
            for item in random_results
        ]
    ).sort_values(["macro_f1", "accuracy"], ascending=False)

    loso_summary = pd.DataFrame(
        [
            {
                "model_name": item["model_name"],
                "feature_set_name": item["feature_set_name"],
                "accuracy": item["accuracy"],
                "macro_f1": item["macro_f1"],
                "subject_accuracy_mean": item["subject_level_summary"]["accuracy_mean"],
                "subject_accuracy_std": item["subject_level_summary"]["accuracy_std"],
                "subject_macro_f1_mean": item["subject_level_summary"]["macro_f1_mean"],
                "subject_macro_f1_std": item["subject_level_summary"]["macro_f1_std"],
            }
            for item in loso_results
        ]
    ).sort_values(["subject_macro_f1_mean", "subject_accuracy_mean"], ascending=False)

    random_summary.to_csv(args.output_dir / "random_split_summary.csv", index=False)
    loso_summary.to_csv(args.output_dir / "loso_summary.csv", index=False)
    save_json({"results": random_results}, args.output_dir / "random_split_results.json")
    save_json({"results": loso_results}, args.output_dir / "loso_results.json")

    if args.feature_set_mode == "all":
        random_summary["feature_family"] = random_summary["feature_set_name"].apply(
            lambda name: "expanded" if "expanded" in name else "baseline"
        )
        loso_summary["feature_family"] = loso_summary["feature_set_name"].apply(
            lambda name: "expanded" if "expanded" in name else "baseline"
        )
        baseline_vs_expanded = []
        pairings = [
            ("ECG-only", "ECG-only-expanded"),
            ("EDA-only", "EDA-only-expanded"),
            ("ECG+EDA+TEMP", "ECG+EDA+TEMP-expanded"),
        ]
        for model_name in MODEL_SPECS:
            for baseline_name, expanded_name in pairings:
                base_rows = loso_summary[
                    (loso_summary["model_name"] == model_name) & (loso_summary["feature_set_name"] == baseline_name)
                ]
                exp_rows = loso_summary[
                    (loso_summary["model_name"] == model_name) & (loso_summary["feature_set_name"] == expanded_name)
                ]
                if base_rows.empty or exp_rows.empty:
                    continue
                base = base_rows.iloc[0]
                exp = exp_rows.iloc[0]
                baseline_vs_expanded.append(
                    {
                        "window_config": f"{args.window_sec:g}s/{args.step_sec:g}s",
                        "model_name": model_name,
                        "baseline_feature_set": baseline_name,
                        "expanded_feature_set": expanded_name,
                        "baseline_subject_macro_f1_mean": base["subject_macro_f1_mean"],
                        "expanded_subject_macro_f1_mean": exp["subject_macro_f1_mean"],
                        "delta_subject_macro_f1_mean": exp["subject_macro_f1_mean"] - base["subject_macro_f1_mean"],
                    }
                )
        comparison_df = pd.DataFrame(baseline_vs_expanded).sort_values(
            ["delta_subject_macro_f1_mean", "expanded_subject_macro_f1_mean"], ascending=False
        )
        comparison_df.to_csv(args.output_dir / "baseline_vs_expanded_summary.csv", index=False)

    print("\nRandom split summary:")
    print(random_summary.to_string(index=False))
    print("\nLOSO summary:")
    print(loso_summary.to_string(index=False))
    if args.feature_set_mode == "all" and 'comparison_df' in locals() and not comparison_df.empty:
        print("\nBaseline vs expanded summary:")
        print(comparison_df.to_string(index=False))

    best_loso_result = max(loso_results, key=lambda item: item["subject_level_summary"]["macro_f1_mean"])
    print("\nBest LOSO setting:")
    print(
        f"{best_loso_result['model_name']} + {best_loso_result['feature_set_name']} "
        f"| macro-F1 mean={best_loso_result['subject_level_summary']['macro_f1_mean']:.4f} "
        f"std={best_loso_result['subject_level_summary']['macro_f1_std']:.4f}"
    )

    best_tree_importance = None
    tree_candidates = [item for item in loso_results if item["model_name"].upper() in {"RF", "BOOSTING"}]
    if tree_candidates:
        best_tree_result = max(tree_candidates, key=lambda item: item["subject_level_summary"]["macro_f1_mean"])
        estimator, _ = fit_final_model(feature_table, best_tree_result["model_name"], best_tree_result["feature_cols"])
        best_tree_importance = extract_feature_importance(
            best_tree_result["model_name"], estimator, best_tree_result["feature_cols"]
        )
        if best_tree_importance is not None:
            best_tree_importance.to_csv(args.output_dir / "best_tree_feature_importance.csv", index=False)

    plot_frame = loso_summary[["model_name", "feature_set_name", "subject_macro_f1_mean"]].rename(
        columns={"subject_macro_f1_mean": "macro_f1"}
    )
    plot_paths = maybe_save_plots(plot_frame, best_loso_result, best_tree_importance, args.output_dir)
    if plot_paths:
        print("\nSaved plots:")
        for path in plot_paths:
            print(f"  {path}")

    if args.save_final_model:
        estimator, encoder = fit_final_model(feature_table, best_loso_result["model_name"], best_loso_result["feature_cols"])
        payload = {
            "estimator": estimator,
            "label_encoder": encoder,
            "feature_cols": best_loso_result["feature_cols"],
            "model_name": best_loso_result["model_name"],
            "feature_set_name": best_loso_result["feature_set_name"],
            "protocol": "selected_by_loso",
        }
        model_path = args.output_dir / "best_loso_final_model.pkl"
        with model_path.open("wb") as f:
            pickle.dump(payload, f)
        print(f"\nSaved final model to {model_path}")


if __name__ == "__main__":
    main()
