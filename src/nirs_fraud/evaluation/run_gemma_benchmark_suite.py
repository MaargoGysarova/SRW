from __future__ import annotations

import argparse
import csv
import http.client
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from ..llm.prompts import format_classification_prompt
from ..llm.run_open_source_llm import parse_json_object
from .datasets import ROOT, build_experiment_02_variant_rows, load_experiment_01_rows, load_experiment_03_rows
from .local_llm import build_retry_prompt, normalize_classification_output, slugify_model_name, write_csv
from .metrics import compute_classification_metrics
from .progress import finish_progress, render_progress


OUTPUT_DIR = ROOT / "outputs" / "experiment_04"
DEFAULT_GEMMA_MODEL = "gemma-4-31b-it"
DEFAULT_ARCHITECTURES = ("single_llm", "llm_checklist", "llm_self_check", "llm_ensemble")
DEFAULT_BENCHMARKS = ("experiment_01", "experiment_02", "experiment_03")
TARGET_VARIANTS = ("original", "paraphrase", "subtle", "asr_noise")
DEFAULT_MAX_ATTEMPTS = 4
DEFAULT_PROVIDER_NAME = "Gemma"
DEFAULT_API_KEY_ENV = "GEMINI_API_KEY"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiTransientError(RuntimeError):
    """Temporary provider-side or network failure that should be retried."""


