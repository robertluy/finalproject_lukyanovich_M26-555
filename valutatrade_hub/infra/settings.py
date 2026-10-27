import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SETTINGS = {
    "data_dir": "data",
    "logs_dir": "logs",
    "rates_ttl_seconds": 60,
    "default_base_currency": "USD",
    "log_format": "text",
    "log_level": "INFO",
    "log_max_bytes": 1_000_000,
    "log_backup_count": 3,
    "rates_update_interval_seconds": 60,
}


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
        """Загрузить настройки проекта или стандартные настройки пакета."""
        project_root = PROJECT_ROOT
        if not (project_root / "pyproject.toml").is_file():
            project_root = Path.cwd()

        self._settings = DEFAULT_SETTINGS.copy()
        config_path = project_root / "pyproject.toml"
        if config_path.is_file():
            with config_path.open("rb") as file:
                config = tomllib.load(file)
            self._settings.update(config.get("tool", {}).get("valutatrade", {}))

        data_dir = project_root / self._settings["data_dir"]
        logs_dir = project_root / self._settings["logs_dir"]

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