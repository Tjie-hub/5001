"""Structured JSON logging with correlation IDs and rotating file output (R13).

Usage in app.py:
    from utils.logging_config import setup_logging
    setup_logging()

Features:
  - JSONFormatter: each log record → {"time", "level", "logger", "msg",
    "correlation_id", **extra}
  - RotatingFileHandler: logs/app.log, 10 MB per file, 5 backups kept
  - CorrelationFilter: injects flask.g.correlation_id when inside a request
  - Console handler retained for development
"""

import json
import logging
import logging.handlers
import os
import traceback
import uuid
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        # Correlation ID injected by CorrelationFilter (or absent outside requests)
        cid = getattr(record, 'correlation_id', None)

        payload: dict = {
            'time':           datetime.now(tz=timezone.utc).isoformat(timespec='milliseconds'),
            'level':          record.levelname,
            'logger':         record.name,
            'msg':            record.getMessage(),
        }
        if cid:
            payload['correlation_id'] = cid
        if record.exc_info:
            payload['exc'] = ''.join(traceback.format_exception(*record.exc_info)).strip()

        # Merge any extra fields passed via `extra=` kwarg
        standard = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
            'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
            'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
            'thread', 'threadName', 'processName', 'process', 'correlation_id',
            'taskName',
        }
        for k, v in record.__dict__.items():
            if k not in standard and not k.startswith('_'):
                try:
                    json.dumps(v)  # only include JSON-serialisable extras
                    payload[k] = v
                except (TypeError, ValueError):
                    payload[k] = str(v)

        return json.dumps(payload, ensure_ascii=False)


class CorrelationFilter(logging.Filter):
    """Inject correlation_id from Flask request context into every log record.

    Falls back gracefully when called outside a request (e.g. scheduler jobs)
    by using the thread-local ID set via set_correlation_id().
    """

    _thread_local_id: str | None = None

    def filter(self, record: logging.LogRecord) -> bool:
        cid = CorrelationFilter._thread_local_id
        # Try Flask request context first
        try:
            from flask import g
            cid = g.get('correlation_id', cid)
        except RuntimeError:
            pass  # outside application context
        record.correlation_id = cid
        return True


_SECRET_VARS = ("TELEGRAM_TOKEN", "ZAI_API_KEY", "DEEPSEEK_API_KEY",
                "TAVILY_API_KEY", "FLASK_SECRET_KEY", "STOCKBIT_PASSWORD",
                "AUTH_TOKEN_ADMIN", "AUTH_TOKEN_OPERATOR", "AUTH_TOKEN_VIEWER",
                "AUTH_TOKEN_SCHEDULER", "TELEGRAM_WEBHOOK_SECRET")


class SecretRedactionFilter(logging.Filter):
    """Mask configured secret values if they ever reach a log line
    (security hardening Phase 3). Values are read from env at filter time so
    rotation needs no restart of the logging stack."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        dirty = False
        for var in _SECRET_VARS:
            for val in (v.strip() for v in os.getenv(var, "").split(",")):
                if len(val) >= 8 and val in msg:
                    msg = msg.replace(val, "[REDACTED]")
                    dirty = True
        if dirty:
            record.msg = msg
            record.args = ()
        return True


def set_correlation_id(cid: str | None = None) -> str:
    """Set a correlation ID for the current thread (used by scheduler jobs)."""
    cid = cid or str(uuid.uuid4())
    CorrelationFilter._thread_local_id = cid
    return cid


def setup_logging(log_dir: str = 'logs', level: int = logging.INFO) -> None:
    """Configure root logger with JSON formatter + rotating file + console."""
    os.makedirs(log_dir, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicate output on reload
    root.handlers.clear()

    correlation_filter = CorrelationFilter()
    redaction_filter = SecretRedactionFilter()
    json_fmt = JSONFormatter()

    # Rotating file handler: logs/app.log, 10 MB × 5 backups
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8',
    )
    file_handler.setFormatter(json_fmt)
    file_handler.addFilter(correlation_filter)
    file_handler.addFilter(redaction_filter)
    root.addHandler(file_handler)

    # Console handler (human-readable for dev; structlog-style prefix)
    console_fmt = logging.Formatter(
        '%(asctime)s  %(levelname)-8s  %(name)s  %(message)s',
        datefmt='%H:%M:%S',
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_fmt)
    console_handler.addFilter(correlation_filter)
    console_handler.addFilter(redaction_filter)
    root.addHandler(console_handler)

    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.info('Structured JSON logging initialised (level=%s)', logging.getLevelName(level))
