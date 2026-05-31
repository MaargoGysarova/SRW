from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = ROOT / "data" / "00_specs"
FINAL_DIR = ROOT / "data" / "04_final_dataset"
EXTERNAL_DIR = ROOT / "data" / "05_external_benchmark" / "normalized"

VALID_LABELS = {"fraud", "suspicious", "safe"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
REQUIRED_FIELDS = {"id", "label", "scenario", "text", "signals", "difficulty", "source", "language", "modality"}


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


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


def main() -> None:
    targets = [
        FINAL_DIR / "internal_synthetic_core_v0.jsonl",
        EXTERNAL_DIR / "external_benchmark_v1.jsonl",
    ]
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
