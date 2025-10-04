"""
Logging configuration for the application.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import structlog
from pythonjsonlogger import jsonlogger

from app.core.config import settings


def setup_logging():
    """
    Configure application logging with structured logging support.
    """
    # Create logs directory if it doesn't exist
    if settings.LOG_FILE_PATH:
        try:
            settings.LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # Skip if we can't create the directory (e.g., in Docker mount or read-only filesystem)
            pass

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    if settings.LOG_FORMAT == "json":
        # JSON formatter for structured logging
        json_formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"asctime": "timestamp"},
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        formatter = json_formatter
    else:
        # Standard text formatter
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    if settings.LOG_FILE_PATH:
        try:
            if "day" in settings.LOG_ROTATION:
                # Time-based rotation
                file_handler = TimedRotatingFileHandler(
                    settings.LOG_FILE_PATH,
                    when="D",
                    interval=1,
                    backupCount=30,
                    encoding="utf-8"
                )
            else:
                # Size-based rotation
                file_handler = RotatingFileHandler(
                    settings.LOG_FILE_PATH,
                    maxBytes=100 * 1024 * 1024,  # 100MB
                    backupCount=10,
                    encoding="utf-8"
                )

            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError, FileNotFoundError) as e:
            # Can't create file handler (e.g., read-only filesystem), log to console only
            console_handler.stream.write(f"Warning: Could not create log file handler: {e}\n")

    # Configure structlog for structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.dict_tracebacks,
            structlog.dev.ConsoleRenderer() if settings.is_development else structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING if not settings.DATABASE_ECHO else logging.INFO)
    logging.getLogger("celery").setLevel(logging.INFO)

    # Log initial configuration
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={settings.LOG_LEVEL}, "
        f"format={settings.LOG_FORMAT}, "
        f"file={settings.LOG_FILE_PATH}"
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)