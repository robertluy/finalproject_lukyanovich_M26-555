import math
from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import (
    CRYPTO_CURRENCIES,
    CRYPTO_ID_MAP,
    FIAT_CURRENCIES,
    ParserConfig,
)


class BaseApiClient(ABC):
    """Общий интерфейс получения курсов из внешнего API."""

    source = "API"

    def __init__(self, config: ParserConfig | None = None):
        self.config = config if config is not None else ParserConfig()

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Получить курсы в формате CODE_BASE → число."""
        raise NotImplementedError

    def _request_json(self, url: str, params: dict | None = None) -> dict:
        """Выполнить GET-запрос и проверить ответ."""
        try:
            response = requests.get(
                url,
                params=params,
                timeout=self.config.request_timeout,
            )
        except requests.Timeout:
            raise ApiRequestError(f"{self.source}: превышен таймаут") from None
        except requests.RequestException:
            raise ApiRequestError(f"{self.source}: сетевая ошибка") from None

        if response.status_code != 200:
            reasons = {
                401: "неверный API-ключ или нет доступа",
                403: "доступ запрещён",
                429: "превышен лимит запросов, повторите позже",
            }
            reason = reasons.get(
                response.status_code,
                f"HTTP {response.status_code}",
            )
            raise ApiRequestError(f"{self.source}: {reason}")

        try:
            data = response.json()
        except ValueError:
            raise ApiRequestError(
                f"{self.source}: ответ не является корректным JSON"
            ) from None

        if not isinstance(data, dict):
            raise ApiRequestError(f"{self.source}: неверная структура ответа")
        return data

    def _positive_rate(self, value, code: str) -> float:
        """Проверить числовое положительное значение курса."""
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ApiRequestError(f"{self.source}: некорректный курс для {code}")
        return float(value)


class CoinGeckoClient(BaseApiClient):
    """Получать цены криптовалют через CoinGecko."""

    source = "CoinGecko"

    def fetch_rates(self) -> dict[str, float]:
        """Получить стоимость криптовалют в базовой валюте."""
        base = self.config.base_currency.upper()
        params = {
            "ids": ",".join(CRYPTO_ID_MAP[code] for code in CRYPTO_CURRENCIES),
            "vs_currencies": base.lower(),
        }
        data = self._request_json(self.config.coingecko_url, params)

        rates = {}
        for code in CRYPTO_CURRENCIES:
            coin = data.get(CRYPTO_ID_MAP[code])
            if not isinstance(coin, dict):
                raise ApiRequestError(f"{self.source}: нет данных для {code}")
            rates[f"{code}_{base}"] = self._positive_rate(
                coin.get(base.lower()), code
            )
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Получать фиатные курсы через ExchangeRate-API."""

    source = "ExchangeRate-API"

    def fetch_rates(self) -> dict[str, float]:
        """Получить фиатные курсы, пересчитанные в направлении CODE_BASE."""
        key = self.config.exchangerate_api_key
        if not key:
            raise ApiRequestError("не задана переменная EXCHANGERATE_API_KEY")

        base = self.config.base_currency.upper()
        url = (
            f"{self.config.exchangerate_api_url.rstrip('/')}"
            f"/{key}/latest/{base}"
        )
        data = self._request_json(url)

        if data.get("result") != "success":
            reasons = {
                "invalid-key": "неверный API-ключ",
                "inactive-account": "подтвердите почту в аккаунте API",
                "quota-reached": "исчерпан лимит запросов",
            }
            reason = reasons.get(
                str(data.get("error-type")),
                "API вернул неуспешный ответ",
            )
            raise ApiRequestError(f"{self.source}: {reason}")

        if data.get("base_code") != base:
            raise ApiRequestError(f"{self.source}: неверная базовая валюта")
        values = data.get("conversion_rates")
        if not isinstance(values, dict):
            raise ApiRequestError(f"{self.source}: нет словаря conversion_rates")

        rates = {}
        for code in FIAT_CURRENCIES:
            value = self._positive_rate(values.get(code), code)
            rates[f"{code}_{base}"] = self._positive_rate(1.0 / value, code)
        return rates