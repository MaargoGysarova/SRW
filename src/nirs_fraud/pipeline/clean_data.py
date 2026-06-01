from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

TO_DELETE = [
    ROOT / "data" / "01_generator" / "outputs" / "internal_generated_candidates_v0.csv",
    ROOT / "data" / "01_generator" / "outputs" / "internal_generated_candidates_v0.jsonl",
    ROOT / "data" / "01_generator" / "requests" / "generator_requests_v0.jsonl",
    ROOT / "data" / "02_augmentator" / "outputs" / "augmentation_subset_v0.jsonl",
    ROOT / "data" / "02_augmentator" / "requests" / "augmentator_requests_v0.jsonl",
    ROOT / "data" / "03_validator" / "outputs" / "validator_decisions_v0.jsonl",
    ROOT / "data" / "03_validator" / "requests" / "validator_requests_v0.jsonl",
    ROOT / "data" / "03_validator" / "reports" / "dataset_manifest.json",
    ROOT / "data" / "03_validator" / "reports" / "validation_report_v0.json",
    ROOT / "data" / "04_final_dataset" / "internal_synthetic_core_v0.csv",
    ROOT / "data" / "04_final_dataset" / "internal_synthetic_core_v0.jsonl",
    ROOT / "data" / "05_external_benchmark" / "normalized" / "external_benchmark_v1.csv",
    ROOT / "data" / "05_external_benchmark" / "normalized" / "external_benchmark_v1.jsonl",
    ROOT / "data" / "external" / "synthetic_fraud_dialogues_ru_v1.csv",
    ROOT / "data" / "raw" / "synthetic_fraud_dialogues_ru_v1.csv",
    ROOT / "data" / "seeds" / "generation_seed_briefs.jsonl",
    ROOT / "data" / "specs" / "dataset_plan.json",
    ROOT / "data" / "specs" / "scenario_catalog.json",
    ROOT / "data" / "specs" / "signal_catalog.json",
    ROOT / "data" / "generated" / "augmentation_dataset.jsonl",
    ROOT / "data" / "generated" / "main_dataset.csv",
    ROOT / "data" / "generated" / "main_dataset.jsonl",
    ROOT / "data" / "final" / "augmentation_subset_v0.jsonl",
    ROOT / "data" / "final" / "dataset_manifest.json",
    ROOT / "data" / "final" / "external_benchmark_v1.csv",
    ROOT / "data" / "final" / "external_benchmark_v1.jsonl",
    ROOT / "data" / "final" / "internal_synthetic_core_v0.csv",
    ROOT / "data" / "final" / "internal_synthetic_core_v0.jsonl",
    ROOT / "outputs" / "metrics.csv",
    ROOT / "outputs" / "predictions.csv",
    ROOT / "outputs" / "summary.md",
]

DIRS_TO_PRUNE = [
    ROOT / "data" / "audio" / "real",
    ROOT / "data" / "audio" / "synthetic",
    ROOT / "data" / "audio",
    ROOT / "data" / "external",
    ROOT / "data" / "generated",
    ROOT / "data" / "final",
    ROOT / "data" / "intermediate",
    ROOT / "data" / "processed",
    ROOT / "data" / "raw",
    ROOT / "data" / "specs",
    ROOT / "data" / "seeds",
]


def main() -> None:
    removed_files = 0
    for path in TO_DELETE:
        if path.exists():
            path.unlink()
            removed_files += 1

    removed_dirs = 0
    for path in DIRS_TO_PRUNE:
        if path.exists() and path.is_dir() and not any(path.iterdir()):
            path.rmdir()
            removed_dirs += 1

    print(f"Removed {removed_files} generated files and pruned {removed_dirs} empty directories.")


if __name__ == "__main__":
    main()