class GeminiFatalError(RuntimeError):
    """Non-retryable provider failure."""


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_checkpoint(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    write_csv(path, rows)


def remove_checkpoint(path: Path) -> None:
    if path.exists():
        path.unlink()


def call_gemini_api(
    prompt: str,
    model: str,
    *,
    base_url: str | None,
    api_key_env: str,
    provider_name: str,
) -> str:
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise GeminiFatalError(
            f"{provider_name} API key is missing. "
            f"Set environment variable {api_key_env} before running the benchmark."
        )

    resolved_base_url = (base_url or DEFAULT_GEMINI_BASE_URL).rstrip("/")
    endpoint = f"{resolved_base_url}/{model}:generateContent?key={urllib.parse.quote(api_key, safe='')}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                ]
            }
        ]
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            raw_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        if exc.code in {401, 403}:
            raise GeminiFatalError(
                f"{provider_name} API request was denied by the platform. "
                "Check key validity, account access, and provider policy restrictions."
            ) from exc
        if exc.code == 404:
            raise GeminiFatalError(
                f"{provider_name} model `{model}` is not available for this API endpoint or account. "
                "Check the exact model name available in your Gemini API project."
            ) from exc
        if exc.code == 429:
            raise GeminiFatalError(
                f"{provider_name} API request failed because the account has no available quota, "
                "hit a billing limit, or exceeded a rate limit. "
                "Check project billing, usage limits, and available credits."
            ) from exc
        if exc.code in {500, 502, 503, 504}:
            raise GeminiTransientError(
                f"{provider_name} API temporary failure HTTP {exc.code}. "
                "Provider returned a transient server error."
            ) from exc
        raise GeminiFatalError(
            f"{provider_name} API request failed with HTTP {exc.code}. "
            f"Response body: {response_body[:500]}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, ConnectionResetError, http.client.RemoteDisconnected) as exc:
        raise GeminiTransientError(
            f"{provider_name} API network error: {exc}"
        ) from exc

    candidates = raw_payload.get("candidates") or []
    if not candidates:
        raise GeminiFatalError(
            f"{provider_name} API returned no candidates. Raw response: {json.dumps(raw_payload, ensure_ascii=False)[:500]}"
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    combined_text = "\n".join(text_parts).strip()
    if not combined_text:
        raise GeminiFatalError(
            f"{provider_name} API returned an empty text response. Raw response: {json.dumps(raw_payload, ensure_ascii=False)[:500]}"
        )
    return combined_text


def classify_text_api(
    *,
    model: str,
    text: str,
    architecture: str,
    base_url: str | None,
    api_key_env: str,
    provider_name: str,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> tuple[dict, float]:
    base_prompt = format_classification_prompt(text, architecture)
    last_error: Exception | None = None
    last_preview = ""

    for attempt_index in range(max_attempts):
        prompt = base_prompt if last_error is None else build_retry_prompt(base_prompt, str(last_error), attempt_index + 1)
        started = time.perf_counter()
        try:
            raw_output = call_gemini_api(
                prompt,
                model,
                base_url=base_url,
                api_key_env=api_key_env,
                provider_name=provider_name,
            )
        except GeminiTransientError as exc:
            last_error = exc
            if attempt_index < max_attempts - 1:
                time.sleep(min(8.0, 2**attempt_index))
                continue
            raise
        except GeminiFatalError:
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        try:
            parsed = parse_json_object(raw_output)
            normalized = normalize_classification_output(parsed)
            return normalized, elapsed_ms
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            last_preview = raw_output[:500].replace("\n", "\\n")

    raise ValueError(
        f"Failed to parse {provider_name} classification output for architecture={architecture} "
        f"after {max_attempts} attempts. Model output preview: {last_preview}"
    ) from last_error


def write_summary_experiment_01(path: Path, metrics_rows: list[dict], provider_name: str) -> None:
    lines = [
        f"# {provider_name} Experiment 1 Summary",
        "",
        "| Model | Architecture | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics_rows:
        lines.append(
            f"| {row['model']} | {row['architecture']} | {row['accuracy']:.3f} | {row['precision_fraud']:.3f} | {row['recall_fraud']:.3f} | {row['f1_fraud']:.3f} | {row['false_positives']} | {row['false_negatives']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_experiment_02(path: Path, metrics_rows: list[dict], provider_name: str) -> None:
    lines = [
        f"# {provider_name} Experiment 2 Summary",
        "",
        "| Model | Architecture | Variant | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics_rows:
        lines.append(
            f"| {row['model']} | {row['architecture']} | {row['variant']} | {row['accuracy']:.3f} | {row['precision_fraud']:.3f} | {row['recall_fraud']:.3f} | {row['f1_fraud']:.3f} | {row['false_positives']} | {row['false_negatives']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_experiment_03(path: Path, metrics_rows: list[dict], provider_name: str) -> None:
    lines = [
        f"# {provider_name} Experiment 3 Summary",
        "",
        "| Model | Architecture | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics_rows:
        lines.append(
            f"| {row['model']} | {row['architecture']} | {row['accuracy']:.3f} | {row['precision_fraud']:.3f} | {row['recall_fraud']:.3f} | {row['f1_fraud']:.3f} | {row['false_positives']} | {row['false_negatives']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_per_architecture_outputs(
    *,
    output_dir: Path,
    prefix: str,
    model_slug: str,
    predictions: list[dict],
    metrics_rows: list[dict],
    summary_writer,
    provider_name: str,
) -> None:
    architectures = sorted({row["architecture"] for row in metrics_rows})
    for architecture in architectures:
        architecture_predictions = [row for row in predictions if row["architecture"] == architecture]
        architecture_metrics = [row for row in metrics_rows if row["architecture"] == architecture]
        write_csv(
            output_dir / f"{prefix}_{model_slug}_{architecture}_predictions.csv",
            architecture_predictions,
        )
        write_csv(
            output_dir / f"{prefix}_{model_slug}_{architecture}_metrics.csv",
            architecture_metrics,
        )
        summary_writer(
            output_dir / f"{prefix}_{model_slug}_{architecture}_summary.md",
            architecture_metrics,
            provider_name,
        )


def run_experiment_01(
    *,
    model: str,
    architectures: tuple[str, ...],
    limit: int | None,
    base_url: str | None,
    api_key_env: str,
    provider_name: str,
    checkpoint_path: Path,
) -> tuple[list[dict], list[dict]]:
    rows = load_experiment_01_rows()
    if limit is not None:
        rows = rows[:limit]

    predictions = read_csv_rows(checkpoint_path)
    metrics_rows: list[dict] = []

    for architecture in architectures:
        architecture_predictions = [row for row in predictions if row["architecture"] == architecture]
        processed_ids = {row["id"] for row in architecture_predictions}
        y_true = [row["true_label"] for row in architecture_predictions]
        y_pred = [row["predicted_label"] for row in architecture_predictions]
        latencies_ms = [float(row["latency_ms"]) for row in architecture_predictions]
        total_rows = len(rows)
        completed_rows = len(processed_ids)
        render_progress(f"exp4:exp1:{architecture}", completed=completed_rows, total=total_rows)
        for row in rows:
            if row["id"] in processed_ids:
                continue
            normalized, elapsed_ms = classify_text_api(
                model=model,
                text=row["text"],
                architecture=architecture,
                base_url=base_url,
                api_key_env=api_key_env,
                provider_name=provider_name,
            )
            y_true.append(row["label"])
            y_pred.append(normalized["label"])
            latencies_ms.append(elapsed_ms)
            predictions.append(
                {
                    "experiment": "experiment_01_internal_synthetic_core",
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
            write_checkpoint(checkpoint_path, predictions)
            completed_rows += 1
            render_progress(f"exp4:exp1:{architecture}", completed=completed_rows, total=total_rows)
        finish_progress()
        metrics_rows.append(
            {
                "experiment": "experiment_01_internal_synthetic_core",
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


def run_experiment_02(
    *,
    model: str,
    architectures: tuple[str, ...],
    limit: int | None,
    base_url: str | None,
    api_key_env: str,
    provider_name: str,
    checkpoint_path: Path,
) -> tuple[list[dict], list[dict]]:
    rows = build_experiment_02_variant_rows(variants=TARGET_VARIANTS[1:])

    predictions = read_csv_rows(checkpoint_path)
    metrics_rows: list[dict] = []

    for architecture in architectures:
        grouped_predictions: dict[str, list[dict]] = {variant: [] for variant in TARGET_VARIANTS}
        for variant in TARGET_VARIANTS:
            subset = [row for row in rows if row["variant"] == variant]
            if limit is not None:
                subset = subset[:limit]
            if not subset:
                continue

            existing_subset_predictions = [
                row
                for row in predictions
                if row["architecture"] == architecture and row["variant"] == variant
            ]
            processed_sample_ids = {row["sample_id"] for row in existing_subset_predictions}
            y_true = [row["true_label"] for row in existing_subset_predictions]
            y_pred = [row["predicted_label"] for row in existing_subset_predictions]
            latencies_ms = [float(row["latency_ms"]) for row in existing_subset_predictions]
            grouped_predictions[variant].extend(
                {
                    "true_label": row["true_label"],
                    "predicted_label": row["predicted_label"],
                    "latency_ms": float(row["latency_ms"]),
                }
                for row in existing_subset_predictions
            )
            total_rows = len(subset)
            completed_rows = len(processed_sample_ids)
            render_progress(f"exp4:exp2:{architecture}:{variant}", completed=completed_rows, total=total_rows)
            for row in subset:
                if row["sample_id"] in processed_sample_ids:
                    continue
                normalized, elapsed_ms = classify_text_api(
                    model=model,
                    text=row["text"],
                    architecture=architecture,
                    base_url=base_url,
                    api_key_env=api_key_env,
                    provider_name=provider_name,
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
                write_checkpoint(checkpoint_path, predictions)
                completed_rows += 1
                render_progress(f"exp4:exp2:{architecture}:{variant}", completed=completed_rows, total=total_rows)
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


def run_experiment_03(
    *,
    model: str,
    architectures: tuple[str, ...],
    limit: int | None,
    base_url: str | None,
    api_key_env: str,
    provider_name: str,
    checkpoint_path: Path,
) -> tuple[list[dict], list[dict]]:
    rows = load_experiment_03_rows()
    if limit is not None:
        rows = rows[:limit]

    predictions = read_csv_rows(checkpoint_path)
    metrics_rows: list[dict] = []

    for architecture in architectures:
        architecture_predictions = [row for row in predictions if row["architecture"] == architecture]
        processed_ids = {row["id"] for row in architecture_predictions}
        y_true = [row["true_label"] for row in architecture_predictions]
        y_pred = [row["predicted_label"] for row in architecture_predictions]
        latencies_ms = [float(row["latency_ms"]) for row in architecture_predictions]
        total_rows = len(rows)
        completed_rows = len(processed_ids)
        render_progress(f"exp4:exp3:{architecture}", completed=completed_rows, total=total_rows)
        for row in rows:
            if row["id"] in processed_ids:
                continue
            normalized, elapsed_ms = classify_text_api(
                model=model,
                text=row["text"],
                architecture=architecture,
                base_url=base_url,
                api_key_env=api_key_env,
                provider_name=provider_name,
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
            write_checkpoint(checkpoint_path, predictions)
            completed_rows += 1
            render_progress(f"exp4:exp3:{architecture}", completed=completed_rows, total=total_rows)
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
    parser = argparse.ArgumentParser(description="Run Gemma via Gemini API across experiments 1, 2, and 3.")
    parser.add_argument("--model", default=DEFAULT_GEMMA_MODEL)
    parser.add_argument("--architectures", nargs="+", choices=DEFAULT_ARCHITECTURES, default=list(DEFAULT_ARCHITECTURES))
    parser.add_argument("--benchmarks", nargs="+", choices=DEFAULT_BENCHMARKS, default=list(DEFAULT_BENCHMARKS))
    parser.add_argument("--limit", type=int, default=None, help="For experiment_02, applies per variant; otherwise per dataset.")
    parser.add_argument("--base-url", default=None, help="Optional override for the Gemini API base URL.")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV, help="Environment variable that stores the Gemini API key.")
    parser.add_argument("--provider-name", default=DEFAULT_PROVIDER_NAME, help="Human-readable provider name for outputs and errors.")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model_slug = slugify_model_name(args.model)
    provider_slug = slugify_model_name(args.provider_name.lower())
    architectures = tuple(args.architectures)

    if "experiment_01" in args.benchmarks:
        output_dir = OUTPUT_DIR / "experiment_01"
        output_dir.mkdir(parents=True, exist_ok=True)
        prefix = f"{provider_slug}_experiment_01"
        checkpoint_path = output_dir / f"{prefix}_{model_slug}_predictions.partial.csv"
        predictions, metrics_rows = run_experiment_01(
            model=args.model,
            architectures=architectures,
            limit=args.limit,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            provider_name=args.provider_name,
            checkpoint_path=checkpoint_path,
        )
        write_csv(output_dir / f"{prefix}_{model_slug}_predictions.csv", predictions)
        write_csv(output_dir / f"{prefix}_{model_slug}_metrics.csv", metrics_rows)
        write_summary_experiment_01(output_dir / f"{prefix}_{model_slug}_summary.md", metrics_rows, args.provider_name)
        write_per_architecture_outputs(
            output_dir=output_dir,
            prefix=prefix,
            model_slug=model_slug,
            predictions=predictions,
            metrics_rows=metrics_rows,
            summary_writer=write_summary_experiment_01,
            provider_name=args.provider_name,
        )
        remove_checkpoint(checkpoint_path)

    if "experiment_02" in args.benchmarks:
        output_dir = OUTPUT_DIR / "experiment_02"
        output_dir.mkdir(parents=True, exist_ok=True)
        prefix = f"{provider_slug}_experiment_02"
        checkpoint_path = output_dir / f"{prefix}_{model_slug}_predictions.partial.csv"
        predictions, metrics_rows = run_experiment_02(
            model=args.model,
            architectures=architectures,
            limit=args.limit,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            provider_name=args.provider_name,
            checkpoint_path=checkpoint_path,
        )
        write_csv(output_dir / f"{prefix}_{model_slug}_predictions.csv", predictions)
        write_csv(output_dir / f"{prefix}_{model_slug}_metrics.csv", metrics_rows)
        write_summary_experiment_02(output_dir / f"{prefix}_{model_slug}_summary.md", metrics_rows, args.provider_name)
        write_per_architecture_outputs(
            output_dir=output_dir,
            prefix=prefix,
            model_slug=model_slug,
            predictions=predictions,
            metrics_rows=metrics_rows,
            summary_writer=write_summary_experiment_02,
            provider_name=args.provider_name,
        )
        remove_checkpoint(checkpoint_path)

    if "experiment_03" in args.benchmarks:
        output_dir = OUTPUT_DIR / "experiment_03"
        output_dir.mkdir(parents=True, exist_ok=True)
        prefix = f"{provider_slug}_experiment_03"
        checkpoint_path = output_dir / f"{prefix}_{model_slug}_predictions.partial.csv"
        predictions, metrics_rows = run_experiment_03(
            model=args.model,
            architectures=architectures,
            limit=args.limit,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            provider_name=args.provider_name,
            checkpoint_path=checkpoint_path,
        )
        write_csv(output_dir / f"{prefix}_{model_slug}_predictions.csv", predictions)
        write_csv(output_dir / f"{prefix}_{model_slug}_metrics.csv", metrics_rows)
        write_summary_experiment_03(output_dir / f"{prefix}_{model_slug}_summary.md", metrics_rows, args.provider_name)
        write_per_architecture_outputs(
            output_dir=output_dir,
            prefix=prefix,
            model_slug=model_slug,
            predictions=predictions,
            metrics_rows=metrics_rows,
            summary_writer=write_summary_experiment_03,
            provider_name=args.provider_name,
        )
        remove_checkpoint(checkpoint_path)

    print(
        f"Wrote Gemma API experiment 04 outputs for provider={args.provider_name}, model={args.model} "
        f"into {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
