from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GENERATOR_OUTPUTS_PATH = ROOT / "data" / "01_generator" / "outputs" / "internal_generated_candidates_v0.jsonl"

AUDIO_ROOT = ROOT / "data" / "06_audio"
SYNTHETIC_ROOT = AUDIO_ROOT / "synthetic"
REAL_ROOT = AUDIO_ROOT / "real"

SYNTHETIC_MANIFESTS_DIR = SYNTHETIC_ROOT / "manifests"
SYNTHETIC_AUDIO_DIR = SYNTHETIC_ROOT / "audio"
SYNTHETIC_SEGMENTS_DIR = SYNTHETIC_ROOT / "segments"
SYNTHETIC_TRANSCRIPTS_ASR_DIR = SYNTHETIC_ROOT / "transcripts" / "asr"
SYNTHETIC_TRANSCRIPTS_MANUAL_DIR = SYNTHETIC_ROOT / "transcripts" / "manual"
REAL_METADATA_DIR = REAL_ROOT / "metadata"

TARGET_COUNTS = {
    "fraud": 8,
    "suspicious": 4,
    "safe": 8,
}

DEFAULT_VOICE_BY_ROLE = {
    "operator": "ru-RU-DmitryNeural",
    "specialist": "ru-RU-DmitryNeural",
    "manager": "ru-RU-DmitryNeural",
    "investor": "ru-RU-DmitryNeural",
    "courier": "ru-RU-DmitryNeural",
    "follow_up": "ru-RU-DmitryNeural",
    "следователь": "ru-RU-DmitryNeural",
    "сотрудник": "ru-RU-DmitryNeural",
    "клиент": "ru-RU-SvetlanaNeural",
    "пользователь": "ru-RU-SvetlanaNeural",
    "получатель": "ru-RU-SvetlanaNeural",
    "пациент": "ru-RU-SvetlanaNeural",
    "родитель": "ru-RU-SvetlanaNeural",
    "мама": "ru-RU-SvetlanaNeural",
    "подруга": "ru-RU-SvetlanaNeural",
    "друг": "ru-RU-DmitryNeural",
}


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized_rows: list[dict] = []
    for row in rows:
        serialized: dict[str, object] = {}
        for key, value in row.items():
            if isinstance(value, list):
                serialized[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, dict):
                serialized[key] = json.dumps(value, ensure_ascii=False)
            else:
                serialized[key] = value
        serialized_rows.append(serialized)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serialized_rows[0].keys()))
        writer.writeheader()
        writer.writerows(serialized_rows)


