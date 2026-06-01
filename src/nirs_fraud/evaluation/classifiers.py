from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


KEYWORDS = {
    "bank_impersonation": ["служба безопасности банка", "кредитного отдела банка", "техподдержка банка", "защиты счета"],
    "government_impersonation": ["госуслуг", "госпортале", "центробанка"],
    "police_impersonation": ["следователь", "полиция", "фсб", "спецоперация"],
    "urgency": ["срочно", "прямо сейчас", "немедленно"],
    "pressure": ["деньги уйдут", "выполняйте", "обязаны", "место осталось одно", "иначе сим-карта отключится"],
    "sms_code_request": ["код из смс", "цифры из уведомления", "код подтверждения", "одноразовый пароль", "код"],
    "password_request": ["пароль из сообщения", "введите пароль", "одноразовый пароль"],
    "card_data_request": ["данные карты", "реквизиты карты", "последние цифры карты", "номер карты"],
    "loan_fraud": ["заявка на кредит", "отмены кредита", "оформление кредита", "кредит"],
    "safe_account_transfer": ["безопасный счет", "резервный счет", "перевести средства"],
    "secrecy": ["никому не говорите", "не рассказывайте никому", "секрет"],
    "do_not_hang_up": ["не кладите трубку", "не отключайтесь", "оставайтесь на линии"],
    "instruction_to_lie": ["скажите, что перевод делаете сами", "соврать", "подтвердите, что это ваш перевод"],
    "remote_access_app": ["установите приложение", "покажите экран", "удаленного доступа"],
    "phishing_link": ["перейдите по ссылке", "вот ссылка", "жми на ссылку"],
    "trust_building": ["я вижу подозрительную операцию", "127 тысяч", "ваш аккаунт", "на ваше имя", "финансовый номер", "гарантированным доходом"],
    "voice_biometrics_abuse": ["повторить фразу", "соединю с роботом", "голосового подтверждения"],
}

LABEL_TO_INDEX = {"safe": 0, "suspicious": 1, "fraud": 2}


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def detect_signals(text: str) -> list[str]:
    lowered = text.lower()
    found = []
    for signal, phrases in KEYWORDS.items():
        if any(phrase in lowered for phrase in phrases):
            found.append(signal)
    return found


def rules_baseline(text: str) -> tuple[str, list[str], float]:
    signals = detect_signals(text)
    strong = {"sms_code_request", "password_request", "card_data_request", "safe_account_transfer", "remote_access_app"}
    fraud_hits = len(strong.intersection(signals))
    if fraud_hits >= 1 and len(signals) >= 2:
        return "fraud", signals, min(0.55 + 0.08 * len(signals), 0.98)
    if len(signals) >= 1:
        return "suspicious", signals, min(0.35 + 0.05 * len(signals), 0.75)
    return "safe", signals, 0.08


def checklist_proxy(text: str) -> tuple[str, list[str], float]:
    signals = detect_signals(text)
    lowered = text.lower()
    score = 0.0
    weights = {
        "bank_impersonation": 0.18,
        "government_impersonation": 0.18,
        "police_impersonation": 0.18,
        "urgency": 0.08,
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
        ("sms_code_request" in signals and ("bank_impersonation" in signals or "government_impersonation" in signals or "card_data_request" in signals or "loan_fraud" in signals))
        or ("remote_access_app" in signals and "bank_impersonation" in signals)
        or ("instruction_to_lie" in signals)
        or ("voice_biometrics_abuse" in signals and ("sms_code_request" in signals or "loan_fraud" in signals))
        or ("police_impersonation" in signals and "secrecy" in signals)
        or ("police_impersonation" in signals and "do_not_hang_up" in signals)
        or ("sms_code_request" in signals and "trust_building" in signals and "pressure" in signals)
        or ("безопасный счет" in lowered)
        or ("30 процентов в неделю" in lowered)
    )

    if strong_combo or score >= 0.42:
        return "fraud", signals, score
    if score >= 0.14:
        return "suspicious", signals, score
    return "safe", signals, score


def self_check_proxy(text: str) -> tuple[str, list[str], float]:
    label, signals, score = checklist_proxy(text)
    lowered = text.lower()
    safe_context = ["спасибо", "завтра", "буду", "до скольки", "встретимся", "напоминаем о записи"]
    strong_signals = {"sms_code_request", "password_request", "card_data_request", "safe_account_transfer", "remote_access_app", "instruction_to_lie"}
    if label == "suspicious" and len(signals) == 1 and not strong_signals.intersection(signals) and any(token in lowered for token in safe_context):
        return "safe", signals, max(0.05, score - 0.15)
    if label == "fraud" and "trust_building" in signals and len(signals) == 1:
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
