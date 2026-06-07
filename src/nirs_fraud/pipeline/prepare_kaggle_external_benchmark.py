from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RAW_INPUT_PATH = ROOT / "data" / "05_external_benchmark" / "raw" / "kaggle_scam_non_scam_ru_subset.csv"
NORMALIZED_JSONL_PATH = ROOT / "data" / "05_external_benchmark" / "normalized" / "kaggle_external_benchmark_v1.jsonl"
NORMALIZED_CSV_PATH = ROOT / "data" / "05_external_benchmark" / "normalized" / "kaggle_external_benchmark_v1.csv"
GENERIC_NORMALIZED_JSONL_PATH = ROOT / "data" / "05_external_benchmark" / "normalized" / "external_benchmark_v1.jsonl"
GENERIC_NORMALIZED_CSV_PATH = ROOT / "data" / "05_external_benchmark" / "normalized" / "external_benchmark_v1.csv"

REQUIRED_COLUMNS = {
    "id",
    "label",
    "original_text",
    "text_ru",
    "scenario",
    "signals",
    "difficulty",
}


def load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return []
    missing = REQUIRED_COLUMNS.difference(rows[0].keys())
    if missing:
        raise ValueError(f"Missing required columns in {path.name}: {sorted(missing)}")
    return rows


def normalize_rows(rows: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for row in rows:
        normalized.append(
            {
                "id": row["id"].strip(),
                "source": row.get("source", "kaggle_scam_non_scam").strip() or "kaggle_scam_non_scam",
                "original_language": row.get("original_language", "en").strip() or "en",
                "language": row.get("language", "ru").strip() or "ru",
                "translation_type": row.get("translation_type", "machine_translated").strip() or "machine_translated",
                "label": row["label"].strip(),
                "original_text": row["original_text"].strip(),
                "text": row["text_ru"].strip(),
                "text_ru": row["text_ru"].strip(),
                "scenario": row["scenario"].strip(),
                "signals": [part.strip() for part in row["signals"].split(";") if part.strip()],
                "difficulty": row.get("difficulty", "easy").strip() or "easy",
                "source_type": "external_benchmark",
                "modality": row.get("modality", "text").strip() or "text",
            }
        )
    return normalized


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized_rows = []
    for row in rows:
        serialized_rows.append(
            {
                **row,
                "signals": ";".join(row["signals"]),
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serialized_rows[0].keys()))
        writer.writeheader()
        writer.writerows(serialized_rows)


def main() -> None:
    if not RAW_INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Raw Kaggle subset not found: {RAW_INPUT_PATH}. "
            "Сначала заполни шаблон kaggle_scam_non_scam_ru_subset.csv."
        )
    rows = load_csv(RAW_INPUT_PATH)
    normalized = normalize_rows(rows)
    write_jsonl(NORMALIZED_JSONL_PATH, normalized)
    write_csv(NORMALIZED_CSV_PATH, normalized)
    write_jsonl(GENERIC_NORMALIZED_JSONL_PATH, normalized)
    write_csv(GENERIC_NORMALIZED_CSV_PATH, normalized)
    print(f"Prepared Kaggle external benchmark: {len(normalized)} rows")


if __name__ == "__main__":
    main()
