from __future__ import annotations

import logging
import json
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import get_settings
from app.core.request_context import get_request_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    formatter: logging.Formatter = JsonFormatter() if settings.log_format == "json" else logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    if settings.log_to_stdout:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)
    if settings.log_to_file:
        log_dir = Path(settings.log_directory)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_dir / "alduor.log", maxBytes=settings.log_file_max_bytes, backupCount=settings.log_file_backup_count, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
