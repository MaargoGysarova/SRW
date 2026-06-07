from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TTS_JOBS_PATH = ROOT / "data" / "06_audio" / "synthetic" / "manifests" / "synthetic_tts_jobs_v0.jsonl"
OUTPUT_SCRIPT_PATH = ROOT / "data" / "06_audio" / "synthetic" / "manifests" / "run_edge_tts_v0.sh"


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_command(job: dict) -> str:
    output_path = ROOT / job["output_path"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return (
        "edge-tts "
        f"--voice {shlex.quote(job['voice'])} "
        f"--text {shlex.quote(job['text'])} "
        f"--write-media {shlex.quote(str(output_path))}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export edge-tts commands for the synthetic audio subset.")
    parser.add_argument("--jobs-path", default=str(TTS_JOBS_PATH))
    parser.add_argument("--output-script", default=str(OUTPUT_SCRIPT_PATH))
    args = parser.parse_args()

    jobs_path = Path(args.jobs_path)
    output_script = Path(args.output_script)
    jobs = load_jsonl(jobs_path)

    lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    for job in jobs:
        lines.append(build_command(job))

    output_script.parent.mkdir(parents=True, exist_ok=True)
    output_script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    output_script.chmod(0o755)
    print(f"Exported {len(jobs)} edge-tts commands to {output_script}")


if __name__ == "__main__":
    main()
