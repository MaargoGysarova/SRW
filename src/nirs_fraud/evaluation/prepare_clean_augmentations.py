from __future__ import annotations

from ..pipeline.validate_dataset import validate_and_write_augmentations


def main() -> None:
    report = validate_and_write_augmentations()
    if report is None:
        print("Augmentation validation skipped: required inputs not found.")
        return
    print(
        f"Prepared clean augmentations: accepted={report['accepted_count']}, "
        f"rejected={report['rejected_count']}"
    )


if __name__ == "__main__":
    main()
