"""Logging configuration for the trading bot.

Every API request, response, and error is written to a rotating log file
(logs/trading_bot.log) as well as mirrored to the console, so that a full
audit trail of bot activity is always available.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root 'trading_bot' logger.

    Safe to call multiple times (e.g. from tests) — handlers are only
    attached once.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    root_logger = logging.getLogger("trading_bot")
    root_logger.setLevel(level)

    if root_logger.handlers:
        return root_logger

    formatter = logging.Formatter(_FORMAT)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.propagate = False

    return root_logger
