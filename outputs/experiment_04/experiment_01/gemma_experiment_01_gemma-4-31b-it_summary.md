# Дополнительное исследование 1. Gemma API на Experiment 1

## Постановка

В качестве дополнительного исследования модель `gemma-4-31b-it` была протестирована через API на `Experiment 1` в конфигурации `single_llm`.

## Результат Gemma API

| Модель | Конфигурация | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| Gemma 4-31B API | `single_llm` | 0.647 | 0.676 | 0.714 | 0.694 | 12 | 10 |

## Сравнение с другими подходами на Experiment 1

| Подход | Конфигурация | F1 fraud |
|---|---|---:|
| Правила | baseline | 0.678 |
| Gemma 4-31B API | `single_llm` | 0.694 |
| Qwen 2.5-14B | `llm_self_check` | 0.835 |

## Интерпретация

- `Gemma API` показала результат немного выше правилового baseline.
- При этом `Gemma API single_llm` уступила `Qwen 2.5-14B` в конфигурации `llm_self_check`.
- Данное сравнение носит прикладной характер: для `Gemma API` в рамках работы был завершен прогон только в конфигурации `single_llm`.

## Связанный график

- `supplement_exp4_exp1_gemma.png`
