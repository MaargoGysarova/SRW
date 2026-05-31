# Методология датасета для НИРС

## Главная логика

В НИРС основной датасет должен быть **внутренним контролируемым синтетическим набором**, а не внешним готовым CSV. Поэтому структура работы по данным задается так:

```text
LLM-generator
  -> LLM-augmentator
  -> LLM-validator / manual review
  -> final dataset
```

## Разделение данных

В проекте теперь разделены четыре сущности:

1. `internal_synthetic_core`
   Это основной набор для метрик и сравнения архитектур.

2. `augmentation_subset`
   Это отдельный набор для проверки устойчивости к paraphrase, subtle и ASR-noise.

3. `external_benchmark`
   Это внешний датасет-пример, который используется не как основной корпус, а как дополнительный тест и материал для обсуждения переносимости.

4. `audio_subsets`
   Это synthetic TTS-аудио и небольшой набор реальных аудио для качественной валидации.

## Почему так корректно методологически

- Мы не подменяем собственный вклад готовым внешним CSV.
- Мы честно показываем, что основной вклад НИРС — схема получения и проверки данных.
- Мы оставляем внешний датасет как независимую проверку и точку сравнения.

## Внутренний synthetic core

Целевой баланс классов:

- `fraud`: 40
- `suspicious`: 20
- `safe`: 30

Этот баланс зафиксирован в [dataset_plan.json](/Users/margogusarova/Documents/НИРС/data/00_specs/dataset_plan.json).

## Generator stage

На стадии генерации создаются диалоги по seed-брифам, а не в случайном режиме. Для каждого seed-брифа задаются:

- метка;
- сценарий;
- обязательные сигналы;
- дополнительные сигналы;
- запрещенные сигналы;
- сложность;
- stylistic notes.

Эти брифы лежат в [generation_seed_briefs.jsonl](/Users/margogusarova/Documents/НИРС/data/01_generator/seed_briefs/generation_seed_briefs.jsonl).

## Augmentator stage

После базовой генерации часть примеров расширяется аугментациями:

- `paraphrase`
- `subtle`
- `asr_noise`
- `scenario_variation`

Это нужно для эксперимента на устойчивость к переформулировкам и шуму.

## Validator stage

Каждый пример должен проходить автоматическую и ручную проверку:

- соответствует ли текст метке;
- отражены ли заявленные сигналы;
- нет ли персональных данных;
- нет ли противоречий в сценарии;
- пригоден ли пример для финального корпуса.

Для этого в проект добавлен скрипт [validate_dataset.py](/Users/margogusarova/Documents/НИРС/src/nirs_fraud/validate_dataset.py).

## Роль внешнего CSV

Файл [synthetic_fraud_dialogues_ru_v1.csv](/Users/margogusarova/Documents/НИРС/data/05_external_benchmark/raw/synthetic_fraud_dialogues_ru_v1.csv) теперь интерпретируется как:

- внешний benchmark;
- дополнительный тестовый набор;
- источник обсуждения coverage и domain shift;
- не основной internally generated dataset.

## Почему отдельные папки важны

Структура данных должна визуально отражать этапы исследования:

- `data/01_generator/` — что было сгенерировано;
- `data/02_augmentator/` — что было получено после аугментации;
- `data/03_validator/` — что прошло проверку и какие есть отчеты;
- `data/04_final_dataset/` — что в итоге вошло в основной набор;
- `data/05_external_benchmark/` — что используется только как внешний тест.

## Что уже готово

- каталог сценариев;
- каталог сигналов;
- seed-брифы для генерации;
- prompt-pack для generator / augmentator / validator;
- сборка internal synthetic core v0;
- нормализация external benchmark;
- manifest датасета.
