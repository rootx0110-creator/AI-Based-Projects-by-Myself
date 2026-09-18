"""Core logging configuration for LBSimulator."""

import logging
import sys
from datetime import datetime

_log_colors = {
    logging.DEBUG: "\x1b[38;5;33m",
    logging.INFO: "\x1b[38;5;39m",
    logging.WARNING: "\x1b[38;5;227m",
    logging.ERROR: "\x1b[38;5;196m",
}

class ColoredFormatter(logging.Formatter):
    """Colored log formatter for terminal output."""

    def format(self, record):
        color = _log_colors.get(record.levelno, "")
        reset = "\x1b[0m"
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        base = f"{color}[{ts} {record.levelname:<8}] {reset}"
        msg = super().format(record)
        return f"{base}{msg}"

def setup_logger(name: str = "lbsim", level: int = logging.INFO) -> logging.Logger:
    """Initialize and return a configured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColoredFormatter("%(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = setup_logger()
