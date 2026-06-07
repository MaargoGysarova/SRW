from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SPECS_DIR = ROOT / "data" / "00_specs"
FINAL_DIR = ROOT / "data" / "04_final_dataset"
EXTERNAL_DIR = ROOT / "data" / "05_external_benchmark" / "normalized"
GENERATOR_OUTPUTS_DIR = ROOT / "data" / "01_generator" / "outputs"
AUGMENTATOR_OUTPUTS_DIR = ROOT / "data" / "02_augmentator" / "outputs"
AUGMENTATOR_REPORTS_DIR = ROOT / "data" / "02_augmentator" / "reports"

GENERATOR_INPUT_PATH = GENERATOR_OUTPUTS_DIR / "internal_generated_candidates_v0.jsonl"
RAW_AUGMENTATION_INPUT_PATH = AUGMENTATOR_OUTPUTS_DIR / "augmentation_subset_v0.jsonl"
CLEAN_AUGMENTATION_OUTPUT_PATH = AUGMENTATOR_OUTPUTS_DIR / "augmentation_subset_clean_v1.jsonl"
REJECTED_AUGMENTATION_OUTPUT_PATH = AUGMENTATOR_OUTPUTS_DIR / "augmentation_subset_rejected_v1.jsonl"
AUGMENTATION_REPORT_PATH = AUGMENTATOR_REPORTS_DIR / "augmentation_cleaning_report_v1.json"

VALID_LABELS = {"fraud", "suspicious", "safe"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
REQUIRED_FIELDS = {"id", "label", "scenario", "text", "signals", "difficulty", "source", "language", "modality"}
SIMILARITY_THRESHOLDS = {
    "paraphrase": 0.94,
    "subtle": 0.96,
    "scenario_variation": 0.94,
    "asr_noise": 0.995,
}


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_catalog_ids(path: Path) -> set[str]:
    payload = load_json(path)
    if isinstance(payload, dict):
        values = payload.get("scenarios") or payload.get("signals") or []
        return {item["id"] for item in values}
    return {item["id"] for item in payload}


def validate_record(record: dict, valid_scenarios: set[str], valid_signals: set[str], strict_taxonomy: bool) -> list[str]:
    errors = []
    missing = REQUIRED_FIELDS.difference(record.keys())
    if missing:
        errors.append(f"missing_fields={sorted(missing)}")
        return errors
    if record["label"] not in VALID_LABELS:
        errors.append(f"invalid_label={record['label']}")
    if record["difficulty"] not in VALID_DIFFICULTIES:
        errors.append(f"invalid_difficulty={record['difficulty']}")
    if strict_taxonomy and record["scenario"] not in valid_scenarios:
        errors.append(f"unknown_scenario={record['scenario']}")
    if not isinstance(record["signals"], list):
        errors.append("signals_not_list")
    elif strict_taxonomy:
        unknown = [signal for signal in record["signals"] if signal not in valid_signals]
        if unknown:
            errors.append(f"unknown_signals={unknown}")
    if not str(record["text"]).strip():
        errors.append("empty_text")
    if record["language"] != "ru":
        errors.append(f"unexpected_language={record['language']}")
    if record["modality"] != "text":
        errors.append(f"unexpected_modality={record['modality']}")
    return errors


def validate_dataset(path: Path) -> tuple[int, list[str]]:
    valid_scenarios = load_catalog_ids(SPECS_DIR / "scenario_catalog.json")
    valid_signals = load_catalog_ids(SPECS_DIR / "signal_catalog.json")
    rows = load_jsonl(path)
    issues = []
    strict_taxonomy = "internal_synthetic_core" in path.name
    for row in rows:
        row_errors = validate_record(row, valid_scenarios, valid_signals, strict_taxonomy)
        if row_errors:
            issues.append(f"{row['id']}: {'; '.join(row_errors)}")
    return len(rows), issues


def similarity_ratio(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def clean_augmentation_rows(base_rows: list[dict], augmentation_rows: list[dict]) -> tuple[list[dict], list[dict], dict]:
    originals_by_id = {row["id"]: row for row in base_rows}
    accepted: list[dict] = []
    rejected: list[dict] = []

    for row in augmentation_rows:
        base = originals_by_id.get(row["base_id"])
        if base is None:
            rejected.append({**row, "_reject_reason": "missing_base_record"})
            continue

        source_text = base["text"].strip()
        aug_text = row["text"].strip()
        aug_type = row["augmentation_type"]
        similarity = similarity_ratio(source_text, aug_text)
        threshold = SIMILARITY_THRESHOLDS.get(aug_type, 1.0)

        reject_reason = None
        if not aug_text:
            reject_reason = "empty_text"
        elif aug_type in {"paraphrase", "subtle", "scenario_variation"} and aug_text == source_text:
            reject_reason = "exact_duplicate"
        elif aug_type == "asr_noise" and aug_text == source_text:
            reject_reason = "asr_noise_exact_duplicate"
        elif similarity > threshold:
            reject_reason = f"too_similar_{aug_type}"

        if reject_reason is not None:
            rejected.append(
                {
                    **row,
                    "_reject_reason": reject_reason,
                    "_base_id": base["id"],
                    "_similarity": round(similarity, 4),
                }
            )
            continue

        accepted.append({**row, "_similarity": round(similarity, 4)})

    report = {
        "raw_count": len(augmentation_rows),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted_by_type": {
            aug_type: sum(1 for row in accepted if row["augmentation_type"] == aug_type)
            for aug_type in sorted({row["augmentation_type"] for row in augmentation_rows})
        },
        "rejected_by_reason": {
            reason: sum(1 for row in rejected if row["_reject_reason"] == reason)
            for reason in sorted({row["_reject_reason"] for row in rejected})
        },
    }
    return accepted, rejected, report


def validate_and_write_augmentations() -> dict | None:
    if not GENERATOR_INPUT_PATH.exists() or not RAW_AUGMENTATION_INPUT_PATH.exists():
        return None

    base_rows = load_jsonl(GENERATOR_INPUT_PATH)
    augmentation_rows = load_jsonl(RAW_AUGMENTATION_INPUT_PATH)
    accepted, rejected, report = clean_augmentation_rows(base_rows, augmentation_rows)

    write_jsonl(CLEAN_AUGMENTATION_OUTPUT_PATH, accepted)
    write_jsonl(REJECTED_AUGMENTATION_OUTPUT_PATH, rejected)
    AUGMENTATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUGMENTATION_REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    targets = [
        FINAL_DIR / "internal_synthetic_core_v0.jsonl",
        EXTERNAL_DIR / "external_benchmark_v1.jsonl",
    ]

    augmentation_report = validate_and_write_augmentations()
    if augmentation_report is not None:
        print(
            "augmentation_subset_v0.jsonl: "
            f"accepted={augmentation_report['accepted_count']}, "
            f"rejected={augmentation_report['rejected_count']}"
        )

    for target in targets:
        if not target.exists():
            print(f"SKIP {target.name}: file not found")
            continue
        total, issues = validate_dataset(target)
        if issues:
            print(f"{target.name}: {len(issues)} problematic rows out of {total}")
            for issue in issues[:20]:
                print(f"  - {issue}")
        else:
            print(f"{target.name}: OK ({total} rows)")


if __name__ == "__main__":
    main()
