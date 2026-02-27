import json
import logging
import logging.config
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter for structured application logs."""

    RESERVED = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName", "processName",
        "process", "message", "asctime",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    formatter_name = "json" if log_format.lower() == "json" else "standard"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                },
                "json": {
                    "()": "app.utils.logging.JsonFormatter",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter_name,
                    "level": log_level.upper(),
                }
            },
            "root": {
                "handlers": ["default"],
                "level": log_level.upper(),
            },
        }
    )
