"""
Dashboard package for arbitrage bot monitoring.

This package provides:
1. FastAPI application
2. WebSocket server
3. Metrics collection
4. Real-time monitoring
"""

from .app import app
from .run import DashboardRunner, main

__all__ = [
    'app',
    'DashboardRunner',
    'main'
]
