from __future__ import annotations

import csv
import time
from pathlib import Path

from .classifiers import MODELS, load_jsonl
from .metrics import compute_classification_metrics


ROOT = Path(__file__).resolve().parents[3]
GENERATOR_INPUT_PATH = ROOT / "data" / "01_generator" / "outputs" / "internal_generated_candidates_v0.jsonl"
AUGMENTATION_INPUT_PATH = ROOT / "data" / "02_augmentator" / "outputs" / "augmentation_subset_v0.jsonl"
OUTPUT_DIR = ROOT / "outputs"

TARGET_MODELS = ("llm_checklist", "llm_self_check", "llm_ensemble")
TARGET_VARIANTS = ("original", "paraphrase", "subtle", "asr_noise")


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def require_jsonl(path: Path, label: str) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"{label} file not found: {path}. "
            "Сначала нужно получить данные генератора и аугментатора."
        )
    return load_jsonl(path)


def build_variant_rows() -> list[dict]:
    original_rows = require_jsonl(GENERATOR_INPUT_PATH, "generator output")
    augmentation_rows = require_jsonl(AUGMENTATION_INPUT_PATH, "augmentation output")
    originals_by_id = {row["id"]: row for row in original_rows}

    combined = []
    for aug in augmentation_rows:
        base_id = aug["base_id"]
        aug_type = aug["augmentation_type"]
        if aug_type not in TARGET_VARIANTS[1:]:
            continue
        base = originals_by_id.get(base_id)
        if base is None:
            continue
        combined.append(
            {
                "variant": "original",
                "sample_id": base["id"],
                "base_id": base["id"],
                "label": base["label"],
                "scenario": base["scenario"],
                "text": base["text"],
            }
        )
        combined.append(
            {
                "variant": aug_type,
                "sample_id": aug["id"],
                "base_id": base["id"],
                "label": aug["label"],
                "scenario": base["scenario"],
                "text": aug["text"],
            }
        )

    deduped = {}
    for row in combined:
        deduped[(row["variant"], row["sample_id"])] = row
    return list(deduped.values())


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
            for row in subset:
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
