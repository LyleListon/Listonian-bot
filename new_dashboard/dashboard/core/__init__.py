"""Core functionality for the dashboard."""

from .logging import get_logger, log_execution_time, setup_logging
from .dependencies import get_memory_service, get_metrics_service, get_system_service

__all__ = [
    'get_logger',
    'log_execution_time',
    'setup_logging',
    'get_memory_service',
    'get_metrics_service',
    'get_system_service'
]