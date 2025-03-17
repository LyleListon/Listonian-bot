"""
Alchemy SDK integration for arbitrage bot.

This package provides a comprehensive interface to Alchemy's SDK
with focus on arbitrage operations, MEV protection, and real-time
monitoring.
"""

from .alchemy_config import (
    AlchemySettings,
    NetworkConfig,
    WebSocketConfig,
)

from .alchemy_provider import (
    AlchemyProvider,
)

from .alchemy_websocket import (
    AlchemyWebSocket,
    Subscription,
)

from .alchemy_gas import (
    AlchemyGasManager,
    GasEstimate,
    GasStrategy,
)

from .alchemy_mempool import (
    AlchemyMempool,
    MempoolTransaction,
    MEVRisk,
)

from .alchemy_service import (
    AlchemyService,
    NetworkStats,
    ArbitrageStats,
)

__all__ = [
    # Configuration
    'AlchemySettings',
    'NetworkConfig',
    'WebSocketConfig',
    
    # Provider
    'AlchemyProvider',
    
    # WebSocket
    'AlchemyWebSocket',
    'Subscription',
    
    # Gas Management
    'AlchemyGasManager',
    'GasEstimate',
    'GasStrategy',
    
    # Mempool Monitoring
    'AlchemyMempool',
    'MempoolTransaction',
    'MEVRisk',
    
    # Main Service
    'AlchemyService',
    'NetworkStats',
    'ArbitrageStats',
]

# Default configuration for Base mainnet
DEFAULT_SETTINGS = AlchemySettings(
    api_key="kRXhWVt8YU_8LnGS20145F5uBDFbL_k0",
    network=NetworkConfig(
        name="base-mainnet",
        chain_id=8453
    )
)

# Example usage:
"""
from src.core import AlchemyService, DEFAULT_SETTINGS

async def main():
    async with AlchemyService(DEFAULT_SETTINGS) as alchemy:
        # Get network stats
        stats = await alchemy.get_network_stats()
        print(f"Network Stats: {stats}")
        
        # Register for MEV alerts
        await alchemy.register_callback(
            "mev_risk",
            lambda data: print(f"MEV Alert: {data}")
        )
        
        # Wait for events
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
"""