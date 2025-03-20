"""
Core functionality for the arbitrage bot.

This package provides:
1. Web3 interaction layer
 (contract interactions, transactions, gas estimation)
2. Storage management
3. Cache management
4. System monitoring
5. Resource management
6. WebSocket management
7. Metrics collection
"""

from typing import Dict, Any
from .storage import StorageManager
from .cache import get_cache, Cache
from .websocket import get_ws_manager, WebSocketManager
from .metrics import get_metrics_collector, MetricsCollector
from .web3 import (
    Web3Manager,
    Web3Error,
    get_web3_manager
)

__all__ = [
    'StorageManager',
    'get_cache',
    'Cache',
    'get_ws_manager',
    'WebSocketManager',
    'get_metrics_collector',
    'MetricsCollector',
    'Web3Manager',
    'Web3Error',
    'get_web3_manager'
]
