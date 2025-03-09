"""
Execution Strategies

This package contains strategy implementations for executing arbitrage opportunities,
including standard strategies, flash loan strategies, and custom execution flows.
"""

from .standard_strategy import StandardExecutionStrategy

__all__ = [
    "StandardExecutionStrategy"
]