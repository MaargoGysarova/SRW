from __future__ import annotations

import argparse
from pathlib import Path

from .datasets import ROOT, load_experiment_03_rows
from .local_llm import (
    DEFAULT_LOCAL_LLM_MODEL,
    DEFAULT_MAX_NEW_TOKENS,
    DEFAULT_TEMPERATURE,
    TransformersClassificationBackend,
    classify_text,
    slugify_model_name,
    write_csv,
)
from .metrics import compute_classification_metrics
from .progress import finish_progress, render_progress


OUTPUT_DIR = ROOT / "outputs"
DEFAULT_ARCHITECTURES = ("single_llm", "llm_checklist", "llm_self_check", "llm_ensemble")


def write_summary(path: Path, metrics_rows: list[dict]) -> None:
    lines = [
        "# Local LLM Experiment 3 Summary",
        "",
        "| Model | Architecture | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics_rows:
        lines.append(
            f"| {row['model']} | {row['architecture']} | {row['accuracy']:.3f} | {row['precision_fraud']:.3f} | {row['recall_fraud']:.3f} | {row['f1_fraud']:.3f} | {row['false_positives']} | {row['false_negatives']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    *,
    model: str,
    architectures: tuple[str, ...],
    max_new_tokens: int,
    temperature: float,
) -> tuple[list[dict], list[dict]]:
    rows = load_experiment_03_rows()
    backend = TransformersClassificationBackend(
        model_name=model,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
    )

    predictions: list[dict] = []
    metrics_rows: list[dict] = []

    for architecture in architectures:
        y_true: list[str] = []
        y_pred: list[str] = []
        latencies_ms: list[float] = []
        total_rows = len(rows)
        render_progress(f"exp3:{architecture}", completed=0, total=total_rows)
        for row_index, row in enumerate(rows, start=1):
            normalized, elapsed_ms = classify_text(
                backend=backend,
                text=row["text"],
                architecture=architecture,
            )
            y_true.append(row["label"])
            y_pred.append(normalized["label"])
            latencies_ms.append(elapsed_ms)
            predictions.append(
                {
                    "experiment": "experiment_03_external_benchmark",
                    "model": model,
                    "architecture": architecture,
                    "id": row["id"],
                    "true_label": row["label"],
                    "predicted_label": normalized["label"],
                    "fraud_score": normalized["fraud_score"],
                    "predicted_signals": "|".join(normalized["signals"]),
                    "explanation": normalized["explanation"],
                    "scenario": row["scenario"],
                    "latency_ms": round(elapsed_ms, 3),
                }
            )
            render_progress(f"exp3:{architecture}", completed=row_index, total=total_rows)
        finish_progress()
        metrics_rows.append(
            {
                "experiment": "experiment_03_external_benchmark",
                "model": model,
                "architecture": architecture,
                **compute_classification_metrics(
                    y_true,
                    y_pred,
                    latency_ms_avg=sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0,
                ),
            }
        )

    return predictions, metrics_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run experiment 3 with a local GPU LLM via transformers.")
    parser.add_argument("--model", default=DEFAULT_LOCAL_LLM_MODEL)
    parser.add_argument("--architectures", nargs="+", choices=DEFAULT_ARCHITECTURES, default=list(DEFAULT_ARCHITECTURES))
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    predictions, metrics_rows = run(
        model=args.model,
        architectures=tuple(args.architectures),
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
    )

    model_slug = slugify_model_name(args.model)
    write_csv(OUTPUT_DIR / f"local_llm_experiment_03_{model_slug}_predictions.csv", predictions)
    write_csv(OUTPUT_DIR / f"local_llm_experiment_03_{model_slug}_metrics.csv", metrics_rows)
    write_summary(OUTPUT_DIR / f"local_llm_experiment_03_{model_slug}_summary.md", metrics_rows)
    print(
        f"Wrote {len(predictions)} local LLM experiment 03 predictions and "
        f"{len(metrics_rows)} metric rows for model={args.model}"
    )


if __name__ == "__main__":
    main()
