from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from ..evaluation.metrics import compute_classification_metrics
from .prompts import format_classification_prompt
from .run_open_source_llm import ensure_list, ensure_string, parse_json_object


ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = ROOT / "data" / "04_final_dataset" / "internal_synthetic_core_v0.jsonl"
OUTPUT_DIR = ROOT / "outputs"

DEFAULT_MODEL = "gpt-5.2"
# export OPENAI_API_KEY="твой_ключ"

def load_jsonl(path: Path) -> list[dict]:
    import json

    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def slugify_model_name(model: str) -> str:
    return model.replace("/", "_").replace(":", "_").replace(".", "_")


def normalize_classification_output(parsed: dict) -> dict:
    fraud_score_raw = parsed.get("fraud_score", 0.0)
    try:
        fraud_score = float(fraud_score_raw)
    except (TypeError, ValueError):
        fraud_score = 0.0
    fraud_score = max(0.0, min(1.0, fraud_score))
    return {
        "label": ensure_string(parsed.get("label"), "suspicious"),
        "fraud_score": round(fraud_score, 3),
        "signals": ensure_list(parsed.get("signals")),
        "explanation": ensure_string(parsed.get("explanation")),
    }


def call_openai(prompt: str, model: str):
    from openai import OpenAI

    client = OpenAI()
    return client.responses.create(model=model, input=prompt)


def run(
    *,
    architecture: str,
    model: str,
    limit: int | None,
) -> tuple[list[dict], list[dict]]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset file not found: {DATASET_PATH}. "
            "Сначала нужно собрать internal synthetic core."
        )

    rows = load_jsonl(DATASET_PATH)
    if limit is not None:
        rows = rows[:limit]

    predictions = []
    y_true = []
    y_pred = []
    latencies_ms = []

    for row in rows:
        prompt = format_classification_prompt(row["text"], architecture)
        started = time.perf_counter()
        response = call_openai(prompt, model)
        elapsed_ms = (time.perf_counter() - started) * 1000
        parsed = parse_json_object(response.output_text)
        normalized = normalize_classification_output(parsed)

        y_true.append(row["label"])
        y_pred.append(normalized["label"])
        latencies_ms.append(elapsed_ms)

        predictions.append(
            {
                "model": model,
                "architecture": architecture,
                "id": row["id"],
                "true_label": row["label"],
                "predicted_label": normalized["label"],
                "fraud_score": normalized["fraud_score"],
                "predicted_signals": "|".join(normalized["signals"]),
                "explanation": normalized["explanation"],
                "latency_ms": round(elapsed_ms, 3),
                "scenario": row["scenario"],
            }
        )

    metrics_rows = [
        {
            "model": model,
            "architecture": architecture,
            **compute_classification_metrics(
                y_true,
                y_pred,
                latency_ms_avg=sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0,
            ),
        }
    ]
    return predictions, metrics_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run experiment 1 with a large OpenAI model via the Responses API.")
    parser.add_argument("--architecture", choices=["single_llm", "llm_checklist", "llm_self_check", "llm_ensemble"], default="single_llm")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    predictions, metrics_rows = run(
        architecture=args.architecture,
        model=args.model,
        limit=args.limit,
    )

    model_slug = slugify_model_name(args.model)
    write_csv(OUTPUT_DIR / f"openai_{args.architecture}_{model_slug}_predictions.csv", predictions)
    write_csv(OUTPUT_DIR / f"openai_{args.architecture}_{model_slug}_metrics.csv", metrics_rows)
    print(
        f"Wrote {len(predictions)} predictions and {len(metrics_rows)} metrics rows "
        f"for architecture={args.architecture}, model={args.model}"
    )


if __name__ == "__main__":
    main()
