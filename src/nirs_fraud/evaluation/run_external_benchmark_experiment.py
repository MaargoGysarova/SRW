from __future__ import annotations

import csv
import time
from pathlib import Path

from .classifiers import MODELS
from .datasets import ROOT, load_experiment_03_rows
from .metrics import compute_classification_metrics
from .progress import finish_progress, render_progress

OUTPUT_DIR = ROOT / "outputs"


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run() -> tuple[list[dict], list[dict]]:
    rows = load_experiment_03_rows()
    predictions = []
    metrics_rows = []

    for model_name, model_fn in MODELS.items():
        y_true = []
        y_pred = []
        latencies_ms = []
        total_rows = len(rows)
        render_progress(f"exp3:{model_name}", completed=0, total=total_rows)
        for row_index, row in enumerate(rows, start=1):
            started = time.perf_counter()
            label, signals, score = model_fn(row["text"])
            elapsed_ms = (time.perf_counter() - started) * 1000
            latencies_ms.append(elapsed_ms)
            y_true.append(row["label"])
            y_pred.append(label)
            predictions.append(
                {
                    "experiment": "experiment_03_external_benchmark",
                    "model": model_name,
                    "id": row["id"],
                    "true_label": row["label"],
                    "predicted_label": label,
                    "fraud_score": round(score, 3),
                    "predicted_signals": "|".join(signals),
                    "scenario": row["scenario"],
                    "latency_ms": round(elapsed_ms, 3),
                }
            )
            render_progress(f"exp3:{model_name}", completed=row_index, total=total_rows)
        finish_progress()

        metric_row = {
            "experiment": "experiment_03_external_benchmark",
            "model": model_name,
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


def write_summary(path: Path, metrics_rows: list[dict]) -> None:
    lines = [
        "# Experiment 3 Summary",
        "",
        "| Model | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics_rows:
        lines.append(
            f"| {row['model']} | {row['accuracy']:.3f} | {row['precision_fraud']:.3f} | {row['recall_fraud']:.3f} | {row['f1_fraud']:.3f} | {row['false_positives']} | {row['false_negatives']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    predictions, metrics_rows = run()
    write_csv(OUTPUT_DIR / "experiment_03_predictions.csv", predictions)
    write_csv(OUTPUT_DIR / "experiment_03_metrics.csv", metrics_rows)
    write_summary(OUTPUT_DIR / "experiment_03_summary.md", metrics_rows)
    print(
        f"Wrote {len(predictions)} experiment 03 predictions and "
        f"{len(metrics_rows)} metric rows to {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