def ensure_audio_dirs() -> None:
    for path in [
        SYNTHETIC_MANIFESTS_DIR,
        SYNTHETIC_AUDIO_DIR,
        SYNTHETIC_SEGMENTS_DIR,
        SYNTHETIC_TRANSCRIPTS_ASR_DIR,
        SYNTHETIC_TRANSCRIPTS_MANUAL_DIR,
        REAL_METADATA_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def normalize_role(role: str) -> str:
    cleaned = role.strip().lower()
    cleaned = cleaned.replace("ё", "е")
    return cleaned


def guess_voice(role: str) -> str:
    normalized = normalize_role(role)
    for marker, voice in DEFAULT_VOICE_BY_ROLE.items():
        if marker in normalized:
            return voice
    if normalized in {"оператор", "менеджер", "следователь", "специалист"}:
        return "ru-RU-DmitryNeural"
    return "ru-RU-SvetlanaNeural"


def split_dialogue_segments(text: str) -> list[dict]:
    pattern = re.compile(r"([А-ЯA-ZЁа-яa-z0-9 _-]+):\s*")
    matches = list(pattern.finditer(text))
    if not matches:
        return [{"speaker": "Narrator", "text": text.strip()}] if text.strip() else []

    segments: list[dict] = []
    for index, match in enumerate(matches):
        speaker = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        utterance = text[start:end].strip()
        if utterance:
            segments.append({"speaker": speaker, "text": utterance})
    return segments


def select_diverse_subset(rows: list[dict], label: str, target_count: int) -> list[dict]:
    label_rows = [row for row in rows if row["label"] == label]
    by_scenario: dict[str, list[dict]] = defaultdict(list)
    for row in label_rows:
        by_scenario[row["scenario"]].append(row)

    selected: list[dict] = []
    ordered_scenarios = sorted(by_scenario.keys())
    scenario_index = 0
    while len(selected) < target_count and ordered_scenarios:
        scenario = ordered_scenarios[scenario_index % len(ordered_scenarios)]
        bucket = by_scenario[scenario]
        if bucket:
            selected.append(bucket.pop(0))
        scenario_index += 1
        ordered_scenarios = [item for item in ordered_scenarios if by_scenario[item]]

    if len(selected) != target_count:
        raise ValueError(f"Not enough rows for label={label}. Expected {target_count}, got {len(selected)}")
    return selected


def build_subset(rows: list[dict]) -> list[dict]:
    subset: list[dict] = []
    for label, count in TARGET_COUNTS.items():
        subset.extend(select_diverse_subset(rows, label, count))
    return sorted(subset, key=lambda item: (item["label"], item["scenario"], item["id"]))


def build_synthetic_audio_records(rows: list[dict]) -> list[dict]:
    records: list[dict] = []
    for row in rows:
        audio_id = f"syn_audio_{row['id']}"
        segments = split_dialogue_segments(row["text"])
        enriched_segments = []
        for index, segment in enumerate(segments, start=1):
            voice = guess_voice(segment["speaker"])
            segment_id = f"{audio_id}_seg_{index:02d}"
            enriched_segments.append(
                {
                    "segment_id": segment_id,
                    "speaker": segment["speaker"],
                    "text": segment["text"],
                    "voice": voice,
                    "segment_audio_path": str((SYNTHETIC_SEGMENTS_DIR / f"{segment_id}.mp3").relative_to(ROOT)),
                }
            )

        records.append(
            {
                "audio_id": audio_id,
                "source_id": row["id"],
                "label": row["label"],
                "scenario": row["scenario"],
                "difficulty": row["difficulty"],
                "text": row["text"],
                "signals": row.get("signals", []),
                "segment_count": len(enriched_segments),
                "segments": enriched_segments,
                "audio_output_path": str((SYNTHETIC_AUDIO_DIR / f"{audio_id}.mp3").relative_to(ROOT)),
                "wav_output_path": str((SYNTHETIC_AUDIO_DIR / f"{audio_id}.wav").relative_to(ROOT)),
                "asr_transcript_path": str((SYNTHETIC_TRANSCRIPTS_ASR_DIR / f"{audio_id}.txt").relative_to(ROOT)),
                "manual_transcript_path": str((SYNTHETIC_TRANSCRIPTS_MANUAL_DIR / f"{audio_id}.txt").relative_to(ROOT)),
                "notes": "Synthetic TTS example for audio -> ASR -> LLM experiment.",
            }
        )
    return records


def build_tts_jobs(audio_records: list[dict]) -> list[dict]:
    jobs: list[dict] = []
    for record in audio_records:
        for segment in record["segments"]:
            jobs.append(
                {
                    "job_id": segment["segment_id"],
                    "audio_id": record["audio_id"],
                    "source_id": record["source_id"],
                    "label": record["label"],
                    "scenario": record["scenario"],
                    "speaker": segment["speaker"],
                    "voice": segment["voice"],
                    "text": segment["text"],
                    "output_path": segment["segment_audio_path"],
                }
            )
    return jobs


def build_asr_eval_template(audio_records: list[dict]) -> list[dict]:
    template: list[dict] = []
    for record in audio_records:
        template.append(
            {
                "audio_id": record["audio_id"],
                "source_id": record["source_id"],
                "label": record["label"],
                "scenario": record["scenario"],
                "original_text": record["text"],
                "asr_transcript_path": record["asr_transcript_path"],
                "manual_transcript_path": record["manual_transcript_path"],
                "predicted_label_original": "",
                "predicted_label_asr": "",
                "asr_quality": "",
                "notes": "",
            }
        )
    return template


def build_real_audio_metadata_template() -> list[dict]:
    rows: list[dict] = []
    for index in range(1, 5):
        audio_id = f"real_audio_{index:03d}"
        rows.append(
            {
                "audio_id": audio_id,
                "source_file": f"data/06_audio/real/{audio_id}.mp3",
                "source_url_or_note": "",
                "label": "fraud",
                "scenario": "",
                "duration_sec": "",
                "asr_transcript_path": f"data/06_audio/real/metadata/{audio_id}_asr.txt",
                "manual_transcript_path": f"data/06_audio/real/metadata/{audio_id}_manual.txt",
                "predicted_label_asr": "",
                "predicted_label_manual": "",
                "asr_quality": "",
                "detected_signals": "[]",
                "notes": "Open-source real audio sample for qualitative validation.",
            }
        )
    return rows


def build_summary(audio_records: list[dict], tts_jobs: list[dict]) -> dict:
    label_counts: dict[str, int] = defaultdict(int)
    scenario_counts: dict[str, int] = defaultdict(int)
    for record in audio_records:
        label_counts[record["label"]] += 1
        scenario_counts[record["scenario"]] += 1
    return {
        "stage": "audio",
        "synthetic_audio_subset_count": len(audio_records),
        "tts_segment_jobs_count": len(tts_jobs),
        "label_counts": dict(label_counts),
        "scenario_counts": dict(scenario_counts),
        "target_counts": TARGET_COUNTS,
        "notes": [
            "Synthetic audio subset is intended for TTS -> ASR -> LLM evaluation.",
            "Real audio is tracked separately as qualitative validation only.",
        ],
    }


def main() -> None:
    ensure_audio_dirs()
    rows = load_jsonl(GENERATOR_OUTPUTS_PATH)
    subset = build_subset(rows)
    audio_records = build_synthetic_audio_records(subset)
    tts_jobs = build_tts_jobs(audio_records)
    asr_template = build_asr_eval_template(audio_records)
    real_audio_template = build_real_audio_metadata_template()
    summary = build_summary(audio_records, tts_jobs)

    write_jsonl(SYNTHETIC_MANIFESTS_DIR / "synthetic_audio_subset_v0.jsonl", audio_records)
    write_csv(SYNTHETIC_MANIFESTS_DIR / "synthetic_audio_subset_v0.csv", audio_records)
    write_jsonl(SYNTHETIC_MANIFESTS_DIR / "synthetic_tts_jobs_v0.jsonl", tts_jobs)
    write_jsonl(SYNTHETIC_MANIFESTS_DIR / "synthetic_asr_eval_template_v0.jsonl", asr_template)
    write_jsonl(REAL_METADATA_DIR / "real_audio_metadata_template_v0.jsonl", real_audio_template)
    (SYNTHETIC_MANIFESTS_DIR / "audio_manifest_summary_v0.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "Built audio manifests: "
        f"{len(audio_records)} synthetic dialogue records, "
        f"{len(tts_jobs)} TTS segment jobs."
    )


if __name__ == "__main__":
    main()

