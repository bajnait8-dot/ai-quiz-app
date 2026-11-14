"""Structured, low-noise logging for the quiz app."""

from __future__ import annotations

import logging
import sys

from core.config import settings

_CONFIGURED = False


class RequestIdFilter(logging.Filter):
    """Injects the current request id into log records when available."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] [rid=%(request_id)s] %(message)s"
        )
    )
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    # Keep framework access logs but route them through the same formatter.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.propagate = False
        logger.setLevel(settings.log_level)

    _CONFIGURED = True
