"""Logging configuration and utilities."""

import logging
import sys
import time
import functools
from pathlib import Path
from typing import Callable, Any

def setup_logging(level: str = "INFO") -> None:
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Set up logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(logs_dir / "dashboard.log"))
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)

def log_execution_time(logger: logging.Logger) -> Callable:
    """Decorator to log function execution time."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.perf_counter() - start_time
                logger.debug(
                    f"{func.__name__} executed in {execution_time:.4f} seconds"
                )
                return result
            except Exception as e:
                execution_time = time.perf_counter() - start_time
                logger.error(
                    f"{func.__name__} failed after {execution_time:.4f} seconds: {e}"
                )
                raise
        return wrapper
    return decorator