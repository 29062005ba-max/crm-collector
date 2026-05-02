"""Structured logging configuration (JSON output)"""
import logging
import json
import sys
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """JSON-formatted logs for production observability"""
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        # Add extra fields (passed via extra={...})
        for k in ("company_id", "user_id", "correlation_id", "request_id",
                 "task_id", "task_name", "queue", "duration_ms"):
            if hasattr(record, k):
                log_data[k] = getattr(record, k)
        return json.dumps(log_data, default=str)


def setup_logging(level: str = "INFO", structured: bool = True):
    """Configure logging for the entire application"""
    handler = logging.StreamHandler(sys.stdout)
    if structured:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
