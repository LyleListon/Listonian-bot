"""Dashboard application for arbitrage bot monitoring."""

from .services import service_manager
from .core import configure_logging, get_logger

__all__ = [
    'create_app',
    'service_manager',
    'configure_logging',
    'get_logger'
]

def create_app():
    """Create and configure the FastAPI application."""
    from .app import create_app as _create_app
    return _create_app()