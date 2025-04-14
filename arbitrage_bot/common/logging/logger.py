"""Logging configuration for the arbitrage bot."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


def setup_logger(
    config: Dict[str, Any],
    name: Optional[str] = None
) -> logging.Logger:
    """Set up a logger with the specified configuration.
    
    Args:
        config: The configuration dictionary.
        name: The name of the logger. If None, the root logger will be used.
        
    Returns:
        The configured logger.
    """
    # Get logging configuration
    log_config = config.get("logging", {})
    log_level = getattr(logging, log_config.get("level", "INFO"))
    log_file = log_config.get("file", "logs/bot.log")
    max_file_size = log_config.get("max_file_size", 10 * 1024 * 1024)  # 10 MB
    backup_count = log_config.get("backup_count", 5)
    console_output = log_config.get("console_output", True)
    log_format = log_config.get(
        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Create file handler
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = Path(log_file).parent
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Create console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger
