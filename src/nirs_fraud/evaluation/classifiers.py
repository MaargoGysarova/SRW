from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


SIGNAL_PATTERNS = {
    "bank_impersonation": [
        r"служб[аы]\s+безопасности\s+банк",
        r"(?:сотрудник|специалист|оператор)\s+банк",
        r"из\s+банк[ауы]?",
        r"техподдержк[аи]\s+банк",
        r"кредитн(?:ый|ого)\s+отдел[а]?\s+банк",
    ],
    "government_impersonation": [
        r"госуслуг",
        r"госпортал",
        r"госорган",
        r"центробанк",
        r"центральн(?:ый|ого)\s+банк",
    ],
    "police_impersonation": [
        r"следоват",
        r"\bполици",
        r"\bфсб\b",
        r"оперативн(?:ая|ой)\s+групп",
        r"силов(?:ое|ого)\s+ведомств",
    ],
    "urgency": [
        r"срочн",
        r"немедлен",
        r"прямо\s+сейчас",
        r"сегодня\b",
        r"не\s+теряя\s+времени",
    ],
    "pressure": [
        r"\bиначе\b",
        r"обязан[ыо]?",
        r"обязательн[оы]",
        r"уголовн",
        r"будут\s+последствия",
        r"средства\s+спиш",
        r"счет\s+заблок",
    ],
    "sms_code_request": [
        r"код(?:а)?\s+из\s+смс",
        r"код(?:а)?\s+подтвержден",
        r"одноразов(?:ый|ого)\s+парол",
        r"цифр(?:ы|у)\s+из\s+(?:сообщени|уведомлени)",
        r"код,\s+который\s+вам\s+пришел",
    ],
    "password_request": [
        r"\bпарол[ья]",
        r"введите\s+парол",
        r"сообщите\s+парол",
    ],
    "card_data_request": [
        r"данн(?:ые|ых)\s+карт",
        r"реквизит(?:ы|ов)\s+карт",
        r"номер\s+карт",
        r"последни(?:е|х)\s+цифр(?:ы|)\s+карт",
    ],
    "loan_fraud": [
        r"заявк[аи]\s+на\s+кредит",
        r"оформл\w*\s+кредит",
        r"отмен\w*\s+кредит",
        r"\bкредит\b",
    ],
    "safe_account_transfer": [
        r"безопасн(?:ый|ого)\s+счет",
        r"резервн(?:ый|ого)\s+счет",
        r"защищенн(?:ый|ого)\s+счет",
        r"перевед\w*\s+деньги\s+на\s+счет",
    ],
    "secrecy": [
        r"никому\s+не\s+говор",
        r"не\s+рассказывай?те?\s+никому",
        r"это\s+секретн",
        r"сохраните\s+это\s+в\s+тайне",
    ],
    "do_not_hang_up": [
        r"не\s+кладите\s+трубку",
        r"не\s+отключайт",
        r"оставайтесь\s+на\s+линии",
    ],
    "instruction_to_lie": [
        r"скажите,\s+что\s+перевод\s+делаете\s+сами",
        r"совр\w*",
        r"подтвердите,\s+что\s+это\s+ваш\s+перевод",
    ],
    "remote_access_app": [
        r"установит[ье]\s+приложени",
        r"покажите\s+экран",
        r"удаленн(?:ого|ый)\s+доступ",
        r"приложени[ея]\s+для\s+доступа",
    ],
    "phishing_link": [
        r"перейдите\s+по\s+ссылке",
        r"вот\s+ссылк",
        r"жми\s+на\s+ссылк",
        r"откройте\s+ссылк",
    ],
    "trust_building": [
        r"по\s+вашему\s+счету",
        r"по\s+вашей\s+карте",
        r"на\s+ваше\s+имя",
        r"ваш\s+аккаунт",
        r"ваш\s+финансовый\s+номер",
        r"подозрительн(?:ая|ую|ой)\s+операци",
    ],
    "voice_biometrics_abuse": [
        r"повторит[ье]\s+фраз",
        r"соединю\s+с\s+робот",
        r"голосов(?:ого|ое)\s+подтверждени",
    ],
}

