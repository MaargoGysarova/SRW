from __future__ import annotations

import csv
import time
from pathlib import Path

from .classifiers import MODELS
from .datasets import ROOT, build_experiment_02_variant_rows
from .metrics import compute_classification_metrics
from .progress import finish_progress, render_progress

OUTPUT_DIR = ROOT / "outputs"

TARGET_MODELS = ("llm_checklist", "llm_self_check", "llm_ensemble")
TARGET_VARIANTS = ("original", "paraphrase", "subtle", "asr_noise")


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_variant_rows() -> list[dict]:
    return build_experiment_02_variant_rows(variants=TARGET_VARIANTS[1:])


def run() -> tuple[list[dict], list[dict]]:
    rows = build_variant_rows()
    predictions = []
    metrics_rows = []

    for model_name in TARGET_MODELS:
        model_fn = MODELS[model_name]
        for variant in TARGET_VARIANTS:
            subset = [row for row in rows if row["variant"] == variant]
            if not subset:
                continue
            y_true = []
            y_pred = []
            latencies_ms = []
            total_rows = len(subset)
            render_progress(f"exp2:{model_name}:{variant}", completed=0, total=total_rows)
            for row_index, row in enumerate(subset, start=1):
                started = time.perf_counter()
                label, signals, score = model_fn(row["text"])
                elapsed_ms = (time.perf_counter() - started) * 1000
                latencies_ms.append(elapsed_ms)
                y_true.append(row["label"])
                y_pred.append(label)
                predictions.append(
                    {
                        "experiment": "experiment_02_augmentation_robustness",
                        "model": model_name,
                        "variant": variant,
                        "sample_id": row["sample_id"],
                        "base_id": row["base_id"],
                        "true_label": row["label"],
                        "predicted_label": label,
                        "fraud_score": round(score, 3),
                        "predicted_signals": "|".join(signals),
                        "latency_ms": round(elapsed_ms, 3),
                    }
                )
                render_progress(f"exp2:{model_name}:{variant}", completed=row_index, total=total_rows)
            finish_progress()

            metric_row = {
                "experiment": "experiment_02_augmentation_robustness",
                "model": model_name,
                "variant": variant,
            }
            metric_row.update(
                compute_classification_metrics(
                    y_true,
                    y_pred,
                    latency_ms_avg=sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0,
                )
            )
            metrics_rows.append(metric_row)

    return predictions, metrics_rows


def write_summary(path: Path, rows: list[dict]) -> None:
    lines = [
        "# Experiment 2 Summary",
        "",
        "| Model | Variant | Accuracy | Recall fraud | FP | FN |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['model']} | {row['variant']} | {row['accuracy']:.3f} | {row['recall_fraud']:.3f} | {row['false_positives']} | {row['false_negatives']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    predictions, metrics_rows = run()
    write_csv(OUTPUT_DIR / "experiment_02_predictions.csv", predictions)
    write_csv(OUTPUT_DIR / "experiment_02_metrics.csv", metrics_rows)
    write_summary(OUTPUT_DIR / "experiment_02_summary.md", metrics_rows)
    print(
        f"Wrote {len(predictions)} experiment 02 predictions and "
        f"{len(metrics_rows)} metric rows to {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
