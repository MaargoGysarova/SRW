# Статус внутреннего датасета

Текущая версия внутреннего synthetic-core хранится в [internal_synthetic_core_v0.jsonl](/Users/margogusarova/Documents/НИРС/data/04_final_dataset/internal_synthetic_core_v0.jsonl):

- `fraud`: 12
- `suspicious`: 8
- `safe`: 10
- всего: 30

Целевой баланс НИРС:

- `fraud`: 40
- `suspicious`: 20
- `safe`: 30
- всего: 90

Осталось добрать:

- `fraud`: 28
- `suspicious`: 12
- `safe`: 20

Корректная интерпретация:

Текущий `internal_synthetic_core_v0` — это не финальный основной датасет, а первая принятая seed-версия внутреннего набора. Она уже годится для описания методологии, валидации схемы и первичного baseline, но до целевого объема ее нужно расширить следующими батчами генерации.
