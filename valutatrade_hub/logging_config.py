import logging
import logging.config
import os
from pathlib import Path


def setup_logging():
    """
    Настраивает логирование для приложения.
    - Вывод в консоль (INFO и выше).
    - Вывод в файл (DEBUG и выше, с ротацией).
    - Единый формат сообщений.
    """
    # Создаём директорию для логов, если её нет
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Конфигурация логирования
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(funcName)s: %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": log_dir / "app.log",
                "maxBytes": 10_485_760,  # 10 МБ
                "backupCount": 3,
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "": {  # корневой логгер
                "handlers": ["console", "file"],
                "level": "DEBUG",
                "propagate": False
            }
        }
    }

    # Применяем конфигурацию
    logging.config.dictConfig(logging_config)
    logging.info("Логирование настроено.")