from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

from ..catalog.taxonomy import scenario_ids, signal_ids
from .prompts import format_augmentator_prompt, format_generator_prompt, format_validator_prompt


ROOT = Path(__file__).resolve().parents[3]
GENERATOR_SEEDS_PATH = ROOT / "data" / "01_generator" / "seed_briefs" / "generation_seed_briefs.jsonl"
GENERATOR_REQUESTS_DIR = ROOT / "data" / "01_generator" / "requests"
GENERATOR_OUTPUTS_DIR = ROOT / "data" / "01_generator" / "outputs"
GENERATOR_FAILED_DIR = ROOT / "data" / "01_generator" / "failed"
AUGMENTATOR_REQUESTS_DIR = ROOT / "data" / "02_augmentator" / "requests"
AUGMENTATOR_OUTPUTS_DIR = ROOT / "data" / "02_augmentator" / "outputs"
AUGMENTATOR_FAILED_DIR = ROOT / "data" / "02_augmentator" / "failed"
VALIDATOR_REQUESTS_DIR = ROOT / "data" / "03_validator" / "requests"
VALIDATOR_OUTPUTS_DIR = ROOT / "data" / "03_validator" / "outputs"
VALIDATOR_FAILED_DIR = ROOT / "data" / "03_validator" / "failed"
DEFAULT_GENERATOR_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_AUGMENTATOR_MODEL = "Qwen/Qwen2.5-14B-Instruct"
DEFAULT_VALIDATOR_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_MAX_NEW_TOKENS = 700
DEFAULT_TEMPERATURE = 0.2
CANONICAL_SCENARIO_IDS = set(scenario_ids())
CANONICAL_SIGNAL_IDS = set(signal_ids())
GENERATOR_MAX_ATTEMPTS = 3
AUGMENTATOR_MAX_ATTEMPTS = 2


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def failed_output_path(stage: str) -> Path:
    if stage == "generator":
        return GENERATOR_FAILED_DIR / "generator_failed_v0.jsonl"
    if stage == "augmentator":
        return AUGMENTATOR_FAILED_DIR / "augmentator_failed_v0.jsonl"
    if stage == "validator":
        return VALIDATOR_FAILED_DIR / "validator_failed_v0.jsonl"
    raise ValueError(f"Unsupported stage: {stage}")


def default_model_for_stage(stage: str) -> str:
    if stage == "generator":
        return DEFAULT_GENERATOR_MODEL
    if stage == "augmentator":
        return DEFAULT_AUGMENTATOR_MODEL
    if stage == "validator":
        return DEFAULT_VALIDATOR_MODEL
    raise ValueError(f"Unsupported stage: {stage}")


def render_progress(stage: str, completed: int, total: int, failures: int) -> None:
    total = max(total, 1)
    width = 28
    ratio = completed / total
    filled = min(width, int(ratio * width))
    bar = "#" * filled + "-" * (width - filled)
    message = f"\r[{stage}] [{bar}] {completed}/{total} | failures: {failures}"
    sys.stderr.write(message)
    sys.stderr.flush()


def finish_progress() -> None:
    sys.stderr.write("\n")
    sys.stderr.flush()


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped.strip()


def find_balanced_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise ValueError("Model output does not contain a JSON object start")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError("Model output does not contain a balanced JSON object")


def sanitize_json_text(text: str) -> str:
    sanitized = strip_code_fences(text)
    sanitized = sanitized.replace("\u201c", '"').replace("\u201d", '"')
    sanitized = sanitized.replace("\u2018", "'").replace("\u2019", "'")
    sanitized = sanitized.replace("\ufeff", "")
    sanitized = re.sub(r",(\s*[}\]])", r"\1", sanitized)
    return sanitized.strip()


def _next_non_whitespace_char(text: str, start_index: int) -> str:
    for index in range(start_index, len(text)):
        if not text[index].isspace():
            return text[index]
    return ""


