from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class MetricDefinition:
    id: str
    description_ru: str


METRICS: tuple[MetricDefinition, ...] = (
    MetricDefinition("accuracy", "доля правильных предсказаний по всем классам"),
    MetricDefinition("precision_fraud", "точность по fraud-классу"),
    MetricDefinition("recall_fraud", "полнота по fraud-классу"),
    MetricDefinition("f1_fraud", "F1-score по fraud-классу"),
    MetricDefinition("latency_ms_avg", "среднее время обработки одного примера в миллисекундах"),
    MetricDefinition("false_positives", "число ложных срабатываний по fraud-классу"),
    MetricDefinition("false_negatives", "число пропущенных fraud-примеров"),
)


def metrics_as_json() -> dict:
    return {"metrics": [asdict(item) for item in METRICS]}


def compute_classification_metrics(
    y_true: list[str],
    y_pred: list[str],
    *,
    positive_label: str = "fraud",
    latency_ms_avg: float,
) -> dict[str, float]:
    total = len(y_true)
    correct = sum(1 for truth, pred in zip(y_true, y_pred) if truth == pred)
    tp = sum(1 for truth, pred in zip(y_true, y_pred) if truth == positive_label and pred == positive_label)
    fp = sum(1 for truth, pred in zip(y_true, y_pred) if truth != positive_label and pred == positive_label)
    fn = sum(1 for truth, pred in zip(y_true, y_pred) if truth == positive_label and pred != positive_label)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "accuracy": round(correct / total, 3) if total else 0.0,
        "precision_fraud": round(precision, 3),
        "recall_fraud": round(recall, 3),
        "f1_fraud": round(f1, 3),
        "latency_ms_avg": round(latency_ms_avg, 3),
        "false_positives": fp,
        "false_negatives": fn,
    }
