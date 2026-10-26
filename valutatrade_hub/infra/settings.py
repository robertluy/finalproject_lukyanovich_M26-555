import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class SettingsLoader:
    """Единственный экземпляр настроек приложения."""

    _instance = None

    def __new__(cls):
        # Singleton через __new__: простой контроль создания экземпляра.
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._load()
            cls._instance = instance
        return cls._instance

    def _load(self):
        """Прочитать настройки и подготовить абсолютные пути."""
        with (PROJECT_ROOT / "pyproject.toml").open("rb") as file:
            config = tomllib.load(file)

        self._settings = config["tool"]["valutatrade"].copy()
        data_dir = PROJECT_ROOT / self._settings["data_dir"]
        logs_dir = PROJECT_ROOT / self._settings["logs_dir"]

        self._settings.update(
            data_dir=data_dir,
            logs_dir=logs_dir,
            users_file=data_dir / "users.json",
            portfolios_file=data_dir / "portfolios.json",
            rates_file=data_dir / "rates.json",
            history_file=data_dir / "exchange_rates.json",
        )

    def get(self, key: str, default=None):
        """Получить настройку или значение по умолчанию."""
        return self._settings.get(key, default)