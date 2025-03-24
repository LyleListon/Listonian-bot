"""Logging configuration for the dashboard."""

import asyncio
import logging
import os
import sys
import time
import functools
from typing import Optional, Any, Callable

def configure_logging(level: str = "DEBUG") -> None:
    """Set up logging configuration.
    
    Args:
        level: Logging level (default: INFO)
    """
    # Get log level from environment or parameter
    log_level = os.getenv("LOG_LEVEL", level).upper()
    
    # Basic configuration
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout
    )
    
    # Reduce verbosity of some loggers
    logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
    logging.getLogger("fastapi").setLevel(logging.DEBUG)
    logging.getLogger("dashboard").setLevel(logging.DEBUG)

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (optional)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

def log_execution_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to log function execution time.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logger = get_logger(func.__module__)
            logger.debug(f"{func.__name__} completed in {elapsed_time:.2f}s")
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger = get_logger(func.__module__)
            logger.error(f"{func.__name__} failed after {elapsed_time:.2f}s: {e}")
            raise

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logger = get_logger(func.__module__)
            logger.debug(f"{func.__name__} completed in {elapsed_time:.2f}s")
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger = get_logger(func.__module__)
            logger.error(f"{func.__name__} failed after {elapsed_time:.2f}s: {e}")
            raise

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

__all__ = [
    "configure_logging", "get_logger", "log_execution_time"
]