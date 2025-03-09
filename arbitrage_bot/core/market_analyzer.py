"""
Market Analyzer Module

Analyzes market conditions and identifies arbitrage opportunities.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

from .dex.dex_manager import DexManager

logger = logging.getLogger(__name__)

@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity."""
    token_id: str
    token_address: str
    buy_dex: str
    sell_dex: str
    buy_price: Decimal
    sell_price: Decimal
    profit_margin: Decimal
    timestamp: datetime
    tx_hash: Optional[str] = None
    gas_cost: Optional[Decimal] = None

class MarketAnalyzer:
    """Analyzes market conditions for arbitrage opportunities."""
    
    def __init__(
        self,
        dex_manager: DexManager,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the market analyzer.
        
        Args:
            dex_manager: DEX manager instance
            config: Optional configuration
        """
        self.dex_manager = dex_manager
        self.config = config or {}
        self.initialized = False
        self.lock = asyncio.Lock()
        
        # Configuration
        self.min_profit_threshold = Decimal(str(self.config.get('min_profit_threshold', 0.001)))
        self.max_price_impact = Decimal(str(self.config.get('max_price_impact', 0.01)))
        self.min_liquidity = Decimal(str(self.config.get('min_liquidity', 1000)))
        
        # Cache for price data
        self._price_cache = {}
        self._liquidity_cache = {}
        
        # Cache TTL in seconds
        self.cache_ttl = int(self.config.get('price_cache_ttl', 5))
        
    async def initialize(self) -> bool:
        """
        Initialize the market analyzer.
        
        Returns:
            True if initialization successful
        """
        try:
            # Initialize price monitoring
            await self._update_prices()
            
            # Start background price updates
            asyncio.create_task(self._price_monitor())
            
            self.initialized = True
            logger.info("Market analyzer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize market analyzer: {e}")
            return False
            
    async def _price_monitor(self):
        """Monitor prices in the background."""
        while True:
            try:
                await self._update_prices()
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Error updating prices: {e}")
                await asyncio.sleep(30)  # Longer delay on error
                
    async def _update_prices(self):
        """Update current prices."""
        try:
            # Get all DEXs
            dexes = await self.dex_manager.get_all_dexes()
            
            # Update prices for each DEX
            for dex in dexes:
                # Get supported tokens
                dex_info = await self.dex_manager.get_dex_info(dex)
                if not dex_info:
                    continue
                    
                for token in dex_info.supported_tokens:
                    # Get pool address
                    pool_address = await self.dex_manager.get_pool_address(dex, token, None)
                    if not pool_address:
                        continue
                        
                    # Get liquidity
                    liquidity = await self.dex_manager.get_pool_liquidity(dex, pool_address)
                    if not liquidity or liquidity < self.min_liquidity:
                        continue
                        
                    # Update cache
                    cache_key = f"{dex}:{token}"
                    self._liquidity_cache[cache_key] = (
                        asyncio.get_event_loop().time(),
                        liquidity
                    )
                    
        except Exception as e:
            logger.error(f"Failed to update prices: {e}")
            
    async def get_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Get current arbitrage opportunities.
        
        Returns:
            List of arbitrage opportunities
        """
        if not self.initialized:
            raise RuntimeError("Market analyzer not initialized")
            
        opportunities = []
        
        try:
            # Get all DEXs
            dexes = await self.dex_manager.get_all_dexes()
            
            # Compare prices across DEXs
            common_tokens = await self._get_common_tokens(dexes)
            async for token in common_tokens:
                for buy_dex in dexes:
                    for sell_dex in dexes:
                        if buy_dex == sell_dex:
                            continue
                            
                        # Get prices
                        buy_price = await self._get_price(buy_dex, token)
                        sell_price = await self._get_price(sell_dex, token)
                        
                        if not buy_price or not sell_price:
                            continue
                            
                        # Calculate profit margin
                        profit_margin = (sell_price - buy_price) / buy_price
                        
                        # Check if profitable
                        if profit_margin > self.min_profit_threshold:
                            opportunities.append(ArbitrageOpportunity(
                                token_id=token,
                                token_address=token,
                                buy_dex=buy_dex,
                                sell_dex=sell_dex,
                                buy_price=buy_price,
                                sell_price=sell_price,
                                profit_margin=profit_margin,
                                timestamp=datetime.utcnow()
                            ))
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error getting opportunities: {e}")
            return []
            
    async def _get_common_tokens(self, dexes: List[str]) -> List[str]:
        """Get tokens supported by multiple DEXs."""
        common_tokens = set()
        first = True
        
        for dex in dexes:
            dex_info = await self.dex_manager.get_dex_info(dex)
            if not dex_info:
                continue
                
            if first:
                common_tokens = dex_info.supported_tokens
                first = False
            else:
                common_tokens &= dex_info.supported_tokens
                
        return list(common_tokens)
        
    async def _get_price(self, dex: str, token: str) -> Optional[Decimal]:
        """Get price from cache or update."""
        cache_key = f"{dex}:{token}"
        
        if cache_key in self._price_cache:
            timestamp, price = self._price_cache[cache_key]
            if asyncio.get_event_loop().time() - timestamp < self.cache_ttl:
                return price
                
        # Price not in cache or expired
        try:
            # Get pool address
            pool_address = await self.dex_manager.get_pool_address(dex, token, None)
            if not pool_address:
                return None
                
            # Get liquidity
            liquidity = await self.dex_manager.get_pool_liquidity(dex, pool_address)
            if not liquidity or liquidity < self.min_liquidity:
                return None
                
            # TODO: Implement actual price fetching
            # For now, return None to indicate price not available
            return None
            
        except Exception as e:
            logger.error(f"Failed to get price for {token} on {dex}: {e}")
            return None

async def create_market_analyzer(
    dex_manager: DexManager,
    config: Optional[Dict[str, Any]] = None
) -> MarketAnalyzer:
    """
    Create and initialize a market analyzer.
    
    Args:
        dex_manager: DEX manager instance
        config: Optional configuration
        
    Returns:
        Initialized MarketAnalyzer instance
    """
    analyzer = MarketAnalyzer(dex_manager, config)
    if not await analyzer.initialize():
        raise RuntimeError("Failed to initialize market analyzer")
    return analyzer
