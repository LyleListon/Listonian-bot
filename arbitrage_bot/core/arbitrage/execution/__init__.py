"""
Arbitrage Execution Package

This package contains components responsible for executing arbitrage opportunities,
including execution managers and strategies.
"""

from .default_manager import DefaultExecutionManager

__all__ = [
    "DefaultExecutionManager"
]