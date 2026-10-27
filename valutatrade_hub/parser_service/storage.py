import json
from datetime import datetime, timezone
from pathlib import Path

from valutatrade_hub.parser_service.config import ParserConfig


class RatesStorage:
    """Хранить последние курсы и историю их получения в JSON."""

    def __init__(self, config: ParserConfig | None = None):
        self.config = config if config is not None else ParserConfig()

    @staticmethod
    def _read_json(path: Path, default):
        """Прочитать JSON или вернуть начальное значение для нового файла."""
        try:
            with path.open(encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            return default
        except (json.JSONDecodeError, UnicodeError):
            raise ValueError(f"Некорректный JSON в файле {path.name}") from None

        if not isinstance(data, type(default)):
            raise ValueError(f"Неверная структура файла {path.name}")
        return data

    @staticmethod
    def _write_json(path: Path, data):
        """Записать JSON через временный файл и атомарную замену."""
        text = json.dumps(data, ensure_ascii=False, indent=4, allow_nan=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        try:
            temporary_path.write_text(text, encoding="utf-8")
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def load_cache(self) -> dict:
        """Прочитать кеш последних курсов."""
        cache = self._read_json(
            self.config.rates_file_path,
            {"pairs": {}, "last_refresh": None},
        )
        if not isinstance(cache.get("pairs"), dict):
            raise ValueError("В кеше курсов отсутствует словарь pairs")
        return cache

    def load_history(self) -> list:
        """Прочитать историю обновлений."""
        return self._read_json(self.config.history_file_path, [])

    def save_rates(
        self,
        rates: dict[str, float],
        source: str,
        timestamp: str | None = None,
    ) -> int:
        """Сохранить проверенные курсы API, сохраняя свежие значения в кеше."""
        if not rates:
            return 0

        moment = (
            datetime.now(timezone.utc)
            if timestamp is None
            else datetime.fromisoformat(timestamp)
        )
        if moment.utcoffset() is None:
            raise ValueError("Время обновления должно содержать часовой пояс")
        moment = moment.astimezone(timezone.utc)
        timestamp = moment.isoformat()

        cache = self.load_cache()
        history = self.load_history()
        known_ids = {record["id"] for record in history}
        updated = 0

        for pair, rate in rates.items():
            from_currency, to_currency = pair.split("_")
            record_id = f"{pair}_{timestamp}"
            if record_id not in known_ids:
                history.append({
                    "id": record_id,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": rate,
                    "timestamp": timestamp,
                    "source": source,
                })
                known_ids.add(record_id)

            previous = cache["pairs"].get(pair)
            if previous is None or moment > datetime.fromisoformat(
                previous["updated_at"]
            ):
                cache["pairs"][pair] = {
                    "rate": rate,
                    "updated_at": timestamp,
                    "source": source,
                }
                updated += 1

        previous_refresh = cache.get("last_refresh")
        if previous_refresh is None or moment > datetime.fromisoformat(
            previous_refresh
        ):
            cache["last_refresh"] = timestamp

        self._write_json(self.config.history_file_path, history)
        self._write_json(self.config.rates_file_path, cache)
        return updated