def escape_inner_quotes_in_json_strings(text: str) -> str:
    repaired: list[str] = []
    in_string = False
    escaped = False

    for index, char in enumerate(text):
        if not in_string:
            repaired.append(char)
            if char == '"':
                in_string = True
                escaped = False
            continue

        if escaped:
            repaired.append(char)
            escaped = False
            continue

        if char == "\\":
            repaired.append(char)
            escaped = True
            continue

        if char == '"':
            next_char = _next_non_whitespace_char(text, index + 1)
            if next_char and next_char not in {":", ",", "}", "]"}:
                repaired.append('\\"')
                continue
            repaired.append(char)
            in_string = False
            continue

        repaired.append(char)

    return "".join(repaired)


def parse_json_object(text: str) -> dict:
    candidate = find_balanced_json_object(sanitize_json_text(text))
    repaired_candidate = escape_inner_quotes_in_json_strings(candidate)
    parsers = [
        lambda raw: json.loads(raw),
        lambda raw: json.loads(re.sub(r",(\s*[}\]])", r"\1", raw)),
        lambda raw: ast.literal_eval(
            raw.replace(": true", ": True")
            .replace(": false", ": False")
            .replace(": null", ": None")
        ),
    ]
    last_error = None
    for raw in (candidate, repaired_candidate):
        for parser in parsers:
            try:
                parsed = parser(raw)
                if not isinstance(parsed, dict):
                    raise ValueError("Parsed object is not a dictionary")
                return parsed
            except Exception as exc:  # noqa: BLE001
                last_error = exc
    raise ValueError(f"Failed to parse model JSON output: {last_error}") from last_error


def ensure_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[;\n,|]+", value)
        return [part.strip() for part in parts if part.strip()]
    return [str(value).strip()]


def ensure_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "ok", "accepted", "accept"}:
            return True
        if lowered in {"false", "no", "reject", "rejected"}:
            return False
    return default


