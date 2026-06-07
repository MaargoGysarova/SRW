# NIRS Fraud Dialog Baseline

Baseline-репозиторий для НИРС по теме выявления мошенничества в русскоязычных текстовых и аудиотранскрибированных диалогах.

## Что внутри

- `data/00_specs/` — спецификации сценариев, сигналов и плана датасета.
- `data/01_generator/` — seed-брифы и выходы генератора.
- `data/02_augmentator/` — сырые, валидированные и отбракованные аугментации.
- `data/03_validator/` — manifest и отчёты валидации.
- `data/04_final_dataset/` — итоговый внутренний датасет для экспериментов.
- `data/05_external_benchmark/` — внешний benchmark отдельно от основного датасета, сейчас под Kaggle subset.
- `data/06_audio/` — реальные и синтетические аудио.
- `src/nirs_fraud/catalog/` — таксономии и каталоги.
- `src/nirs_fraud/pipeline/` — сборка, очистка и валидация датасета.
- `src/nirs_fraud/llm/` — промпты и раннеры для моделей.
- `src/nirs_fraud/evaluation/` — классификаторы, метрики и экспериментальные раннеры.
- `src/nirs_fraud/research/` — дизайн экспериментов, гипотезы и экспорт спецификаций.
- `docs/presentation_outline.md` — структура презентации.
- `docs/experiment_01_baseline_classification.md` — оформленный текст для базового эксперимента.
- `docs/experiment_02_augmentation_robustness.md` — оформленный текст для эксперимента на устойчивость.
- `docs/research_hypotheses_nirs.md` — основные гипотезы для отчёта НИРС.
- `docs/supervisor_summary.md` — короткое объяснение руководителю.
- `docs/dataset_methodology.md` — методология сбора данных.
- `docs/thesis_dataset_section.md` — готовый текст для раздела НИРС про датасет.
- `docs/external_kaggle_benchmark.md` — схема внешнего Kaggle benchmark.

## Честная граница текущей версии

Репозиторий уже позволяет:

- собрать артефакты по отдельным этапам `generator -> augmentator -> validator -> final dataset`;
- собрать внутренний synthetic core и отдельно оформить внешний benchmark;
- описать pipeline `generator -> augmentator -> validator -> final dataset`;
- прогнать rule-based baseline;
- прогнать checklist/self-check/ensemble proxy-классификаторы без внешнего API;
- получить `predictions.csv` и `metrics.csv`;
- использовать готовые промпты для реального LLM-запуска позже.
- экспортировать jobs для open-source LLM или запускать их через прямую загрузку модели в `transformers`.

Важно:

- тексты диалогов больше не хранятся внутри `pipeline/build_dataset.py`;
- `pipeline/build_dataset.py` читает данные из этапных папок и собирает итоговый датасет;
- основной источник внутренних примеров сейчас: `data/01_generator/outputs/internal_generated_candidates_v0.jsonl`.
- рекомендуемый open-source baseline для генерации сейчас: `Qwen/Qwen2.5-3B-Instruct`.

Пока без сетевого доступа здесь **не выполняются реальные вызовы внешней LLM**. Поэтому `single_llm`, `llm_checklist`, `llm_self_check` и `llm_ensemble` в коде сейчас представлены как **proxy-версии baseline-логики**, а промпты и интерфейс вынесены отдельно для дальнейшего подключения API.

## Структура данных

Для НИРС теперь различаются два набора:

- `internal_synthetic_core` — основной внутренний датасет;
- `validated_augmentation_subset` — валидированный набор аугментаций для эксперимента на устойчивость;
- `external_benchmark` — внешний датасет для дополнительного теста.

И они лежат в отдельных этапных папках:

- генерация: `data/01_generator/`
- аугментация: `data/02_augmentator/`
- валидация: `data/03_validator/`
- итоговый датасет: `data/04_final_dataset/`
- внешний benchmark: `data/05_external_benchmark/`
- аудио: `data/06_audio/`

Для аугментаций внутри `data/02_augmentator/` используются три состояния:

- `augmentation_subset_v0.jsonl` — raw augmentation subset;
- `augmentation_subset_clean_v1.jsonl` — validated augmentation subset;
- `augmentation_subset_rejected_v1.jsonl` — rejected augmentations.

Целевой баланс внутреннего core:

- `fraud`: 40
- `suspicious`: 20
- `safe`: 30

## Быстрый старт

```bash
python3 -m src.nirs_fraud.pipeline.clean_data
python3 -m src.nirs_fraud.pipeline.build_dataset
python3 -m src.nirs_fraud.pipeline.validate_dataset
python3 -m src.nirs_fraud.evaluation.run_experiments
```

Результаты появятся в `outputs/`:

- `predictions.csv`
- `metrics.csv`
- `summary.md`

## Целевая логика НИРС

```text
text/audio
  -> ASR (для аудио)
  -> checklist-based analysis
  -> fraud score
  -> label: fraud / suspicious / safe
  -> explanation
```

## Что показывать на презентации

- постановку задачи;
- структуру датасета и таксономию сигналов;
- сравнение baseline-архитектур;
- устойчивость к paraphrase / subtle / asr-noise;
- ограничения и план перехода к диплому.

## Реальные аудио

Для демонстрации на настоящих звонках складывай файлы в:

- `data/audio/real/`

Рекомендуемый минимальный набор метаданных на каждый файл:

- `id`
- `source_url` или `source_note`
- `label`
- `scenario`
- `duration_sec`
- `asr_transcript`
- `manual_transcript`
- `notes`

Лучше использовать 3-4 записи как **качественную валидацию**, а не как основной набор для метрик.
