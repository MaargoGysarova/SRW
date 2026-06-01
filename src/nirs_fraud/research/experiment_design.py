from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ArchitectureSpec:
    id: str
    title_ru: str
    description_ru: str


@dataclass(frozen=True)
class ExperimentSpec:
    id: str
    title_ru: str
    dataset_ru: str
    question_ru: str
    compared_architectures: tuple[str, ...]
    primary_metrics: tuple[str, ...]
    secondary_metrics: tuple[str, ...]


ARCHITECTURE_SPECS: tuple[ArchitectureSpec, ...] = (
    ArchitectureSpec("rules_baseline", "Rules baseline", "простые правила по ключевым словам"),
    ArchitectureSpec("single_llm", "Single LLM", "одна LLM классифицирует текст"),
    ArchitectureSpec("llm_checklist", "LLM checklist", "LLM анализирует текст по чек-листу признаков"),
    ArchitectureSpec("llm_self_check", "LLM self-check", "LLM сначала отвечает, потом проверяет собственный вывод"),
    ArchitectureSpec("llm_ensemble", "LLM ensemble", "несколько независимых LLM/промптов голосуют"),
)


EXPERIMENT_SPECS: tuple[ExperimentSpec, ...] = (
    ExperimentSpec(
        id="experiment_01_baseline_classification",
        title_ru="Эксперимент 1 — базовая классификация",
        dataset_ru="наша синтетика fraud / suspicious / safe",
        question_ru="Как меняется качество классификации при переходе от rules baseline к LLM-подходам?",
        compared_architectures=("rules_baseline", "single_llm", "llm_checklist", "llm_self_check", "llm_ensemble"),
        primary_metrics=("accuracy", "precision_fraud", "recall_fraud", "f1_fraud"),
        secondary_metrics=("latency_ms_avg", "false_positives", "false_negatives"),
    ),
    ExperimentSpec(
        id="experiment_02_augmentation_robustness",
        title_ru="Эксперимент 2 — устойчивость к аугментации",
        dataset_ru="original / paraphrased / subtle / asr_noise",
        question_ru="Сохраняет ли модель качество, если мошенник переформулирует фразы или если текст искажается ASR-подобным шумом?",
        compared_architectures=("llm_checklist", "llm_self_check", "llm_ensemble"),
        primary_metrics=("accuracy", "recall_fraud"),
        secondary_metrics=("false_positives", "false_negatives", "latency_ms_avg"),
    ),
)


def architectures_as_json() -> dict:
    return {"architectures": [asdict(item) for item in ARCHITECTURE_SPECS]}


def experiments_as_json() -> dict:
    return {"experiments": [asdict(item) for item in EXPERIMENT_SPECS]}
