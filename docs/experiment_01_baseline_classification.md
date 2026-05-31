# Эксперимент 1 — базовая классификация

## Данные

Основной текстовый synthetic-core датасет с тремя классами:

- `fraud`
- `suspicious`
- `safe`

## Что сравниваем

- `rules_baseline`
- `single_llm`
- `llm_checklist`
- `llm_self_check`
- `llm_ensemble`

## Основные метрики

- `accuracy`
- `precision_fraud`
- `recall_fraud`
- `f1_fraud`

## Почему особенно важен recall для fraud

В данной задаче критичнее пропустить как можно меньше мошеннических диалогов, чем изредка дать лишнее подозрительное срабатывание. Поэтому для интерпретации результатов ключевой метрикой выступает `recall_fraud`.

## Дополнительные метрики

- `latency_ms_avg`
- `cost_usd_estimate`
- `false_positives`
- `false_negatives`

## Как интерпретировать таблицу

Базовая таблица для презентации должна содержать:

| Model | Accuracy | Precision fraud | Recall fraud | F1 fraud |
|---|---:|---:|---:|---:|

При необходимости во второй таблице или в устном комментарии отдельно показываются:

- `false_positives`
- `false_negatives`
- `latency_ms_avg`
- `cost_usd_estimate`
