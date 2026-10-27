import logging

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Обновлять курсы из доступных источников и сохранять результаты."""

    def __init__(
        self,
        config: ParserConfig | None = None,
        clients: dict[str, BaseApiClient] | None = None,
        storage: RatesStorage | None = None,
    ):
        self.config = config if config is not None else ParserConfig()
        self.clients = clients if clients is not None else {
            "coingecko": CoinGeckoClient(self.config),
            "exchangerate": ExchangeRateApiClient(self.config),
        }
        self.storage = storage if storage is not None else RatesStorage(self.config)
        self.logger = logging.getLogger("valutatrade.parser")

    def run_update(self, source: str | None = None) -> dict:
        """Обновить все источники или один выбранный, учитывая частичные сбои."""
        if source is not None and source not in self.clients:
            raise ValueError(f"Неизвестный источник курсов: {source}")

        selected = (
            self.clients if source is None else {source: self.clients[source]}
        )
        self.logger.info("Начало обновления: source=%s", source or "all")
        updated_pairs = 0
        successful_sources = []
        errors = {}

        for name, client in selected.items():
            self.logger.info("Запрос курсов: source=%s", name)
            try:
                rates = client.fetch_rates()
                if not rates:
                    raise ApiRequestError(f"{client.source}: получен пустой ответ")
            except ApiRequestError as error:
                errors[name] = str(error)
                self.logger.warning("Ошибка источника %s: %s", name, error)
                continue

            try:
                count = self.storage.save_rates(rates, client.source)
            except (OSError, ValueError):
                self.logger.exception("Ошибка сохранения курсов: source=%s", name)
                raise

            updated_pairs += count
            successful_sources.append(name)
            self.logger.info(
                "Курсы сохранены: source=%s received=%s updated=%s",
                name,
                len(rates),
                count,
            )

        if not successful_sources:
            self.logger.error("Обновление не удалось: все источники недоступны")
            details = "; ".join(errors.values()) or "не настроены источники"
            raise ApiRequestError(f"Не удалось обновить курсы. {details}")

        result = {
            "updated_pairs": updated_pairs,
            "sources": successful_sources,
            "errors": errors,
            "last_refresh": self.storage.load_cache().get("last_refresh"),
        }
        self.logger.info(
            "Обновление завершено: updated=%s errors=%s",
            updated_pairs,
            len(errors),
        )
        return result