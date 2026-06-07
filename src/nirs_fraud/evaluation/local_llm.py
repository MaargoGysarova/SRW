from __future__ import annotations

import csv
import time
from pathlib import Path

from ..llm.prompts import format_classification_prompt
from ..llm.run_open_source_llm import ensure_list, ensure_string, parse_json_object


DEFAULT_LOCAL_LLM_MODEL = "Qwen/Qwen2.5-14B-Instruct"
DEFAULT_MAX_NEW_TOKENS = 500
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_ATTEMPTS = 2
VALID_LABELS = {"fraud", "suspicious", "safe"}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def slugify_model_name(model: str) -> str:
    return model.replace("/", "_").replace(":", "_").replace(".", "_")


def normalize_classification_output(parsed: dict) -> dict:
    label = ensure_string(parsed.get("label"), "suspicious").strip().lower()
    if label not in VALID_LABELS:
        label = "suspicious"

    fraud_score_raw = parsed.get("fraud_score", 0.0)
    try:
        fraud_score = float(fraud_score_raw)
    except (TypeError, ValueError):
        fraud_score = 0.0
    fraud_score = max(0.0, min(1.0, fraud_score))

    return {
        "label": label,
        "fraud_score": round(fraud_score, 3),
        "signals": ensure_list(parsed.get("signals")),
        "explanation": ensure_string(parsed.get("explanation")),
    }


def build_retry_prompt(base_prompt: str, error_message: str, attempt_number: int) -> str:
    return (
        base_prompt
        + "\n\n"
        + "Предыдущий ответ был отклонён постобработкой.\n"
        + f"Причина: {error_message}\n"
        + f"Это попытка номер {attempt_number}.\n"
        + "Исправь формат и верни только один JSON-объект строго по схеме.\n"
        + "Дополнительно проверь:\n"
        + '- что `label` равен ровно одному из: "fraud", "suspicious", "safe";\n'
        + '- что `fraud_score` — число от 0.0 до 1.0;\n'
        + '- что `signals` — массив строк;\n'
        + '- что вне JSON нет никакого текста.'
    )


class TransformersClassificationBackend:
    def __init__(self, model_name: str, max_new_tokens: int, temperature: float) -> None:
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self._tokenizer = None
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return

        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
        )

    def complete(self, prompt: str) -> str:
        self._ensure_loaded()

        import torch

        tokenizer = self._tokenizer
        model = self._model
        assert tokenizer is not None
        assert model is not None

        messages = [
            {"role": "system", "content": "You are a JSON-only assistant. Return exactly one JSON object."},
            {"role": "user", "content": prompt},
        ]
        rendered_prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = tokenizer(rendered_prompt, return_tensors="pt")
        inputs = {key: value.to(model.device) for key, value in inputs.items()}

        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=self.temperature > 0,
                temperature=max(self.temperature, 1e-5),
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )

        generated_ids = output_ids[0][inputs["input_ids"].shape[1] :]
        return tokenizer.decode(generated_ids, skip_special_tokens=True)


def classify_text(
    *,
    backend: TransformersClassificationBackend,
    text: str,
    architecture: str,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> tuple[dict, float]:
    base_prompt = format_classification_prompt(text, architecture)
    last_error: Exception | None = None
    last_preview = ""

    for attempt_index in range(max_attempts):
        prompt = base_prompt if last_error is None else build_retry_prompt(base_prompt, str(last_error), attempt_index + 1)
        started = time.perf_counter()
        raw_output = backend.complete(prompt)
        elapsed_ms = (time.perf_counter() - started) * 1000
        try:
            parsed = parse_json_object(raw_output)
            normalized = normalize_classification_output(parsed)
            return normalized, elapsed_ms
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            last_preview = raw_output[:500].replace("\n", "\\n")

    raise ValueError(
        f"Failed to parse local LLM classification output for architecture={architecture} "
        f"after {max_attempts} attempts. Model output preview: {last_preview}"
    ) from last_error
