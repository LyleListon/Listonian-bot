"""Logging configuration for the arbitrage bot."""

import logging
# import logging.handlers # Unused
# import os # Unused
from datetime import datetime
from pathlib import Path


def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Get current date for log file name
    current_date = datetime.now().strftime("%Y%m%d")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)d)",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)8s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Create and configure analytics file handler
    analytics_handler = logging.FileHandler(
        logs_dir / f"analytics_{current_date}.log", encoding="utf-8"
    )
    analytics_handler.setLevel(logging.INFO)
    analytics_handler.setFormatter(file_formatter)
    analytics_logger = logging.getLogger("arbitrage_bot.core.analytics")
    analytics_logger.addHandler(analytics_handler)

    # Create and configure WebSocket file handler
    websocket_handler = logging.FileHandler(
        logs_dir / f"websocket_{current_date}.log", encoding="utf-8"
    )
    websocket_handler.setLevel(logging.INFO)
    websocket_handler.setFormatter(file_formatter)
    websocket_logger = logging.getLogger("arbitrage_bot.dashboard.websocket")
    websocket_logger.addHandler(websocket_handler)

    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Create and configure error file handler
    error_handler = logging.FileHandler(
        logs_dir / f"error_{current_date}.log", encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)

    # Configure individual loggers
    loggers = [
        "arbitrage_bot.core.analytics",
        "arbitrage_bot.dashboard.websocket",
        "arbitrage_bot.core.web3",
        "arbitrage_bot.core.execution",
        "arbitrage_bot.core.monitoring",
        "arbitrage_bot.core.metrics",
        "arbitrage_bot.core.alerts",
        "arbitrage_bot.core.ml",
        "arbitrage_bot.core.backtesting",
        "arbitrage_bot.core.reporting",
        "arbitrage_bot.dashboard",
    ]

    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.propagate = True  # Allow propagation to root logger

    logging.info("Logging system initialized")
