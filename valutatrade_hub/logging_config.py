import logging
import time
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


def configure_logging():
    """Настроить текстовые логи с временем UTC и ротацией файлов."""
    settings = SettingsLoader()
    logs_dir = settings.get("logs_dir")
    logs_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(levelname)s %(asctime)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    formatter.converter = time.gmtime

    for name in ("actions", "parser"):
        logger = logging.getLogger(f"valutatrade.{name}")
        logger.setLevel(settings.get("log_level", "INFO"))
        logger.propagate = False
        if logger.handlers:
            continue

        handler = RotatingFileHandler(
            logs_dir / f"{name}.log",
            maxBytes=settings.get("log_max_bytes", 1_000_000),
            backupCount=settings.get("log_backup_count", 3),
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)