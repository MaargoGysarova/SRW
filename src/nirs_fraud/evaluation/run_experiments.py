from __future__ import annotations

import csv
import time
from pathlib import Path

from .classifiers import MODELS, load_jsonl
from .metrics import compute_classification_metrics

ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = ROOT / "data" / "04_final_dataset" / "internal_synthetic_core_v0.jsonl"
OUTPUT_DIR = ROOT / "outputs"


def run() -> tuple[list[dict], list[dict]]:
    rows = load_jsonl(DATASET_PATH)
    predictions = []
    metrics_rows = []

    for model_name, model_fn in MODELS.items():
        y_true = []
        y_pred = []
        latencies_ms = []
        for row in rows:
            started = time.perf_counter()
            label, signals, score = model_fn(row["text"])
            elapsed_ms = (time.perf_counter() - started) * 1000
            latencies_ms.append(elapsed_ms)
            y_true.append(row["label"])
            y_pred.append(label)
            predictions.append(
                {
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
        metric_row = {"model": model_name}
        metric_row.update(
            compute_classification_metrics(
                y_true,
                y_pred,
                latency_ms_avg=sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0,
            )
        )
        metrics_rows.append(metric_row)

    return predictions, metrics_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, metrics_rows: list[dict]) -> None:
    lines = [
        "# Experiment Summary",
        "",
        "## Experiment 1 — Baseline Classification",
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
    write_csv(OUTPUT_DIR / "predictions.csv", predictions)
    write_csv(OUTPUT_DIR / "metrics.csv", metrics_rows)
    write_summary(OUTPUT_DIR / "summary.md", metrics_rows)
    print(f"Wrote {len(predictions)} predictions and {len(metrics_rows)} metrics rows to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
