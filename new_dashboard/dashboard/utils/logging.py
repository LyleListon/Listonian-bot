"""Logging configuration for the dashboard."""

import logging
from typing import Optional


def configure_logging() -> None:
    """Configure logging for the dashboard."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name or "dashboard")
