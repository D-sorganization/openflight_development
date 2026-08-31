"""Logging configuration and utilities for OpenFlight.

Provides structured logging across all server, monitor, and background tasks.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
CONSOLE_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    level: str | int = "INFO",
    log_file: str | Path | None = None,
    fmt: str | None = None,
) -> logging.Logger:
    """Configure root / OpenFlight logging with consistent formatting.

    Parameters
    ----------
    level : str | int
        Logging level (e.g. "DEBUG", "INFO", "WARNING", "ERROR", logging.INFO).
    log_file : str | Path | None
        Optional file path to write log output to.
    fmt : str | None
        Optional custom log format string.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    if isinstance(level, str):
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {level}")
    else:
        numeric_level = level

    log_format = fmt or DEFAULT_LOG_FORMAT
    formatter = logging.Formatter(log_format, datefmt=DATE_FORMAT)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if reconfigured
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return logging.getLogger("openflight")


def get_logger(name: str = "openflight") -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)