def ensure_string(value: object, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def normalize_text_for_token_diff(text: str) -> list[str]:
    normalized = text.lower().replace("ё", "е")
    normalized = re.sub(r"[^a-zа-я0-9\s]", " ", normalized)
    return [token for token in normalized.split() if token]


def count_token_differences(source_text: str, generated_text: str) -> int:
    source_tokens = normalize_text_for_token_diff(source_text)
    generated_tokens = normalize_text_for_token_diff(generated_text)
    max_len = max(len(source_tokens), len(generated_tokens))
    diff_count = 0
    for index in range(max_len):
        source_token = source_tokens[index] if index < len(source_tokens) else ""
        generated_token = generated_tokens[index] if index < len(generated_tokens) else ""
        if source_token != generated_token:
            diff_count += 1
    return diff_count


def scrub_generated_text(text: str) -> str:
    sanitized = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-zА-Яа-я]{2,}\b", "[email_removed]", text)
    sanitized = re.sub(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b", "[phone_removed]", sanitized)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized


def canonicalize_generator_signals(raw_signals: object, metadata: dict) -> list[str]:
    parsed_signals = [
        signal
        for signal in ensure_list(raw_signals)
        if signal in CANONICAL_SIGNAL_IDS
    ]
    required = [signal for signal in metadata["required_signals"] if signal in CANONICAL_SIGNAL_IDS]
    optional = [signal for signal in metadata["optional_signals"] if signal in CANONICAL_SIGNAL_IDS]
    forbidden = set(metadata["forbidden_signals"])

    ordered: list[str] = []
    for signal in required + parsed_signals + optional:
        if signal in forbidden:
            continue
        if signal not in ordered:
            ordered.append(signal)

    return ordered


def canonicalize_augmentator_signals(raw_signals: object, metadata: dict) -> list[str]:
    source_signals = [
        signal
        for signal in metadata.get("source_signals", [])
        if signal in CANONICAL_SIGNAL_IDS
    ]
    parsed_signals = [
        signal
        for signal in ensure_list(raw_signals)
        if signal in CANONICAL_SIGNAL_IDS and signal in source_signals
    ]

    ordered: list[str] = []
    for signal in parsed_signals or source_signals:
        if signal not in ordered:
            ordered.append(signal)
    return ordered


def validate_generator_record(record: dict, metadata: dict) -> None:
    text = record["text"].lower()
    required = set(metadata["required_signals"])
    forbidden = set(metadata["forbidden_signals"])
    signals = set(record["signals"])

    missing_required = [signal for signal in required if signal not in signals]
    if missing_required:
        raise ValueError(f"missing required signals: {missing_required}")

    present_forbidden = [signal for signal in forbidden if signal in signals]
    if present_forbidden:
        raise ValueError(f"contains forbidden signals: {present_forbidden}")

    if len(record["text"]) < 40:
        raise ValueError("generated text is too short")

    if record["label"] == "safe":
        suspicious_markers = [
            "код из смс",
            "безопасный счет",
            "перейдите по ссылке",
            "установите приложение",
            "не говорите никому",
        ]
        if any(marker in text for marker in suspicious_markers):
            raise ValueError("safe example contains obvious fraud markers")

    if record["scenario"] == "relative_emergency":
        family_markers = ["мама", "папа", "сын", "дочь", "брат", "сестра", "родствен"]
        scam_markers = [
            "перевед",
            "деньги",
            "сбил",
            "следоват",
            "полиц",
            "не звони",
            "никому не говори",
            "никому не сообщай",
            "сохрани это в тайне",
        ]
        if not any(marker in text for marker in family_markers):
            raise ValueError("relative_emergency example lacks family cue")
        if not any(marker in text for marker in scam_markers):
            raise ValueError("relative_emergency fraud lacks explicit scam action")

    if record["scenario"] == "safe_account_transfer":
        if not any(marker in text for marker in ["безопасн", "резервн", "защищенн"]):
            raise ValueError("safe_account_transfer example lacks safe-account wording")

    if record["scenario"] == "fake_loan_application":
        if "кредит" not in text:
            raise ValueError("fake_loan_application example lacks credit cue")
        if not any(marker in text for marker in ["заявк", "оформ", "отмен"]):
            raise ValueError("fake_loan_application example lacks application/cancel cue")


def validate_augmentator_record(record: dict, request: dict) -> None:
    metadata = request["metadata"]
    source_text = ensure_string(metadata.get("source_text")).strip()
    generated_text = record["text"].strip()
    source_signals = [
        signal
        for signal in metadata.get("source_signals", [])
        if signal in CANONICAL_SIGNAL_IDS
    ]

    if not generated_text:
        raise ValueError("augmentator generated empty text")

    if record["label"] != metadata["label"]:
        raise ValueError("augmentator changed label")

    if record["base_id"] != request["base_id"]:
        raise ValueError("augmentator changed base_id")

    if record["augmentation_type"] != metadata["augmentation_type"]:
        raise ValueError("augmentator changed augmentation_type")

    if record["augmentation_type"] in {"paraphrase", "subtle", "scenario_variation"} and generated_text == source_text:
        raise ValueError("augmentator returned unchanged text")

    token_diff_count = count_token_differences(source_text, generated_text)

    if record["augmentation_type"] == "asr_noise":
        if generated_text == source_text:
            raise ValueError("asr_noise returned unchanged text")
        if token_diff_count < 2:
            raise ValueError("asr_noise is too close to the original text")

    if source_signals and not record["preserved_signals"]:
        raise ValueError("augmentator returned no preserved signals")

    lowered = generated_text.lower()
    if record["label"] == "safe":
        suspicious_markers = [
            "код из смс",
            "безопасный счет",
            "перейдите по ссылке",
            "установите приложение",
        ]
        if any(marker in lowered for marker in suspicious_markers):
            raise ValueError("safe augmentation contains obvious fraud markers")


def normalize_generator_output(request: dict, parsed: dict) -> dict:
    metadata = request["metadata"]
    request_id = request["request_id"]
    normalized = {
        "id": request_id,
        "label": metadata["label"],
        "scenario": metadata["scenario"] if metadata["scenario"] in CANONICAL_SCENARIO_IDS else ensure_string(parsed.get("scenario"), metadata["scenario"]),
        "text": scrub_generated_text(ensure_string(parsed.get("text") or parsed.get("dialogue") or parsed.get("dialog"))),
        "signals": canonicalize_generator_signals(parsed.get("signals"), metadata),
        "difficulty": metadata["difficulty"],
        "source": "synthetic_llm_generated",
        "language": "ru",
        "modality": "text",
        "_meta": {
            "request_id": request_id,
            "brief_id": metadata["brief_id"],
        },
    }
    validate_generator_record(normalized, metadata)
    return normalized


def normalize_augmentator_output(request: dict, parsed: dict) -> dict:
    metadata = request["metadata"]
    request_id = request["request_id"]
    normalized = {
        "id": request_id,
        "base_id": request["base_id"],
        "augmentation_type": metadata["augmentation_type"],
        "label": metadata["label"],
        "text": scrub_generated_text(ensure_string(parsed.get("text") or parsed.get("dialogue") or parsed.get("dialog"))),
        "preserved_signals": canonicalize_augmentator_signals(parsed.get("preserved_signals") or parsed.get("signals"), metadata),
        "notes": ensure_string(parsed.get("notes") or parsed.get("changed_aspects")),
        "_meta": {
            "request_id": request_id,
            "scenario": metadata["scenario"],
        },
    }
    validate_augmentator_record(normalized, request)
    return normalized


def normalize_validator_output(request: dict, parsed: dict) -> dict:
    request_id = request["request_id"]
    accept_value = parsed.get("accept", parsed.get("is_valid"))
    return {
        "id": request_id,
        "base_id": ensure_string(parsed.get("base_id"), request.get("base_id", request_id.removesuffix("_validator"))),
        "accept": ensure_bool(accept_value, default=False),
        "label_consistency": ensure_string(parsed.get("label_consistency") or parsed.get("label_match"), "warning"),
        "signal_consistency": ensure_string(parsed.get("signal_consistency") or parsed.get("signals_present"), "warning"),
        "privacy_check": ensure_string(parsed.get("privacy_check") or ("fail" if ensure_bool(parsed.get("pii_detected"), False) else "ok"), "warning"),
        "issues": ensure_list(parsed.get("issues") or parsed.get("quality_issues")),
        "recommended_fixes": ensure_list(parsed.get("recommended_fixes") or parsed.get("review_comment")),
        "_meta": {
            "request_id": request_id,
            "scenario": request["metadata"]["scenario"],
            "label": request["metadata"]["label"],
        },
    }


def postprocess_model_output(stage: str, request: dict, raw_text: str) -> dict:
    parsed = parse_json_object(raw_text)
    if stage == "generator":
        return normalize_generator_output(request, parsed)
    if stage == "augmentator":
        return normalize_augmentator_output(request, parsed)
    if stage == "validator":
        return normalize_validator_output(request, parsed)
    raise ValueError(f"Unsupported stage: {stage}")


def build_retry_prompt(stage: str, request: dict, error_message: str, attempt_number: int) -> str:
    base_prompt = request["prompt"]
    if stage == "augmentator":
        extra_rules = ""
        augmentation_type = request.get("metadata", {}).get("augmentation_type")
        if augmentation_type == "asr_noise":
            extra_rules = (
                "\n"
                + "Дополнительно для asr_noise:\n"
                + "- внеси 2-4 умеренные ASR-подобные ошибки;\n"
                + "- не меняй смысл диалога;\n"
                + "- не возвращай исходный текст;\n"
                + "- используй искажения уровня «потвердите», «эсэмэс», «гос услуги», «кридит», «кот из смс».\n"
            )
        return (
            base_prompt
            + "\n\n"
            + "Предыдущая попытка была отклонена постобработкой.\n"
            + f"Причина: {error_message}\n"
            + f"Это попытка номер {attempt_number}.\n"
            + "Исправь именно эту проблему.\n"
            + "Особенно важно:\n"
            + "- текст должен заметно отличаться от исходника;\n"
            + "- измени минимум две формулировки;\n"
            + "- сохрани метку и preserved_signals;\n"
            + "- верни только один JSON-объект."
            + extra_rules
        )
    if stage == "generator":
        return (
            base_prompt
            + "\n\n"
            + "Предыдущая попытка была отклонена постобработкой.\n"
            + f"Причина: {error_message}\n"
            + f"Это попытка номер {attempt_number}.\n"
            + "Исправь именно эту проблему и верни только один JSON-объект."
        )
    return base_prompt


class ExportBackend:
    name = "export"

    def complete(self, prompt: str, model: str) -> str:
        raise RuntimeError("Export backend should not be called for direct completion")


class TransformersBackend:
    name = "transformers"

    def __init__(self, max_new_tokens: int, temperature: float) -> None:
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self._tokenizer = None
        self._model = None
        self._model_name = None

    def _ensure_loaded(self, model_name: str) -> None:
        if self._model is not None and self._model_name == model_name:
            return

        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        self._tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
        )
        self._model_name = model_name

    def complete(self, prompt: str, model: str) -> str:
        self._ensure_loaded(model)

        import torch

        messages = [
            {"role": "system", "content": "You are a JSON-only assistant. Return exactly one JSON object."},
            {"role": "user", "content": prompt},
        ]

        tokenizer = self._tokenizer
        model_obj = self._model
        assert tokenizer is not None
        assert model_obj is not None

        rendered_prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = tokenizer(rendered_prompt, return_tensors="pt")
        inputs = {key: value.to(model_obj.device) for key, value in inputs.items()}

        with torch.no_grad():
            output_ids = model_obj.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=self.temperature > 0,
                temperature=max(self.temperature, 1e-5),
                pad_token_id=tokenizer.eos_token_id,
            )

        generated_ids = output_ids[0][inputs["input_ids"].shape[1] :]
        generated_text = tokenizer.decode(generated_ids, skip_special_tokens=True)
        return generated_text


