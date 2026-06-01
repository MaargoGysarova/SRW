from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ScenarioDefinition:
    id: str
    title_ru: str
    description_ru: str
    allowed_labels: tuple[str, ...]


@dataclass(frozen=True)
class SignalDefinition:
    id: str
    description_ru: str


@dataclass(frozen=True)
class ArchitectureDefinition:
    id: str
    description_ru: str


SCENARIOS: tuple[ScenarioDefinition, ...] = (
    ScenarioDefinition(
        id="bank_security_call",
        title_ru="служба безопасности банка",
        description_ru="Мошенник представляется службой безопасности банка и требует срочных действий.",
        allowed_labels=("fraud",),
    ),
    ScenarioDefinition(
        id="fake_loan_application",
        title_ru="на вас оформляют кредит",
        description_ru="Жертве сообщают о якобы оформленном кредите или необходимости срочной отмены.",
        allowed_labels=("fraud",),
    ),
    ScenarioDefinition(
        id="safe_account_transfer",
        title_ru="переведите деньги на безопасный счёт",
        description_ru="Жертву убеждают перевести деньги на резервный или безопасный счёт.",
        allowed_labels=("fraud",),
    ),
    ScenarioDefinition(
        id="fake_police_call",
        title_ru="следователь / ФСБ / полиция",
        description_ru="Звонящий представляется следователем, полицией или силовым ведомством.",
        allowed_labels=("fraud",),
    ),
    ScenarioDefinition(
        id="secrecy_pressure",
        title_ru="никому не говорите, секретная операция",
        description_ru="Сценарий секретности и давления, когда жертву просят никому не сообщать о разговоре.",
        allowed_labels=("fraud",),
    ),
    ScenarioDefinition(
        id="fake_delivery",
        title_ru="доставка цветов / заказ / курьер",
        description_ru="Подозрительная доставка или курьерский сценарий с нестандартным подтверждением.",
        allowed_labels=("suspicious", "fraud"),
    ),
    ScenarioDefinition(
        id="financial_number_change",
        title_ru="изменение финансового номера",
        description_ru="Сообщение о смене финансового номера или критичных реквизитов.",
        allowed_labels=("fraud",),
    ),
    ScenarioDefinition(
        id="relative_emergency",
        title_ru="мама, я сбил человека",
        description_ru="Эмоциональное давление через беду родственника и срочный перевод денег.",
        allowed_labels=("fraud",),
    ),
    ScenarioDefinition(
        id="phone_number_extension",
        title_ru="продление номера",
        description_ru="Продление номера или SIM-карты с запросом кода или срочных действий.",
        allowed_labels=("suspicious", "fraud"),
    ),
    ScenarioDefinition(
        id="voting_link_phishing",
        title_ru="проголосуйте за племянницу",
        description_ru="Фишинговая ссылка под видом голосования, конкурса или просьбы знакомого.",
        allowed_labels=("suspicious", "fraud"),
    ),
    ScenarioDefinition(
        id="fake_support_app_install",
        title_ru="установка приложения удалённого доступа",
        description_ru="Под видом помощи жертву просят установить приложение удалённого доступа или показать экран.",
        allowed_labels=("fraud",),
    ),
    ScenarioDefinition(
        id="investment_scam",
        title_ru="инвестиции / быстрый доход",
        description_ru="Обещание быстрого дохода и давление на срочный перевод денег.",
        allowed_labels=("fraud",),
    ),
)


SIGNALS: tuple[SignalDefinition, ...] = (
    SignalDefinition("urgency", "срочность: «прямо сейчас», «немедленно»"),
    SignalDefinition("pressure", "давление, запугивание"),
    SignalDefinition("bank_impersonation", "представляется банком"),
    SignalDefinition("government_impersonation", "представляется госорганом"),
    SignalDefinition("police_impersonation", "представляется следователем / полицией"),
    SignalDefinition("sms_code_request", "просит код из СМС"),
    SignalDefinition("password_request", "просит пароль"),
    SignalDefinition("card_data_request", "просит данные карты"),
    SignalDefinition("loan_fraud", "оформление / отмена кредита"),
    SignalDefinition("safe_account_transfer", "перевод на «безопасный счёт»"),
    SignalDefinition("secrecy", "просит никому не говорить"),
    SignalDefinition("do_not_hang_up", "просит не класть трубку"),
    SignalDefinition("instruction_to_lie", "просит соврать банку / оператору"),
    SignalDefinition("remote_access_app", "просит установить приложение"),
    SignalDefinition("phishing_link", "просит перейти по ссылке"),
    SignalDefinition("trust_building", "называет личные данные, операции, суммы"),
    SignalDefinition("voice_biometrics_abuse", "просит диктовать фразы роботу"),
    SignalDefinition("asr_noise", "ошибки распознавания речи"),
)


ARCHITECTURES: tuple[ArchitectureDefinition, ...] = (
    ArchitectureDefinition("rules_baseline", "простые правила по ключевым словам"),
    ArchitectureDefinition("single_llm", "одна LLM классифицирует текст"),
    ArchitectureDefinition("llm_checklist", "LLM анализирует по чек-листу признаков"),
    ArchitectureDefinition("llm_self_check", "LLM сначала даёт ответ, потом проверяет себя"),
    ArchitectureDefinition("llm_ensemble", "несколько независимых LLM/промптов голосуют"),
)


def scenarios_as_json() -> dict:
    return {"scenarios": [asdict(item) for item in SCENARIOS]}


def signals_as_json() -> list[dict]:
    return [asdict(item) for item in SIGNALS]


def architectures_as_json() -> dict:
    return {"architectures": [asdict(item) for item in ARCHITECTURES]}


def signal_ids() -> list[str]:
    return [item.id for item in SIGNALS]
