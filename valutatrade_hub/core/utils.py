import math
from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


def normalize_currency_code(code: str) -> str:
    """Привести код валюты к единому формату."""
    if not isinstance(code, str):
        raise ValueError("Код валюты должен быть строкой")
    code = code.strip().upper()
    if not 2 <= len(code) <= 5 or not code.isascii() or not code.isalnum():
        raise ValueError("Код валюты должен содержать от 2 до 5 букв или цифр")
    return code


def _get_cached_rate(
    pairs: dict, from_code: str, to_code: str
) -> tuple[float, datetime | None, str]:
    """Прочитать прямой или обратный курс и проверить его срок действия."""
    if from_code == to_code:
        return 1.0, None, ""

    pair = f"{from_code}_{to_code}"
    reverse = False
    if pair not in pairs:
        pair = f"{to_code}_{from_code}"
        reverse = True
    if pair not in pairs:
        raise ApiRequestError(
            f"Нет курса {from_code}/{to_code}. Выполните update-rates"
        )

    record = pairs[pair]
    if not isinstance(record, dict):
        raise ValueError(f"Неверная запись курса {pair}")
    rate = record.get("rate")
    if (
        isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or not math.isfinite(rate)
        or rate <= 0
    ):
        raise ValueError(f"Некорректное значение курса {pair}")

    try:
        updated_at = datetime.fromisoformat(record["updated_at"])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"Некорректная дата курса {pair}") from None
    if updated_at.utcoffset() is None:
        raise ValueError(f"Дата курса {pair} должна содержать часовой пояс")

    age = (datetime.now(timezone.utc) - updated_at).total_seconds()
    ttl = SettingsLoader().get("rates_ttl_seconds", 60)
    if age >= ttl:
        raise ApiRequestError(
            f"Курс {pair} устарел (TTL {ttl} сек.). Выполните update-rates"
        )

    value = 1.0 / rate if reverse else float(rate)
    return value, updated_at, str(record.get("source", "неизвестен"))


def get_rate_info(from_code: str, to_code: str = "USD") -> dict:
    """Получить курс, источник и время обновления из кеша."""
    from valutatrade_hub.core.currencies import get_currency

    from_code = get_currency(from_code).code
    to_code = get_currency(to_code).code
    if from_code == to_code:
        return {
            "from_currency": from_code,
            "to_currency": to_code,
            "rate": 1.0,
            "reverse_rate": 1.0,
            "updated_at": None,
            "source": "совпадающие валюты",
        }

    pairs = DatabaseManager().read("rates").get("pairs", {})
    if not isinstance(pairs, dict):
        raise ValueError("В кеше курсов отсутствует словарь pairs")

    if f"{from_code}_{to_code}" in pairs or f"{to_code}_{from_code}" in pairs:
        rate, updated_at, source = _get_cached_rate(pairs, from_code, to_code)
    else:
        from_rate, from_time, from_source = _get_cached_rate(
            pairs, from_code, "USD"
        )
        to_rate, to_time, to_source = _get_cached_rate(pairs, to_code, "USD")
        rate = from_rate / to_rate
        updated_at = min(time for time in (from_time, to_time) if time is not None)
        source = ", ".join(
            dict.fromkeys(item for item in (from_source, to_source) if item)
        )

    return {
        "from_currency": from_code,
        "to_currency": to_code,
        "rate": rate,
        "reverse_rate": 1.0 / rate,
        "updated_at": updated_at.isoformat() if updated_at is not None else None,
        "source": source,
    }


def get_exchange_rate(from_code: str, to_code: str = "USD") -> float:
    """Получить числовое значение актуального курса."""
    return get_rate_info(from_code, to_code)["rate"]