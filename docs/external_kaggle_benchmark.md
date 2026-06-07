# Внешний Kaggle Benchmark

## Роль в НИРС

Kaggle-набор используется как `external_benchmark`, а не как основной датасет работы.
Его задача — показать, что пайплайн работает не только на внутреннем synthetic core.

## Рекомендуемый объём

- `fraud/scam`: 50
- `safe/non-scam`: 50

Итого: 100 внешних примеров.

## Где лежит шаблон

- raw шаблон: [kaggle_scam_non_scam_ru_subset.csv](/Users/margogusarova/Documents/НИРС/data/05_external_benchmark/raw/kaggle_scam_non_scam_ru_subset.csv)

## Обязательные поля

- `id`
- `label`
- `original_text`
- `text_ru`
- `scenario`
- `signals`
- `difficulty`
- `source`
- `original_language`
- `language`
- `translation_type`
- `modality`

## Нормализация

Для перевода raw CSV в нормализованный benchmark используется:

- [prepare_kaggle_external_benchmark.py](/Users/margogusarova/Documents/НИРС/src/nirs_fraud/pipeline/prepare_kaggle_external_benchmark.py)

Запуск:

```bash
python3 -m src.nirs_fraud.pipeline.prepare_kaggle_external_benchmark
```

На выходе будут:

- `data/05_external_benchmark/normalized/kaggle_external_benchmark_v1.jsonl`
- `data/05_external_benchmark/normalized/kaggle_external_benchmark_v1.csv`

## Корректная формулировка для отчёта

Внешний Kaggle benchmark используется как независимый тестовый корпус для дополнительной проверки переносимости пайплайна. Он не смешивается с `internal_synthetic_core` и не заменяет собственный вклад работы в части генерации и валидации данных.
