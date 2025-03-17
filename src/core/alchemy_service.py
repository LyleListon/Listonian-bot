"""
Main Alchemy service coordinating all Alchemy SDK components.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from decimal import Decimal
from asyncio import Lock

from .alchemy_config import AlchemySettings
from .alchemy_provider import AlchemyProvider
from .alchemy_websocket import AlchemyWebSocket
from .alchemy_gas import AlchemyGasManager, GasEstimate
from .alchemy_mempool import AlchemyMempool, MEVRisk, MempoolTransaction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class NetworkStats:
    """Network statistics."""
    block_number: int
    gas_price: int
    base_fee: int
    network_load: float  # 0.0 to 1.0
    pending_tx_count: int

@dataclass
class ArbitrageStats:
    """Arbitrage statistics."""
    opportunities_found: int
    successful_trades: int
    failed_trades: int
    total_profit: Decimal
    average_profit: Decimal
    gas_spent: Decimal

class AlchemyService:
    """
    Main service coordinating all Alchemy SDK components.
    
    Features:
    - Centralized Alchemy SDK management
    - Real-time network monitoring
    - Gas price optimization
    - MEV protection
    - Arbitrage opportunity detection
    """
    
    def __init__(self, settings: AlchemySettings):
        """Initialize the Alchemy service."""
        self.settings = settings
        self._lock = Lock()
        self._initialized = False
        
        # Components
        self._provider: Optional[AlchemyProvider] = None
        self._ws: Optional[AlchemyWebSocket] = None
        self._gas_manager: Optional[AlchemyGasManager] = None
        self._mempool: Optional[AlchemyMempool] = None
        
        # Stats
        self._network_stats = NetworkStats(
            block_number=0,
            gas_price=0,
            base_fee=0,
            network_load=0.0,
            pending_tx_count=0
        )
        
        self._arbitrage_stats = ArbitrageStats(
            opportunities_found=0,
            successful_trades=0,
            failed_trades=0,
            total_profit=Decimal("0"),
            average_profit=Decimal("0"),
            gas_spent=Decimal("0")
        )
        
        # Callbacks
        self._callbacks: Dict[str, List[Callable]] = {}
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
        
    async def initialize(self):
        """Initialize all Alchemy components."""
        async with self._lock:
            if self._initialized:
                return
                
            try:
                # Initialize provider
                self._provider = AlchemyProvider(self.settings)
                await self._provider.initialize()
                
                # Initialize WebSocket
                self._ws = AlchemyWebSocket(self.settings)
                await self._ws.connect()
                
                # Initialize gas manager
                self._gas_manager = AlchemyGasManager(self.settings)
                await self._gas_manager.initialize()
                
                # Initialize mempool monitor
                self._mempool = AlchemyMempool(self.settings)
                await self._mempool.initialize()
                
                # Set up event handlers
                await self._setup_event_handlers()
                
                self._initialized = True
                logger.info("Alchemy service initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize Alchemy service: {e}")
                await self.cleanup()
                raise
                
    async def _setup_event_handlers(self):
        """Set up event handlers for all components."""
        if not self._mempool:
            return
            
        # Register MEV risk handler
        await self._mempool.register_callback(
            "mev_risk",
            self._handle_mev_risk
        )
        
        # Register arbitrage opportunity handler
        await self._mempool.register_callback(
            "arbitrage",
            self._handle_arbitrage_opportunity
        )
        
    async def _handle_mev_risk(self, tx_hash: str, risk: MEVRisk):
        """Handle MEV risk detection."""
        logger.warning(f"MEV Risk detected for {tx_hash}: {risk.level} ({risk.type})")
        await self._notify_subscribers("mev_risk", {
            "tx_hash": tx_hash,
            "risk": risk
        })
        
    async def _handle_arbitrage_opportunity(self, tx: MempoolTransaction):
        """Handle arbitrage opportunity detection."""
        self._arbitrage_stats.opportunities_found += 1
        await self._notify_subscribers("arbitrage", {
            "transaction": tx
        })
        
    async def get_network_stats(self) -> NetworkStats:
        """Get current network statistics."""
        if not self._initialized:
            raise RuntimeError("Service not initialized")
            
        try:
            # Update network stats
            if self._provider:
                block_number = await self._provider.get_block_number()
                self._network_stats.block_number = block_number
                
            if self._gas_manager:
                gas_estimate = await self._gas_manager.estimate_gas_price()
                self._network_stats.gas_price = gas_estimate.max_fee
                self._network_stats.base_fee = gas_estimate.base_fee
                
            if self._mempool:
                self._network_stats.pending_tx_count = len(self._mempool._pending_txs)
                
            # Calculate network load (simple heuristic)
            self._network_stats.network_load = min(
                1.0,
                self._network_stats.pending_tx_count / 10000
            )
            
            return self._network_stats
            
        except Exception as e:
            logger.error(f"Error getting network stats: {e}")
            raise
            
    async def get_arbitrage_stats(self) -> ArbitrageStats:
        """Get current arbitrage statistics."""
        if not self._initialized:
            raise RuntimeError("Service not initialized")
            
        # Calculate average profit
        if self._arbitrage_stats.successful_trades > 0:
            self._arbitrage_stats.average_profit = (
                self._arbitrage_stats.total_profit /
                self._arbitrage_stats.successful_trades
            )
            
        return self._arbitrage_stats
        
    async def optimize_transaction(
        self,
        tx_params: Dict[str, Any],
        max_wait: float = 30.0
    ) -> Dict[str, Any]:
        """
        Optimize transaction parameters for arbitrage.
        
        Args:
            tx_params: Transaction parameters
            max_wait: Maximum acceptable wait time in seconds
            
        Returns:
            Optimized transaction parameters
        """
        if not self._initialized or not self._gas_manager:
            raise RuntimeError("Service not initialized")
            
        try:
            # Get gas estimate
            gas_estimate = await self._gas_manager.estimate_gas_price()
            
            # Optimize gas prices
            max_fee, priority_fee = await self._gas_manager.optimize_gas_price(
                base_cost=tx_params.get('gas', 21000),
                max_wait=max_wait
            )
            
            # Update transaction parameters
            tx_params.update({
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': priority_fee
            })
            
            return tx_params
            
        except Exception as e:
            logger.error(f"Error optimizing transaction: {e}")
            raise
            
    async def register_callback(self, event_type: str, callback: Callable):
        """Register callback for specific events."""
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)
        
    async def _notify_subscribers(self, event_type: str, data: Any):
        """Notify subscribers of events."""
        if event_type in self._callbacks:
            for callback in self._callbacks[event_type]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Error in callback for {event_type}: {e}")
                    
    async def cleanup(self):
        """Cleanup all components."""
        async with self._lock:
            if not self._initialized:
                return
                
            # Cleanup components
            if self._mempool:
                await self._mempool.cleanup()
                
            if self._gas_manager:
                await self._gas_manager.cleanup()
                
            if self._ws:
                await self._ws.disconnect()
                
            if self._provider:
                await self._provider.cleanup()
                
            # Clear state
            self._initialized = False
            self._callbacks.clear()
            
            logger.info("Alchemy service cleaned up")

# Example usage:
async def main():
    settings = AlchemySettings(
        api_key="kRXhWVt8YU_8LnGS20145F5uBDFbL_k0"
    )
    
    async def handle_mev_alert(data):
        print(f"MEV Alert: {data}")
    
    async with AlchemyService(settings) as alchemy:
        # Register for MEV alerts
        await alchemy.register_callback("mev_risk", handle_mev_alert)
        
        # Get network stats
        stats = await alchemy.get_network_stats()
        print(f"Network Stats: {stats}")
        
        # Wait for events
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())