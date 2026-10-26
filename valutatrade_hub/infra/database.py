import json
from copy import deepcopy
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader

DEFAULT_DATA = {
    "users": [],
    "portfolios": [],
    "rates": {"pairs": {}, "last_refresh": None},
    "history": [],
}


class DatabaseManager:
    """Единственный экземпляр для работы с JSON-хранилищем."""

    _instance = None

    def __new__(cls):
        # Singleton через __new__, как в SettingsLoader.
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._settings = SettingsLoader()
            instance._initialize_files()
            cls._instance = instance
        return cls._instance

    def _get_path(self, name: str) -> Path:
        """Получить путь к одному из файлов хранилища."""
        if name not in DEFAULT_DATA:
            raise ValueError(f"Неизвестное хранилище '{name}'")
        return self._settings.get(f"{name}_file")

    def _initialize_files(self):
        """Создать отсутствующие файлы с начальными данными."""
        for name, default in DEFAULT_DATA.items():
            if not self._get_path(name).exists():
                self.write(name, default)

    def read(self, name: str) -> list | dict:
        """Прочитать данные из выбранного JSON-файла."""
        path = self._get_path(name)
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            return deepcopy(DEFAULT_DATA[name])
        except (json.JSONDecodeError, UnicodeError) as error:
            raise ValueError(
                f"Файл '{path.name}' содержит некорректный JSON"
            ) from error

        if not isinstance(data, type(DEFAULT_DATA[name])):
            raise ValueError(f"Неверный формат данных в '{path.name}'")
        return data

    def write(self, name: str, data: list | dict):
        """Сохранить данные через временный файл и замену исходного."""
        path = self._get_path(name)
        if not isinstance(data, type(DEFAULT_DATA[name])):
            raise ValueError(f"Неверный формат данных для '{name}'")

        text = json.dumps(
            data,
            ensure_ascii=False,
            indent=4,
            allow_nan=False,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".json.tmp")

        try:
            temp_path.write_text(text, encoding="utf-8")
            temp_path.replace(path)
        finally:
            temp_path.unlink(missing_ok=True)