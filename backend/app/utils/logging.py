"""Logging utilities.

Provides common logger setup used by routes, services, and scheduled tasks.
"""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return configured logger with a simple default formatter."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
    return logger
