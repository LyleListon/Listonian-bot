"""Core functionality for the dashboard."""

from .logging import setup_logging, get_logger
from .mock_memory import create_memory_bank, MockMemoryBank

__all__ = [
    'setup_logging',
    'get_logger',
    'create_memory_bank',
    'MockMemoryBank'
]