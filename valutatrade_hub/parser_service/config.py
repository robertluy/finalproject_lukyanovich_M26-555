import os
from dataclasses import dataclass, field
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader

FIAT_CURRENCIES = ("EUR", "GBP", "RUB")
CRYPTO_CURRENCIES = ("BTC", "ETH", "SOL")
CRYPTO_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}


@dataclass(frozen=True)
class ParserConfig:
    """Настройки API-клиентов и файлов с курсами."""

    exchangerate_api_key: str = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY", "").strip(),
        repr=False,
    )
    coingecko_url: str = "https://api.coingecko.com/api/v3/simple/price"
    exchangerate_api_url: str = "https://v6.exchangerate-api.com/v6"
    base_currency: str = "USD"
    request_timeout: int = 10
    rates_file_path: Path = field(
        default_factory=lambda: SettingsLoader().get("rates_file")
    )
    history_file_path: Path = field(
        default_factory=lambda: SettingsLoader().get("history_file")
    )