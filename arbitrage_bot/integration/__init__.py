"""Integration package for arbitrage bot components.

This package provides integration utilities for various components of the arbitrage bot:
1. Gas Optimization Framework
2. Enhanced Multi-Hop Path Support
3. Path Finding Production Test Framework
4. Flashbots RPC Integration
"""

from .flashbots_integration import (
    setup_flashbots_rpc,
    test_flashbots_connection,
    create_and_simulate_bundle,
    optimize_and_submit_bundle
)

__all__ = [
    # Flashbots RPC Integration
    'setup_flashbots_rpc',
    'test_flashbots_connection',
    'create_and_simulate_bundle',
    'optimize_and_submit_bundle',
]