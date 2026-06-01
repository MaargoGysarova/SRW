from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

from .prompts import format_augmentator_prompt, format_generator_prompt, format_validator_prompt


ROOT = Path(__file__).resolve().parents[3]
GENERATOR_SEEDS_PATH = ROOT / "data" / "01_generator" / "seed_briefs" / "generation_seed_briefs.jsonl"
GENERATOR_REQUESTS_DIR = ROOT / "data" / "01_generator" / "requests"
GENERATOR_OUTPUTS_DIR = ROOT / "data" / "01_generator" / "outputs"
AUGMENTATOR_REQUESTS_DIR = ROOT / "data" / "02_augmentator" / "requests"
AUGMENTATOR_OUTPUTS_DIR = ROOT / "data" / "02_augmentator" / "outputs"
VALIDATOR_REQUESTS_DIR = ROOT / "data" / "03_validator" / "requests"
VALIDATOR_OUTPUTS_DIR = ROOT / "data" / "03_validator" / "outputs"
DEFAULT_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_MAX_NEW_TOKENS = 700
DEFAULT_TEMPERATURE = 0.2


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


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


def parse_json_object(text: str) -> dict:
    candidate = find_balanced_json_object(sanitize_json_text(text))
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
    for parser in parsers:
        try:
            parsed = parser(candidate)
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


def normalize_generator_output(request: dict, parsed: dict) -> dict:
    metadata = request["metadata"]
    request_id = request["request_id"]
    return {
        "id": ensure_string(parsed.get("id"), request_id),
        "label": ensure_string(parsed.get("label"), metadata["label"]),
        "scenario": ensure_string(parsed.get("scenario"), metadata["scenario"]),
        "text": ensure_string(parsed.get("text") or parsed.get("dialogue") or parsed.get("dialog")),
        "signals": ensure_list(parsed.get("signals")),
        "difficulty": ensure_string(parsed.get("difficulty"), metadata["difficulty"]),
        "source": ensure_string(parsed.get("source"), "synthetic_llm_generated"),
        "language": ensure_string(parsed.get("language"), "ru"),
        "modality": ensure_string(parsed.get("modality"), "text"),
        "_meta": {
            "request_id": request_id,
            "brief_id": metadata["brief_id"],
        },
    }


def normalize_augmentator_output(request: dict, parsed: dict) -> dict:
    metadata = request["metadata"]
    request_id = request["request_id"]
    return {
        "id": ensure_string(parsed.get("id"), request_id),
        "base_id": ensure_string(parsed.get("base_id"), request["base_id"]),
        "augmentation_type": ensure_string(parsed.get("augmentation_type"), metadata["augmentation_type"]),
        "label": ensure_string(parsed.get("label"), metadata["label"]),
        "text": ensure_string(parsed.get("text") or parsed.get("dialogue") or parsed.get("dialog")),
        "preserved_signals": ensure_list(parsed.get("preserved_signals") or parsed.get("signals")),
        "notes": ensure_string(parsed.get("notes") or parsed.get("changed_aspects")),
        "_meta": {
            "request_id": request_id,
            "scenario": metadata["scenario"],
        },
    }


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
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
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
                    "prompt": format_generator_prompt(brief),
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
    for request in requests:
        raw_completion = backend.complete(request["prompt"], model)
        normalized = postprocess_model_output(stage, request, raw_completion)
        outputs.append(normalized)
    write_jsonl(output_path, outputs)
    return output_path


def print_recommended_settings() -> None:
    print("Recommended default model: Qwen/Qwen2.5-3B-Instruct")
    print(f"Recommended max_new_tokens: {DEFAULT_MAX_NEW_TOKENS}")
    print(f"Recommended temperature: {DEFAULT_TEMPERATURE}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or export open-source LLM jobs for the NIRS dataset pipeline.")
    parser.add_argument("stage", choices=["generator", "augmentator", "validator"])
    parser.add_argument("--backend", choices=["export", "transformers"], default="transformers")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Hugging Face model id or local model path.")
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--print-defaults", action="store_true")
    args = parser.parse_args()

    if args.print_defaults:
        print_recommended_settings()

    output_path = run_stage(
        args.stage,
        args.backend,
        args.model,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
    )
    print(f"Wrote {args.stage} artifact to {output_path}")


if __name__ == "__main__":
    main()
