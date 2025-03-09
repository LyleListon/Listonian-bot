"""Memory bank manager for the arbitrage bot."""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from . import MemoryBank
from ..models.opportunity import Opportunity

logger = logging.getLogger(__name__)

class MemoryBankManager:
    """Manages memory bank operations and provides a centralized interface."""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(MemoryBankManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize memory bank manager."""
        if self._initialized:
            return
            
        self.memory_bank = MemoryBank()
        self._data_lock = asyncio.Lock()
        self._initialized = True
        logger.info("Memory bank manager initialized")

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize the memory bank with configuration."""
        try:
            if not self._initialized:
                logger.warning("Memory bank manager not initialized")
                return False
            
            async with self._lock:
                return await self.memory_bank.initialize(config)
        except Exception as e:
            logger.error("Failed to initialize memory bank: %s", str(e))
            return False
    
    async def store_market_data(self, key: str, data: Any, ttl: Optional[int] = None, version_comment: Optional[str] = None) -> None:
        """Store market data with optional TTL."""
        try:
            # Handle market analyzer data
            if key.startswith("condition_"):
                data = {
                    "price": str(data.get("price", 0)),
                    "trend": {
                        "direction": data.get("trend", {}).get("direction", "sideways"),
                        "strength": float(data.get("trend", {}).get("strength", 0.0)),
                        "duration": float(data.get("trend", {}).get("duration", 0.0)),
                        "volatility": float(data.get("trend", {}).get("volatility", 0.0)),
                        "confidence": float(data.get("trend", {}).get("confidence", 0.0))
                    },
                    "volume_24h": str(data.get("volume_24h", 0)),
                    "liquidity": str(data.get("liquidity", 0)),
                    "volatility_24h": float(data.get("volatility_24h", 0)),
                    "price_impact": float(data.get("price_impact", 0)),
                    "last_updated": float(data.get("last_updated", 0))
                }
            
            async with self._data_lock:
                await self.memory_bank.store(key, data, category="market_data", ttl=ttl)
        except Exception as e:
            logger.error("Failed to store market data %s: %s", key, str(e))
    
    async def get_market_data(self, key: str) -> Optional[Any]:
        """Retrieve market data."""
        try:
            async with self._data_lock:
                return await self.memory_bank.retrieve(key, category="market_data")
        except Exception as e:
            logger.error("Failed to retrieve market data %s: %s", key, str(e))
            return None
    
    async def store_transaction(self, key: str, data: Any) -> None:
        """Store transaction data."""
        try:
            async with self._data_lock:
                await self.memory_bank.store(key, data, category="transactions")
        except Exception as e:
            logger.error("Failed to store transaction %s: %s", key, str(e))
    
    async def get_transaction(self, key: str) -> Optional[Any]:
        """Retrieve transaction data."""
        try:
            async with self._data_lock:
                return await self.memory_bank.retrieve(key, category="transactions")
        except Exception as e:
            logger.error("Failed to retrieve transaction %s: %s", key, str(e))
            return None
    
    async def store_analytics(self, key: str, data: Any, ttl: Optional[int] = None, version_comment: Optional[str] = None) -> None:
        """Store analytics data."""
        try:
            # Handle gas optimizer data
            if key == "gas_optimizer":
                data = {
                    "optimal_gas_price": str(data.get("optimal_gas_price", 0)),
                    "current_base_fee": str(data.get("current_base_fee", 0)),
                    "priority_fee": str(data.get("priority_fee", 0)),
                    "max_fee_per_gas": str(data.get("max_fee_per_gas", 0)),
                    "max_priority_fee_per_gas": str(data.get("max_priority_fee_per_gas", 0)),
                    "gas_used_estimate": int(data.get("gas_used_estimate", 0)),
                    "confidence_level": float(data.get("confidence_level", 0.0)),
                    "last_updated": float(data.get("last_updated", datetime.now().timestamp()))
                }
            
            # Handle system metrics
            elif key == "system_metrics":
                data = {
                    "total_trades": int(data.get("total_trades", 0)),
                    "trades_24h": int(data.get("trades_24h", 0)),
                    "success_rate": float(data.get("success_rate", 0.0)),
                    "total_profit_usd": float(data.get("total_profit_usd", 0.0)),
                    "portfolio_change_24h": float(data.get("portfolio_change_24h", 0.0)),
                    "active_opportunities": int(data.get("active_opportunities", 0)),
                    "wallet_balance": str(data.get("wallet_balance", "0")),
                    "wallet_address": data.get("wallet_address"),
                    "gas_metrics": {
                        "average_gas_used": int(data.get("gas_metrics", {}).get("average_gas_used", 0)),
                        "total_gas_spent": str(data.get("gas_metrics", {}).get("total_gas_spent", "0")),
                        "gas_savings": str(data.get("gas_metrics", {}).get("gas_savings", "0"))
                    },
                    "last_updated": float(datetime.now().timestamp())
                }
            
            async with self._data_lock:
                await self.memory_bank.store(key, data, category="analytics", ttl=ttl)
        except Exception as e:
            logger.error("Failed to store analytics %s: %s", key, str(e))
    
    async def get_analytics(self, key: str) -> Optional[Any]:
        """Retrieve analytics data."""
        try:
            async with self._data_lock:
                return await self.memory_bank.retrieve(key, category="analytics")
        except Exception as e:
            logger.error("Failed to retrieve analytics %s: %s", key, str(e))
            return None
    
    async def store_docs(self, key: str, data: Any) -> None:
        """Store documentation data."""
        try:
            async with self._data_lock:
                await self.memory_bank.store(key, data, category="docs")
        except Exception as e:
            logger.error("Failed to store docs %s: %s", key, str(e))
    
    async def get_docs(self, key: str) -> Optional[Any]:
        """Retrieve documentation data."""
        try:
            async with self._data_lock:
                return await self.memory_bank.retrieve(key, category="docs")
        except Exception as e:
            logger.error("Failed to retrieve docs %s: %s", key, str(e))
            return None
    
    async def store_temp(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Store temporary data with optional TTL."""
        try:
            async with self._data_lock:
                await self.memory_bank.store(key, data, category="temp", ttl=ttl)
        except Exception as e:
            logger.error("Failed to store temp data %s: %s", key, str(e))
    
    async def get_temp(self, key: str) -> Optional[Any]:
        """Retrieve temporary data."""
        try:
            async with self._data_lock:
                return await self.memory_bank.retrieve(key, category="temp")
        except Exception as e:
            logger.error("Failed to retrieve temp data %s: %s", key, str(e))
            return None
    
    async def clear_category(self, category: str) -> None:
        """Clear all data in a category."""
        try:
            async with self._data_lock:
                stats = await self.memory_bank.get_memory_stats()
                if category in stats.categories:
                    for key in stats.categories[category]:
                        await self.memory_bank.clear(key, category)
        except Exception as e:
            logger.error("Failed to clear category %s: %s", category, str(e))
    
    async def clear_all(self) -> None:
        """Clear all stored data."""
        try:
            async with self._data_lock:
                await self.memory_bank.clear_all()
        except Exception as e:
            logger.error("Failed to clear all data: %s", str(e))
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        try:
            async with self._data_lock:
                stats = await self.memory_bank.get_memory_stats()
                compression_stats = await self.memory_bank.get_compression_stats()
                return {
                    "memory_stats": stats._asdict(),
                    "compression_stats": {k: v._asdict() for k, v in compression_stats.items()}
                }
        except Exception as e:
            logger.error("Failed to get memory stats: %s", str(e))
            return {}
    
    async def store_opportunities(self, opportunities: List[Opportunity]) -> None:
        """Store arbitrage opportunities."""
        try:
            async with self._data_lock:
                await self.memory_bank.store_opportunities(opportunities)
        except Exception as e:
            logger.error("Failed to store opportunities: %s", str(e))

    async def get_trade_history(self, max_age: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get trade execution history with optional age filter."""
        try:
            if not self._initialized:
                logger.warning("Memory bank manager not initialized")
                return []
            
            async with self._data_lock:
                # Get all trade results
                results = await self.memory_bank.get_trade_results()
                
                # Filter by age if specified
                if max_age is not None:
                    current_time = datetime.now().timestamp()
                    results = [
                        trade for trade in results
                        if current_time - trade.get('timestamp', 0) <= max_age
                    ]
                
                return results
                
        except Exception as e:
            logger.error("Failed to get trade history: %s", str(e))
            return []

    async def get_recent_opportunities(self, max_age: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent arbitrage opportunities with optional age filter."""
        try:
            if not self._initialized:
                logger.warning("Memory bank manager not initialized")
                return []
            
            async with self._data_lock:
                # Get all opportunities
                opportunities = await self.memory_bank.get_opportunities()
                
                # Filter by age if specified
                if max_age is not None:
                    current_time = datetime.now().timestamp()
                    opportunities = [
                        opp for opp in opportunities
                        if current_time - opp.get('timestamp', 0) <= max_age
                    ]
                
                return opportunities
                
        except Exception as e:
            logger.error("Failed to get recent opportunities: %s", str(e))
            return []

    async def store_trade_result(
        self,
        opportunity: Dict[str, Any],
        success: bool,
        net_profit: Optional[float] = None,
        gas_cost: Optional[float] = None,
        tx_hash: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Store trade execution result."""
        try:
            async with self._data_lock:
                await self.memory_bank.store_trade_result(
                    opportunity=opportunity,
                    success=success,
                    net_profit=net_profit,
                    gas_cost=gas_cost,
                    tx_hash=tx_hash,
                    error=error
                )
        except Exception as e:
            logger.error("Failed to store trade result: %s", str(e))
    
    async def stop(self) -> None:
        """Stop memory bank operations."""
        try:
            async with self._data_lock:
                await self.memory_bank.stop()
        except Exception as e:
            logger.error("Failed to stop memory bank: %s", str(e))

    async def cleanup(self) -> None:
        """Cleanup memory bank resources."""
        try:
            async with self._data_lock:
                await self.memory_bank.cleanup()
        except Exception as e:
            logger.error("Failed to cleanup memory bank: %s", str(e))

async def get_memory_bank(config: Optional[Dict[str, Any]] = None) -> MemoryBankManager:
    """Get the singleton memory bank manager instance."""
    manager = MemoryBankManager()
    if not manager.memory_bank.initialized:
        success = await manager.initialize(config or {})
        if not success:
            logger.error("Failed to initialize memory bank")
            raise RuntimeError("Memory bank initialization failed")
        logger.debug("Memory bank initialized with config")
    return manager
