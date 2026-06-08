from __future__ import annotations

import argparse
from pathlib import Path

from .datasets import ROOT, build_experiment_02_variant_rows
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


OUTPUT_DIR = ROOT / "outputs" / "experiment_02"
DEFAULT_ARCHITECTURES = ("single_llm", "llm_checklist", "llm_self_check", "llm_ensemble")
TARGET_VARIANTS = ("original", "paraphrase", "subtle", "asr_noise")


def write_summary(path: Path, metrics_rows: list[dict]) -> None:
    lines = [
        "# Local LLM Experiment 2 Summary",
        "",
        "| Model | Architecture | Variant | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics_rows:
        lines.append(
            f"| {row['model']} | {row['architecture']} | {row['variant']} | {row['accuracy']:.3f} | {row['precision_fraud']:.3f} | {row['recall_fraud']:.3f} | {row['f1_fraud']:.3f} | {row['false_positives']} | {row['false_negatives']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_per_architecture_outputs(output_dir: Path, model_slug: str, predictions: list[dict], metrics_rows: list[dict]) -> None:
    architectures = sorted({row["architecture"] for row in metrics_rows})
    for architecture in architectures:
        architecture_predictions = [row for row in predictions if row["architecture"] == architecture]
        architecture_metrics = [row for row in metrics_rows if row["architecture"] == architecture]
        write_csv(
            output_dir / f"local_llm_experiment_02_{model_slug}_{architecture}_predictions.csv",
            architecture_predictions,
        )
        write_csv(
            output_dir / f"local_llm_experiment_02_{model_slug}_{architecture}_metrics.csv",
            architecture_metrics,
        )
        write_summary(
            output_dir / f"local_llm_experiment_02_{model_slug}_{architecture}_summary.md",
            architecture_metrics,
        )


def run(
    *,
    model: str,
    architectures: tuple[str, ...],
    max_new_tokens: int,
    temperature: float,
) -> tuple[list[dict], list[dict]]:
    rows = build_experiment_02_variant_rows(variants=TARGET_VARIANTS[1:])
    backend = TransformersClassificationBackend(
        model_name=model,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
    )

    predictions: list[dict] = []
    metrics_rows: list[dict] = []

    for architecture in architectures:
        grouped_predictions: dict[str, list[dict]] = {variant: [] for variant in TARGET_VARIANTS}
        for variant in TARGET_VARIANTS:
            subset = [row for row in rows if row["variant"] == variant]
            if not subset:
                continue
            y_true: list[str] = []
            y_pred: list[str] = []
            latencies_ms: list[float] = []
            total_rows = len(subset)
            render_progress(f"exp2:{architecture}:{variant}", completed=0, total=total_rows)
            for row_index, row in enumerate(subset, start=1):
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
                        "experiment": "experiment_02_augmentation_robustness",
                        "model": model,
                        "architecture": architecture,
                        "variant": variant,
                        "sample_id": row["sample_id"],
                        "base_id": row["base_id"],
                        "true_label": row["label"],
                        "predicted_label": normalized["label"],
                        "fraud_score": normalized["fraud_score"],
                        "predicted_signals": "|".join(normalized["signals"]),
                        "explanation": normalized["explanation"],
                        "scenario": row["scenario"],
                        "latency_ms": round(elapsed_ms, 3),
                    }
                )
                grouped_predictions[variant].append(
                    {
                        "true_label": row["label"],
                        "predicted_label": normalized["label"],
                        "latency_ms": elapsed_ms,
                    }
                )
                render_progress(f"exp2:{architecture}:{variant}", completed=row_index, total=total_rows)
            finish_progress()
            metrics_rows.append(
                {
                    "experiment": "experiment_02_augmentation_robustness",
                    "model": model,
                    "architecture": architecture,
                    "variant": variant,
                    **compute_classification_metrics(
                        y_true,
                        y_pred,
                        latency_ms_avg=sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0,
                    ),
                }
            )

        augmented_rows = []
        all_rows = []
        for variant_name, records in grouped_predictions.items():
            if variant_name != "original":
                augmented_rows.extend(records)
            all_rows.extend(records)

        if augmented_rows:
            metrics_rows.append(
                {
                    "experiment": "experiment_02_augmentation_robustness",
                    "model": model,
                    "architecture": architecture,
                    "variant": "all_augmented",
                    **compute_classification_metrics(
                        [row["true_label"] for row in augmented_rows],
                        [row["predicted_label"] for row in augmented_rows],
                        latency_ms_avg=(
                            sum(row["latency_ms"] for row in augmented_rows) / len(augmented_rows)
                            if augmented_rows
                            else 0.0
                        ),
                    ),
                }
            )

        if all_rows:
            metrics_rows.append(
                {
                    "experiment": "experiment_02_augmentation_robustness",
                    "model": model,
                    "architecture": architecture,
                    "variant": "all_variants",
                    **compute_classification_metrics(
                        [row["true_label"] for row in all_rows],
                        [row["predicted_label"] for row in all_rows],
                        latency_ms_avg=(
                            sum(row["latency_ms"] for row in all_rows) / len(all_rows)
                            if all_rows
                            else 0.0
                        ),
                    ),
                }
            )

    return predictions, metrics_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run experiment 2 with a local GPU LLM via transformers.")
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
    write_csv(OUTPUT_DIR / f"local_llm_experiment_02_{model_slug}_predictions.csv", predictions)
    write_csv(OUTPUT_DIR / f"local_llm_experiment_02_{model_slug}_metrics.csv", metrics_rows)
    write_summary(OUTPUT_DIR / f"local_llm_experiment_02_{model_slug}_summary.md", metrics_rows)
    write_per_architecture_outputs(OUTPUT_DIR, model_slug, predictions, metrics_rows)
    print(
        f"Wrote {len(predictions)} local LLM experiment 02 predictions and "
        f"{len(metrics_rows)} metric rows for model={args.model}"
    )


if __name__ == "__main__":
    main()
