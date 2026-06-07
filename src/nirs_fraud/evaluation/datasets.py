from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

GENERATOR_INPUT_PATH = ROOT / "data" / "01_generator" / "outputs" / "internal_generated_candidates_v0.jsonl"
RAW_AUGMENTATION_INPUT_PATH = ROOT / "data" / "02_augmentator" / "outputs" / "augmentation_subset_v0.jsonl"
CLEAN_AUGMENTATION_INPUT_PATH = ROOT / "data" / "02_augmentator" / "outputs" / "augmentation_subset_clean_v1.jsonl"
FINAL_INTERNAL_DATASET_PATH = ROOT / "data" / "04_final_dataset" / "experiment_01_internal_synthetic_core_v0.jsonl"
FINAL_AUGMENTATION_DATASET_PATH = ROOT / "data" / "04_final_dataset" / "experiment_02_validated_augmentation_subset_v1.jsonl"
EXTERNAL_BENCHMARK_PATH = ROOT / "data" / "05_external_benchmark" / "normalized" / "external_benchmark_v1.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def require_jsonl(path: Path, label: str) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"{label} file not found: {path}")
    return load_jsonl(path)


def load_experiment_01_rows() -> list[dict]:
    dataset_path = FINAL_INTERNAL_DATASET_PATH if FINAL_INTERNAL_DATASET_PATH.exists() else GENERATOR_INPUT_PATH
    return require_jsonl(dataset_path, "internal synthetic dataset")


def build_experiment_02_variant_rows(
    *,
    variants: tuple[str, ...] = ("paraphrase", "subtle", "asr_noise"),
) -> list[dict]:
    original_rows = load_experiment_01_rows()
    if FINAL_AUGMENTATION_DATASET_PATH.exists():
        augmentation_path = FINAL_AUGMENTATION_DATASET_PATH
    else:
        augmentation_path = CLEAN_AUGMENTATION_INPUT_PATH if CLEAN_AUGMENTATION_INPUT_PATH.exists() else RAW_AUGMENTATION_INPUT_PATH
    augmentation_rows = require_jsonl(augmentation_path, "augmentation dataset")
    originals_by_id = {row["id"]: row for row in original_rows}

    combined: list[dict] = []
    for aug in augmentation_rows:
        augmentation_type = aug["augmentation_type"]
        if augmentation_type not in variants:
            continue
        base = originals_by_id.get(aug["base_id"])
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
                "variant": augmentation_type,
                "sample_id": aug["id"],
                "base_id": base["id"],
                "label": aug["label"],
                "scenario": base["scenario"],
                "text": aug["text"],
            }
        )

    deduped: dict[tuple[str, str], dict] = {}
    for row in combined:
        deduped[(row["variant"], row["sample_id"])] = row
    return list(deduped.values())


def load_experiment_03_rows() -> list[dict]:
    return require_jsonl(EXTERNAL_BENCHMARK_PATH, "external benchmark")
