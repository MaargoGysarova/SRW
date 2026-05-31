from __future__ import annotations

import json
from pathlib import Path

from .experiment_design import architectures_as_json as experiment_architectures_as_json, experiments_as_json
from .metrics import metrics_as_json
from .taxonomy import scenarios_as_json, signals_as_json


ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = ROOT / "data" / "00_specs"


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    write_json(SPECS_DIR / "scenario_catalog.json", scenarios_as_json())
    write_json(SPECS_DIR / "signal_catalog.json", signals_as_json())
    write_json(SPECS_DIR / "architecture_catalog.json", experiment_architectures_as_json())
    write_json(SPECS_DIR / "metrics_catalog.json", metrics_as_json())
    write_json(SPECS_DIR / "experiment_catalog.json", experiments_as_json())
    print(f"Exported taxonomy files to {SPECS_DIR}")


if __name__ == "__main__":
    main()
