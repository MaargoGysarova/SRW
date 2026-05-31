from __future__ import annotations

from .taxonomy import signal_ids


QWEN_JSON_RULES = """
Критически важно:
- Верни только один JSON-объект.
- Не используй markdown, не добавляй ```json.
- Не добавляй пояснения до или после JSON.
- Все ключи и строковые значения должны быть в двойных кавычках.
- Не используй trailing commas.
""".strip()


SINGLE_LLM_PROMPT = """
Ты классификатор мошеннических диалогов.
Твоя задача: прочитать текст и вернуть JSON:
{
  "label": "fraud|suspicious|safe",
  "fraud_score": 0.0,
  "signals": ["..."],
  "explanation": "краткое объяснение"
}

Классы:
- fraud: явные признаки мошенничества или социальной инженерии
- suspicious: есть тревожные сигналы, но контекст недостаточно однозначен
- safe: признаков мошенничества нет
"""


GENERATOR_PROMPT = """
Ты LLM-генератор синтетических русскоязычных диалогов для исследования мошенничества.

На входе ты получаешь:
- label
- scenario
- required_signals
- optional_signals
- forbidden_signals
- difficulty
- style_notes

Сгенерируй один реалистичный диалог на русском языке и верни JSON:
{
  "id": "temporary_id",
  "label": "fraud|suspicious|safe",
  "scenario": "...",
  "text": "...",
  "signals": ["..."],
  "difficulty": "easy|medium|hard",
  "source": "synthetic_llm_generated",
  "language": "ru",
  "modality": "text"
}

Правила:
- Диалог должен быть правдоподобным и кратким.
- Диалог должен звучать естественно для русского языка, без канцелярита и англицизмов без необходимости.
- Используй 2-5 реплик, если сценарий не требует другого.
- Если это телефонный сценарий, явно разделяй реплики по ролям: "Оператор:", "Клиент:", "Следователь:" и т.д.
- Не добавляй персональные данные реальных людей.
- Для fraud и suspicious обязательно отражай заявленные сигналы в тексте.
- Для safe не используй мошеннические триггеры без необходимости.
- Не придумывай лишние сигналы, если они не соответствуют сценарию.
- Поле "signals" должно содержать только канонические signal ids.
"""


AUGMENTATOR_PROMPT = """
Ты LLM-аугментатор датасета.

На входе дан исходный диалог и тип аугментации:
- paraphrase
- subtle
- asr_noise
- scenario_variation

Верни JSON:
{
  "id": "temporary_aug_id",
  "base_id": "...",
  "augmentation_type": "...",
  "label": "fraud|suspicious|safe",
  "text": "...",
  "preserved_signals": ["..."],
  "notes": "..."
}

Требования:
- Сохраняй исходную метку.
- Сохраняй общий смысл и тип сценария.
- Не превращай safe в fraud и наоборот без явной причины.
- Для asr_noise вноси правдоподобные ошибки распознавания речи.
- Для paraphrase меняй формулировки, но не основную семантику.
- Для subtle делай признаки менее очевидными, но всё ещё различимыми для аналитика.
- Для scenario_variation меняй только обрамляющий контекст, а не целевой класс.
"""


VALIDATOR_PROMPT = """
Ты LLM-валидатор синтетических примеров.

Проверь пример по чек-листу:
1. Соответствует ли текст метке?
2. Есть ли заявленные сигналы?
3. Нет ли реальных персональных данных?
4. Нет ли логических противоречий сценария?
5. Годится ли пример для включения в датасет?

Верни JSON:
{
  "accept": true,
  "label_consistency": "ok|warning|fail",
  "signal_consistency": "ok|warning|fail",
  "privacy_check": "ok|warning|fail",
  "issues": ["..."],
  "recommended_fixes": ["..."]
}

Если пример невалиден, не переписывай его целиком, а укажи проблемы в `issues` и `recommended_fixes`.
"""


CHECKLIST_PROMPT = """
Проанализируй диалог по чек-листу сигналов мошенничества.

Сигналы:
""" + ", ".join(signal_ids()) + """

Сначала заполни найденные сигналы, затем вычисли fraud_score и класс.
"""


SELF_CHECK_PROMPT = """
Шаг 1. Дай первичную классификацию и объяснение.
Шаг 2. Попробуй опровергнуть собственный вывод:
- какие сигналы могли быть ложными?
- достаточно ли контекста?
- не является ли диалог обычным бытовым разговором?
Шаг 3. Выдай финальный JSON с обновленным классом.
"""


ENSEMBLE_PROMPT = """
Смоделируй три независимых мнения:
1. Осторожный аналитик.
2. Эксперт по банковому фроду.
3. Скептичный reviewer, который снижает false positives.

Пусть каждый даст label и короткое объяснение.
Затем верни итоговое голосование и агрегированный список сигналов.
"""


def format_generator_prompt(seed_brief: dict) -> str:
    return (
        GENERATOR_PROMPT.strip()
        + "\n\n"
        + QWEN_JSON_RULES
        + "\n\n"
        + "Входные параметры:\n"
        + f"- brief_id: {seed_brief['brief_id']}\n"
        + f"- label: {seed_brief['label']}\n"
        + f"- scenario: {seed_brief['scenario']}\n"
        + f"- target_count: {seed_brief['target_count']}\n"
        + f"- required_signals: {seed_brief['required_signals']}\n"
        + f"- optional_signals: {seed_brief['optional_signals']}\n"
        + f"- forbidden_signals: {seed_brief['forbidden_signals']}\n"
        + f"- difficulty: {seed_brief['difficulty']}\n"
        + f"- style_notes: {seed_brief['style_notes']}\n"
        + "\n"
        + "Сгенерируй один новый пример, совместимый с этой спецификацией.\n"
        + "Проверь перед ответом:\n"
        + "- что `label` совпадает с входной меткой;\n"
        + "- что `scenario` совпадает с входным сценарием;\n"
        + "- что `signals` содержит канонические ids;\n"
        + "- что `text` не пустой и выглядит как живой русский диалог."
    )


def format_augmentator_prompt(record: dict, augmentation_type: str) -> str:
    return (
        AUGMENTATOR_PROMPT.strip()
        + "\n\n"
        + QWEN_JSON_RULES
        + "\n\n"
        + "Исходный пример:\n"
        + f"{record}\n\n"
        + f"Тип аугментации: {augmentation_type}\n"
        + "Верни один JSON-объект без дополнительных пояснений.\n"
        + "Проверь перед ответом:\n"
        + "- что `label` сохранён;\n"
        + "- что `base_id` указывает на исходный пример;\n"
        + "- что `text` не дублирует исходник буквально, если тип не требует этого."
    )


def format_validator_prompt(record: dict) -> str:
    return (
        VALIDATOR_PROMPT.strip()
        + "\n\n"
        + QWEN_JSON_RULES
        + "\n\n"
        + "Проверяемый пример:\n"
        + f"{record}\n\n"
        + "Верни один JSON-объект без дополнительных пояснений.\n"
        + "Используй строгие оценки:\n"
        + "- `ok`, если всё соответствует;\n"
        + "- `warning`, если пример пограничный, но потенциально пригоден;\n"
        + "- `fail`, если пример не должен попадать в датасет."
    )