def get_backend(name: str, max_new_tokens: int, temperature: float):
    backends = {
        "export": ExportBackend(),
        "transformers": TransformersBackend(max_new_tokens=max_new_tokens, temperature=temperature),
    }
    if name not in backends:
        raise ValueError(f"Unsupported backend: {name}")
    return backends[name]


def build_generator_requests() -> list[dict]:
    briefs = load_jsonl(GENERATOR_SEEDS_PATH)
    requests = []
    for brief in briefs:
        for index in range(brief["target_count"]):
            request_id = f"{brief['brief_id']}_gen_{index + 1:02d}"
            requests.append(
                {
                    "request_id": request_id,
                    "stage": "generator",
                    "brief_id": brief["brief_id"],
                    "target_model_role": "generator",
                    "prompt": format_generator_prompt(brief, request_id),
                    "metadata": brief,
                }
            )
    return requests


def build_augmentator_requests(generated_rows: list[dict]) -> list[dict]:
    requests = []
    augmentation_plan = ["paraphrase", "subtle", "asr_noise"]
    for row in generated_rows:
        if row["label"] == "safe":
            kinds = ["paraphrase", "scenario_variation"]
        else:
            kinds = augmentation_plan
        for augmentation_type in kinds:
            request_id = f"{row['id']}_{augmentation_type}"
            requests.append(
                {
                    "request_id": request_id,
                    "stage": "augmentator",
                    "base_id": row["id"],
                    "target_model_role": "augmentator",
                    "prompt": format_augmentator_prompt(row, augmentation_type),
                    "metadata": {
                        "augmentation_type": augmentation_type,
                        "label": row["label"],
                        "scenario": row["scenario"],
                        "source_signals": row.get("signals", []),
                        "source_text": row.get("text", ""),
                    },
                }
            )
    return requests


