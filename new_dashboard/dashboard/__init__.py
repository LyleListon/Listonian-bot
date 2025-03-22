"""Dashboard application for arbitrage bot monitoring."""

from .app import app
from .services import service_manager
from .core import setup_logging, get_logger

__all__ = [
    'app',
    'service_manager',
    'setup_logging',
    'get_logger'
]