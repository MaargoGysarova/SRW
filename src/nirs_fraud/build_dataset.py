from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

LEGACY_SPECS_DIR = ROOT / "data" / "specs"
LEGACY_SEEDS_DIR = ROOT / "data" / "seeds"
LEGACY_EXTERNAL_PATH = ROOT / "data" / "external" / "synthetic_fraud_dialogues_ru_v1.csv"

STAGE_SPECS_DIR = ROOT / "data" / "00_specs"
GENERATOR_DIR = ROOT / "data" / "01_generator"
GENERATOR_SEEDS_DIR = GENERATOR_DIR / "seed_briefs"
GENERATOR_OUTPUTS_DIR = GENERATOR_DIR / "outputs"
AUGMENTATOR_OUTPUTS_DIR = ROOT / "data" / "02_augmentator" / "outputs"
VALIDATOR_REPORTS_DIR = ROOT / "data" / "03_validator" / "reports"
FINAL_DATASET_DIR = ROOT / "data" / "04_final_dataset"
EXTERNAL_RAW_DIR = ROOT / "data" / "05_external_benchmark" / "raw"
EXTERNAL_NORMALIZED_DIR = ROOT / "data" / "05_external_benchmark" / "normalized"
AUDIO_DIR = ROOT / "data" / "06_audio"

INTERNAL_CANDIDATES_PATH = GENERATOR_OUTPUTS_DIR / "internal_generated_candidates_v0.jsonl"
AUGMENTATION_SUBSET_PATH = AUGMENTATOR_OUTPUTS_DIR / "augmentation_subset_v0.jsonl"
EXTERNAL_BENCHMARK_PATH = EXTERNAL_RAW_DIR / "synthetic_fraud_dialogues_ru_v1.csv"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    serialized_rows = []
    for row in rows:
        serialized = {}
        for key, value in row.items():
            serialized[key] = ";".join(value) if isinstance(value, list) else value
        serialized_rows.append(serialized)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serialized_rows[0].keys()))
        writer.writeheader()
        writer.writerows(serialized_rows)


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_external_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    normalized = []
    for row in rows:
        normalized.append(
            {
                "id": row["id"],
                "label": row["label"],
                "scenario": row["scenario"],
                "text": row["text"],
                "signals": [part.strip() for part in row["signals"].split(";") if part.strip()],
                "difficulty": row["difficulty"],
                "source": row["source"],
                "language": row["language"],
                "modality": row["modality"],
            }
        )
    return normalized


def summarize_rows(rows: list[dict]) -> dict:
    label_counts: dict[str, int] = {}
    scenario_counts: dict[str, int] = {}
    for row in rows:
        label_counts[row["label"]] = label_counts.get(row["label"], 0) + 1
        scenario_counts[row["scenario"]] = scenario_counts.get(row["scenario"], 0) + 1
    return {
        "total_examples": len(rows),
        "label_counts": label_counts,
        "scenario_counts": scenario_counts,
    }


def build_manifest(internal_rows: list[dict], augmentation_rows: list[dict], external_rows: list[dict]) -> dict:
    return {
        "project": "nirs_fraud_dialogs",
        "dataset_logic": [
            "LLM-generator",
            "LLM-augmentator",
            "LLM-validator or manual review",
            "final dataset",
        ],
        "internal_synthetic_core": {
            "description": "Accepted output of the internal generator/validator pipeline.",
            "source_path": str(INTERNAL_CANDIDATES_PATH.relative_to(ROOT)),
            "summary": summarize_rows(internal_rows),
        },
        "augmentation_subset": {
            "description": "Robustness subset produced at the augmentator stage.",
            "source_path": str(AUGMENTATION_SUBSET_PATH.relative_to(ROOT)),
            "count": len(augmentation_rows),
        },
        "external_benchmark": {
            "description": "External example dataset used for additional testing and discussion.",
            "source_path": str(EXTERNAL_BENCHMARK_PATH.relative_to(ROOT)) if EXTERNAL_BENCHMARK_PATH.exists() else None,
            "summary": summarize_rows(external_rows) if external_rows else None,
        },
    }


def ensure_stage_dirs() -> None:
    for path in [
        STAGE_SPECS_DIR,
        GENERATOR_SEEDS_DIR,
        GENERATOR_OUTPUTS_DIR,
        AUGMENTATOR_OUTPUTS_DIR,
        VALIDATOR_REPORTS_DIR,
        FINAL_DATASET_DIR,
        EXTERNAL_RAW_DIR,
        EXTERNAL_NORMALIZED_DIR,
        AUDIO_DIR / "real",
        AUDIO_DIR / "synthetic",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def copy_dir_files(source_dir: Path, target_dir: Path) -> None:
    if not source_dir.exists():
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    for path in source_dir.iterdir():
        if path.is_file():
            shutil.copy2(path, target_dir / path.name)


def sync_reference_files() -> None:
    copy_dir_files(LEGACY_SPECS_DIR, STAGE_SPECS_DIR)
    copy_dir_files(LEGACY_SEEDS_DIR, GENERATOR_SEEDS_DIR)
    if LEGACY_EXTERNAL_PATH.exists() and not EXTERNAL_BENCHMARK_PATH.exists():
        shutil.copy2(LEGACY_EXTERNAL_PATH, EXTERNAL_BENCHMARK_PATH)


def require_jsonl(path: Path, stage_name: str) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"{stage_name} input not found: {path}. "
            "Сначала положи данные в соответствующую этапную папку."
        )
    return load_jsonl(path)


def write_validator_report(path: Path, internal_rows: list[dict], augmentation_rows: list[dict], external_rows: list[dict]) -> None:
    report = {
        "stage": "validator",
        "internal_candidate_count": len(internal_rows),
        "augmentation_count": len(augmentation_rows),
        "external_benchmark_count": len(external_rows),
        "accepted_to_final_dataset": len(internal_rows),
        "notes": [
            "build_dataset.py не хранит тексты диалогов внутри кода и читает их из этапных папок.",
            "External benchmark хранится отдельно и не смешивается с internal synthetic core.",
        ],
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ensure_stage_dirs()
    sync_reference_files()

    internal_rows = require_jsonl(INTERNAL_CANDIDATES_PATH, "generator")
    augmentation_rows = require_jsonl(AUGMENTATION_SUBSET_PATH, "augmentator")
    external_rows = load_external_csv(EXTERNAL_BENCHMARK_PATH) if EXTERNAL_BENCHMARK_PATH.exists() else []

    write_jsonl(FINAL_DATASET_DIR / "internal_synthetic_core_v0.jsonl", internal_rows)
    write_csv(FINAL_DATASET_DIR / "internal_synthetic_core_v0.csv", internal_rows)

    if external_rows:
        write_jsonl(EXTERNAL_NORMALIZED_DIR / "external_benchmark_v1.jsonl", external_rows)
        write_csv(EXTERNAL_NORMALIZED_DIR / "external_benchmark_v1.csv", external_rows)

    manifest = build_manifest(internal_rows, augmentation_rows, external_rows)
    (VALIDATOR_REPORTS_DIR / "dataset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_validator_report(
        VALIDATOR_REPORTS_DIR / "validation_report_v0.json",
        internal_rows,
        augmentation_rows,
        external_rows,
    )

    print(
        "Built final dataset from stage files: "
        f"{len(internal_rows)} internal candidates, "
        f"{len(augmentation_rows)} augmentations, "
        f"{len(external_rows)} external benchmark rows."
    )


if __name__ == "__main__":
    main()
