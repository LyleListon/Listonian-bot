"""Factory package."""

from .system_factory import (
    create_arbitrage_system,
    create_arbitrage_system_from_config
)

__all__ = [
    'create_arbitrage_system',
    'create_arbitrage_system_from_config'
]