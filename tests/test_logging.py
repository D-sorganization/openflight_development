"""Tests for openflight.log module and logging configuration."""

from __future__ import annotations

import logging

from openflight.log import configure_logging, get_logger


def test_get_logger_returns_named_logger():
    logger = get_logger("openflight.test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "openflight.test_module"


def test_configure_logging_sets_level():
    configure_logging(level="DEBUG")
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG

    configure_logging(level=logging.WARNING)
    assert root_logger.level == logging.WARNING

    configure_logging(level="INFO")
    assert root_logger.level == logging.INFO


def test_configure_logging_custom_format():
    custom_fmt = "%(levelname)s: %(message)s"
    configure_logging(level="INFO", fmt=custom_fmt)
    # Logging configuration should complete without raising errors
    logger = get_logger("openflight.test_custom")
    logger.info("Testing custom format")
