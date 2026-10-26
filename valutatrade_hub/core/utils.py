# Учебные фиксированные курсы: стоимость единицы валюты в USD.
EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 1.0786,
    "GBP": 1.25,
    "RUB": 0.01016,
    "BTC": 59337.21,
    "ETH": 3720.0,
    "SOL": 145.12,
}


def normalize_currency_code(code: str) -> str:
    """Проверить формат и привести код валюты к верхнему регистру."""
    if not isinstance(code, str):
        raise ValueError("Код валюты должен быть строкой")
    code = code.strip().upper()
    if not 2 <= len(code) <= 5 or not code.isascii() or not code.isalnum():
        raise ValueError("Код валюты должен содержать от 2 до 5 букв или цифр")
    return code


def get_exchange_rate(from_code: str, to_code: str = "USD") -> float:
    """Получить учебный курс: сколько to_code стоит одна from_code."""
    from_code = normalize_currency_code(from_code)
    to_code = normalize_currency_code(to_code)
    for code in (from_code, to_code):
        if code not in EXCHANGE_RATES:
            raise ValueError(f"Неизвестная валюта '{code}'")
    return EXCHANGE_RATES[from_code] / EXCHANGE_RATES[to_code]