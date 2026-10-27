import argparse
import time

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import configure_logging
from valutatrade_hub.parser_service.updater import RatesUpdater


def run_scheduler(
    interval_seconds: int | None = None,
    source: str | None = None,
) -> None:
    """Повторять обновления через заданный интервал до остановки пользователем."""
    if interval_seconds is None:
        interval_seconds = SettingsLoader().get("rates_update_interval_seconds", 60)
    if (
        isinstance(interval_seconds, bool)
        or not isinstance(interval_seconds, int)
        or interval_seconds <= 0
    ):
        raise ValueError("Интервал должен быть целым числом больше нуля")

    configure_logging()
    updater = RatesUpdater()
    print(f"Интервал обновления: {interval_seconds} сек. Остановка: Ctrl+C")

    try:
        while True:
            try:
                result = updater.run_update(source)
            except ApiRequestError as error:
                print(f"Ошибка обновления: {error}")
            else:
                print(
                    f"Обновлено пар: {result['updated_pairs']}. "
                    f"Время: {result['last_refresh']}"
                )
                for name, error in result["errors"].items():
                    print(f"Предупреждение — {name}: {error}")

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nПланировщик остановлен")


def main() -> None:
    """Обработать параметры запуска планировщика."""
    parser = argparse.ArgumentParser(description="Периодическое обновление курсов")
    parser.add_argument("--interval", type=int, help="Интервал в секундах")
    parser.add_argument("--source", choices=("coingecko", "exchangerate"))
    args = parser.parse_args()

    try:
        run_scheduler(args.interval, args.source)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Ошибка: {error}\n")


if __name__ == "__main__":
    main()