def build_validator_requests(generated_rows: list[dict]) -> list[dict]:
    requests = []
    for row in generated_rows:
        requests.append(
            {
                "request_id": f"{row['id']}_validator",
                "stage": "validator",
                "base_id": row["id"],
                "target_model_role": "validator",
                "prompt": format_validator_prompt(row),
                "metadata": {
                    "label": row["label"],
                    "scenario": row["scenario"],
                },
            }
        )
    return requests


def export_requests(stage: str) -> Path:
    if stage == "generator":
        requests = build_generator_requests()
        path = GENERATOR_REQUESTS_DIR / "generator_requests_v0.jsonl"
    elif stage == "augmentator":
        generated_rows = load_jsonl(GENERATOR_OUTPUTS_DIR / "internal_generated_candidates_v0.jsonl")
        requests = build_augmentator_requests(generated_rows)
        path = AUGMENTATOR_REQUESTS_DIR / "augmentator_requests_v0.jsonl"
    elif stage == "validator":
        generated_rows = load_jsonl(GENERATOR_OUTPUTS_DIR / "internal_generated_candidates_v0.jsonl")
        requests = build_validator_requests(generated_rows)
        path = VALIDATOR_REQUESTS_DIR / "validator_requests_v0.jsonl"
    else:
        raise ValueError(f"Unsupported stage: {stage}")
    write_jsonl(path, requests)
    return path


