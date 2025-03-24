import asyncio
import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..memory.memory_bank import MemoryBank
from .price_validator import PriceValidator

logger = logging.getLogger(__name__)

class EnhancedMarketAnalyzer:
    """Enhanced market analyzer with ML capabilities."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._initialized = False
        self._lock = asyncio.Lock()
        self._memory_bank = MemoryBank()
        self._config = config or {}
        
        # Default price validator config
        price_validator_config = {
            "max_price_deviation": 0.01,  # 1%
            "min_liquidity_usd": 10000,
            "price_history_minutes": 60,
            "suspicious_change_threshold": 0.05  # 5%
        }
        if config and "price_validator" in config:
            price_validator_config.update(config["price_validator"])
        self._price_validator = PriceValidator(price_validator_config)
    
    async def initialize(self) -> None:
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing enhanced market analyzer")
            
            try:
                # Initialize components
                await self._memory_bank.initialize()
                await self._price_validator.initialize()
                
                self._initialized = True
                logger.info("Enhanced market analyzer initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize enhanced market analyzer: {e}", exc_info=True)
                raise
    
    async def analyze_market_data(
        self,
        market_data: Dict[str, Any],
        prices: List[float],
        sources: List[str]
    ) -> Dict[str, Any]:
        if not self._initialized:
            raise RuntimeError("Enhanced market analyzer not initialized")
        
        try:
            # Validate prices
            token_pair = market_data.get("token_pair", ("", ""))
            price_dict = dict(zip(sources, prices))
            liquidity_dict = {src: market_data.get("liquidity", {}).get(src, 0) for src in sources}
            
            price_validation = await self._price_validator.validate_prices(
                token_pair=token_pair,
                prices=price_dict,
                liquidity=liquidity_dict
            )
            
            is_valid, error_msg, confidence = price_validation
            
            if not is_valid:
                logger.warning(
                    "Price validation failed",
                    extra={
                        "validation": price_validation,
                        "prices": prices,
                        "sources": sources}
                )
                return {
                    "is_valid": False,
                    "reason": "Price validation failed",
                    "validation": price_validation
                }
            
            # Update memory bank state
            await self._update_state(
                market_data=market_data,
                price_validation=price_validation
            )

            return {
                "is_valid": True,
                "analysis": market_data,
                "validation": price_validation
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market data: {e}", exc_info=True)
            raise
    
    async def cleanup(self) -> None:
        async with self._lock:
            if not self._initialized:
                return
            
            logger.info("Cleaning up enhanced market analyzer")
            
            try:
                await self._memory_bank.cleanup()
                await self._price_validator.cleanup()
                
                self._initialized = False
                logger.info("Enhanced market analyzer cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up enhanced market analyzer: {e}", exc_info=True)
                raise
                
    async def _update_state(
        self,
        market_data: Dict[str, Any],
        price_validation: Dict[str, Any]
    ) -> None:
        """Update memory bank state with market data."""
        try:
            state_dir = Path("memory-bank/state")
            state_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract pool data
            pools = market_data.get("pools", {})
            pool_metrics = {
                pool_id: {
                    "liquidity": pool.get("liquidity"),
                    "token0_price": pool.get("token0_price"),
                    "token1_price": pool.get("token1_price"),
                    "volume_24h": pool.get("volume_24h"),
                    "fees_24h": pool.get("fees_24h"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                for pool_id, pool in pools.items()
            }
            
            # Write pool metrics
            pool_file = state_dir / "pool_metrics.json"
            with open(pool_file, "w") as f:
                json.dump(pool_metrics, f, indent=2)
            
            # Write market state
            market_state = {
                "gas_price": market_data.get("gas_price", 0),
                "network_status": market_data.get("network_status", "unknown"),
                "price_validation": price_validation,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            market_file = state_dir / "market_state.json"
            with open(market_file, "w") as f:
                json.dump(market_state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error updating market state: {e}", exc_info=True)
