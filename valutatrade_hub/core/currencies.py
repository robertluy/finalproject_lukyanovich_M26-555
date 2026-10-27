import math
from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.utils import normalize_currency_code


class Currency(ABC):
    """Базовый класс валюты."""

    def __init__(self, name: str, code: str):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустым")
        self.name = name.strip()
        self.code = normalize_currency_code(code)

    @abstractmethod
    def get_display_info(self) -> str:
        """Вернуть описание валюты."""
        raise NotImplementedError


class FiatCurrency(Currency):
    """Фиатная валюта со страной или зоной выпуска."""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна или зона выпуска не может быть пустой")
        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        """Вернуть описание фиатной валюты."""
        return (
            f"[FIAT] {self.code} — {self.name} "
            f"(Issuing: {self.issuing_country})"
        )


class CryptoCurrency(Currency):
    """Криптовалюта с алгоритмом и известной капитализацией."""

    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float = 0.0,
    ):
        super().__init__(name, code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")
        if (
            isinstance(market_cap, bool)
            or not isinstance(market_cap, (int, float))
            or not math.isfinite(market_cap)
            or market_cap < 0
        ):
            raise ValueError("Капитализация должна быть неотрицательным числом")
        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        """Вернуть описание криптовалюты."""
        market_cap = f"{self.market_cap:.2e}" if self.market_cap else "нет данных"
        return (
            f"[CRYPTO] {self.code} - {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {market_cap})"
        )


_CURRENCIES = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "GBP": FiatCurrency("Pound Sterling", "GBP", "United Kingdom"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256"),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Proof of Stake"),
    "SOL": CryptoCurrency("Solana", "SOL", "Proof of History"),
}


def get_currency(code: str) -> Currency:
    """Найти валюту по коду или вызвать CurrencyNotFoundError."""
    code = normalize_currency_code(code)
    if code not in _CURRENCIES:
        raise CurrencyNotFoundError(code)
    return _CURRENCIES[code]


def get_supported_codes() -> list[str]:
    """Вернуть отсортированный список поддерживаемых кодов."""
    return sorted(_CURRENCIES)