def run_stage(stage: str, backend_name: str, model: str, max_new_tokens: int, temperature: float) -> Path:
    backend = get_backend(backend_name, max_new_tokens=max_new_tokens, temperature=temperature)
    if backend_name == "export":
        return export_requests(stage)

    if stage == "generator":
        requests = build_generator_requests()
        output_path = GENERATOR_OUTPUTS_DIR / "internal_generated_candidates_v0.jsonl"
    elif stage == "augmentator":
        generated_rows = load_jsonl(GENERATOR_OUTPUTS_DIR / "internal_generated_candidates_v0.jsonl")
        requests = build_augmentator_requests(generated_rows)
        output_path = AUGMENTATOR_OUTPUTS_DIR / "augmentation_subset_v0.jsonl"
    elif stage == "validator":
        generated_rows = load_jsonl(GENERATOR_OUTPUTS_DIR / "internal_generated_candidates_v0.jsonl")
        requests = build_validator_requests(generated_rows)
        output_path = VALIDATOR_OUTPUTS_DIR / "validator_decisions_v0.jsonl"
    else:
        raise ValueError(f"Unsupported stage: {stage}")

    outputs = []
    failures = []
    if stage == "generator":
        max_attempts = GENERATOR_MAX_ATTEMPTS
    elif stage == "augmentator":
        max_attempts = AUGMENTATOR_MAX_ATTEMPTS
    else:
        max_attempts = 1
    total_requests = len(requests)
    render_progress(stage, completed=0, total=total_requests, failures=0)
    for request_index, request in enumerate(requests, start=1):
        last_exc = None
        last_preview = ""
        last_raw_completion = ""
        for attempt_index in range(max_attempts):
            prompt = request["prompt"]
            if last_exc is not None:
                prompt = build_retry_prompt(stage, request, str(last_exc), attempt_index + 1)
            raw_completion = backend.complete(prompt, model)
            last_raw_completion = raw_completion
            try:
                normalized = postprocess_model_output(stage, request, raw_completion)
                outputs.append(normalized)
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                last_preview = raw_completion[:500].replace("\n", "\\n")
        else:
            failures.append(
                {
                    "request_id": request["request_id"],
                    "stage": stage,
                    "error": str(last_exc) if last_exc else "unknown_error",
                    "attempts": max_attempts,
                    "raw_output_preview": last_preview,
                    "raw_output": last_raw_completion,
                    "base_id": request.get("base_id"),
                    "metadata": request.get("metadata", {}),
                }
            )
        render_progress(stage, completed=request_index, total=total_requests, failures=len(failures))
    finish_progress()
    write_jsonl(output_path, outputs)
    if failures:
        write_jsonl(failed_output_path(stage), failures)
    return output_path


def print_recommended_settings() -> None:
    print(f"Recommended generator model: {DEFAULT_GENERATOR_MODEL}")
    print(f"Recommended augmentator model: {DEFAULT_AUGMENTATOR_MODEL}")
    print(f"Recommended validator model: {DEFAULT_VALIDATOR_MODEL}")
    print(f"Recommended max_new_tokens: {DEFAULT_MAX_NEW_TOKENS}")
    print(f"Recommended temperature: {DEFAULT_TEMPERATURE}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or export open-source LLM jobs for the NIRS dataset pipeline.")
    parser.add_argument("stage", choices=["generator", "augmentator", "validator"])
    parser.add_argument("--backend", choices=["export", "transformers"], default="transformers")
    parser.add_argument("--model", help="Override Hugging Face model id or local model path for this run.")
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--print-defaults", action="store_true")
    args = parser.parse_args()

    if args.print_defaults:
        print_recommended_settings()

    model_name = args.model or default_model_for_stage(args.stage)

    output_path = run_stage(
        args.stage,
        args.backend,
        model_name,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
    )
    print(f"Wrote {args.stage} artifact to {output_path}")


if __name__ == "__main__":
    main()