LABEL_TO_INDEX = {"safe": 0, "suspicious": 1, "fraud": 2}
STRONG_SIGNALS = {
    "sms_code_request",
    "password_request",
    "card_data_request",
    "safe_account_transfer",
    "remote_access_app",
    "instruction_to_lie",
}


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def detect_signals(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for signal, patterns in SIGNAL_PATTERNS.items():
        if any(re.search(pattern, lowered) for pattern in patterns):
            found.append(signal)
    return found


def rules_baseline(text: str) -> tuple[str, list[str], float]:
    signals = detect_signals(text)
    fraud_hits = len(STRONG_SIGNALS.intersection(signals))
    impersonation_hits = len({"bank_impersonation", "government_impersonation", "police_impersonation"}.intersection(signals))

    if fraud_hits >= 1 and (len(signals) >= 2 or impersonation_hits >= 1):
        return "fraud", signals, min(0.50 + 0.08 * len(signals), 0.98)
    if len(signals) >= 1:
        return "suspicious", signals, min(0.30 + 0.05 * len(signals), 0.75)
    return "safe", signals, 0.08


def checklist_proxy(text: str) -> tuple[str, list[str], float]:
    signals = detect_signals(text)
    lowered = text.lower()
    score = 0.0
    weights = {
        "bank_impersonation": 0.16,
        "government_impersonation": 0.16,
        "police_impersonation": 0.17,
        "urgency": 0.07,
        "pressure": 0.08,
        "sms_code_request": 0.22,
        "password_request": 0.24,
        "card_data_request": 0.22,
        "loan_fraud": 0.14,
        "safe_account_transfer": 0.24,
        "secrecy": 0.10,
        "do_not_hang_up": 0.10,
        "instruction_to_lie": 0.25,
        "remote_access_app": 0.24,
        "phishing_link": 0.18,
        "trust_building": 0.06,
        "voice_biometrics_abuse": 0.20,
    }
    for signal in signals:
        score += weights.get(signal, 0.0)
    score = min(score, 0.99)

    strong_combo = (
        ("sms_code_request" in signals and {"bank_impersonation", "government_impersonation", "card_data_request", "loan_fraud"}.intersection(signals))
        or ("remote_access_app" in signals and "bank_impersonation" in signals)
        or ("instruction_to_lie" in signals)
        or ("voice_biometrics_abuse" in signals and {"sms_code_request", "loan_fraud"}.intersection(signals))
        or ("police_impersonation" in signals and {"secrecy", "do_not_hang_up", "pressure"}.intersection(signals))
        or ("safe_account_transfer" in signals)
        or (re.search(r"быстр\w+\s+доход", lowered) and "urgency" in signals)
    )

    if strong_combo or score >= 0.42:
        return "fraud", signals, score
    if score >= 0.14:
        return "suspicious", signals, score
    return "safe", signals, score


def self_check_proxy(text: str) -> tuple[str, list[str], float]:
    label, signals, score = checklist_proxy(text)
    lowered = text.lower()
    safe_context = [
        "спасибо",
        "завтра",
        "буду",
        "до скольки",
        "встретимся",
        "напоминаем о записи",
        "подъеду",
        "запись к врачу",
    ]
    if label == "suspicious" and len(signals) == 1 and not STRONG_SIGNALS.intersection(signals) and any(token in lowered for token in safe_context):
        return "safe", signals, max(0.05, score - 0.15)
    if label == "fraud" and signals == ["trust_building"]:
        return "suspicious", signals, max(0.20, score - 0.2)
    return label, signals, score


def ensemble_proxy(text: str) -> tuple[str, list[str], float]:
    votes = [
        rules_baseline(text),
        checklist_proxy(text),
        self_check_proxy(text),
    ]
    vote_counter = Counter(label for label, _, _ in votes)
    label = max(vote_counter.items(), key=lambda item: (item[1], LABEL_TO_INDEX[item[0]]))[0]
    merged_signals = sorted({signal for _, signals, _ in votes for signal in signals})
    avg_score = sum(score for _, _, score in votes) / len(votes)
    return label, merged_signals, round(avg_score, 3)


MODELS = {
    "rules_baseline": rules_baseline,
    "single_llm": rules_baseline,
    "llm_checklist": checklist_proxy,
    "llm_self_check": self_check_proxy,
    "llm_ensemble": ensemble_proxy,
}
