# Работа с open-source LLM

## Идея

Датасет создается не вручную внутри Python-кода, а через отдельный слой open-source LLM.

Поддерживаются три этапа:

- `generator`
- `augmentator`
- `validator`

## Что уже сделано

Добавлен универсальный раннер:

- `src/nirs_fraud/llm/run_open_source_llm.py`

Он умеет:

- собирать запросы из брифов;
- экспортировать готовые запросы в `jsonl`;
- напрямую загружать модель через `transformers`;
- извлекать JSON из markdown-блоков и лишнего текста;
- исправлять типичные ошибки формата в ответах модели;
- нормализовать ответы к канонической схеме каждого этапа;
- сохранять результаты по этапным папкам.

## Куда что пишется

### Generator

- вход: `data/01_generator/seed_briefs/generation_seed_briefs.jsonl`
- запросы: `data/01_generator/requests/generator_requests_v0.jsonl`
- ответы модели: `data/01_generator/outputs/internal_generated_candidates_v0.jsonl`

### Augmentator

- вход: `data/01_generator/outputs/internal_generated_candidates_v0.jsonl`
- запросы: `data/02_augmentator/requests/augmentator_requests_v0.jsonl`
- непроверенные ответы модели: `data/02_augmentator/outputs/augmentation_subset_v0.jsonl`
- проверенный набор после фильтрации: `data/02_augmentator/outputs/augmentation_subset_clean_v1.jsonl`
- отклоненные аугментации: `data/02_augmentator/outputs/augmentation_subset_rejected_v1.jsonl`

### Validator

- вход: `data/01_generator/outputs/internal_generated_candidates_v0.jsonl`
- запросы: `data/03_validator/requests/validator_requests_v0.jsonl`
- ответы модели: `data/03_validator/outputs/validator_decisions_v0.jsonl`

## Рекомендуемый старт

Сначала можно не запускать модель, а просто экспортировать запросы:

```bash
python3 -m src.nirs_fraud.llm.run_open_source_llm generator --backend export
python3 -m src.nirs_fraud.llm.run_open_source_llm augmentator --backend export
python3 -m src.nirs_fraud.llm.run_open_source_llm validator --backend export
```

## Основной рекомендуемый вариант

Пример команды:

```bash
python3 -m src.nirs_fraud.llm.run_open_source_llm generator --backend transformers --model Qwen/Qwen2.5-3B-Instruct
```

Текущий основной вариант в проекте:

- модель: `Qwen/Qwen2.5-3B-Instruct`
- `max_new_tokens`: `700`
- `temperature`: `0.2`

Если понадобится другая open-source модель, достаточно заменить `--model` на другой идентификатор Hugging Face или локальный путь к модели.
