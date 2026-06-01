from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ResearchHypothesis:
    id: str
    title_ru: str
    statement_ru: str
    related_experiments: tuple[str, ...]
    primary_metric: str
    success_pattern_ru: str


RESEARCH_HYPOTHESES: tuple[ResearchHypothesis, ...] = (
    ResearchHypothesis(
        id="hypothesis_01_checklist_beats_single_llm_on_recall",
        title_ru="Checklist лучше single LLM по recall fraud",
        statement_ru="Архитектура llm_checklist обеспечивает более высокий recall_fraud, чем single_llm, благодаря структурированному анализу признаков мошенничества.",
        related_experiments=("experiment_01_baseline_classification",),
        primary_metric="recall_fraud",
        success_pattern_ru="recall_fraud у llm_checklist выше, чем у single_llm, при сопоставимом или лучшем F1 fraud.",
    ),
    ResearchHypothesis(
        id="hypothesis_02_self_check_reduces_borderline_errors",
        title_ru="Self-check снижает ошибки на пограничных случаях",
        statement_ru="Архитектура llm_self_check снижает число ошибок на пограничных suspicious-примерах по сравнению с llm_checklist за счёт дополнительного шага самопроверки.",
        related_experiments=("experiment_01_baseline_classification", "experiment_02_augmentation_robustness"),
        primary_metric="false_positives",
        success_pattern_ru="у llm_self_check меньше ложных срабатываний и/или меньше ошибок на suspicious-кейcах при сохранении приемлемого recall_fraud.",
    ),
    ResearchHypothesis(
        id="hypothesis_03_ensemble_is_more_stable",
        title_ru="Ensemble устойчивее одиночного запуска",
        statement_ru="Архитектура llm_ensemble даёт более устойчивое качество по сравнению с одиночным запуском модели, особенно на аугментированных вариантах текста.",
        related_experiments=("experiment_01_baseline_classification", "experiment_02_augmentation_robustness"),
        primary_metric="recall_fraud",
        success_pattern_ru="у llm_ensemble меньше просадка accuracy и recall_fraud на paraphrase / subtle / asr_noise по сравнению с single_llm и llm_checklist.",
    ),
    ResearchHypothesis(
        id="hypothesis_04_rules_fail_on_rewrites",
        title_ru="Rules baseline резко проседает на paraphrase и subtle",
        statement_ru="Простой rules_baseline значительно теряет качество на переформулированных и менее явных мошеннических сценариях по сравнению с LLM-подходами.",
        related_experiments=("experiment_02_augmentation_robustness",),
        primary_metric="recall_fraud",
        success_pattern_ru="на наборах paraphrase и subtle у rules_baseline заметно падает recall_fraud относительно original и относительно LLM-архитектур.",
    ),
)


def hypotheses_as_json() -> dict:
    return {"research_hypotheses": [asdict(item) for item in RESEARCH_HYPOTHESES]}
