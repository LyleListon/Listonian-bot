"""
Enhanced Market Data Provider Implementation

This module provides a concrete implementation of the MarketDataProvider protocol
with enhanced market data capabilities.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path

from .interfaces import MarketDataProvider as MarketDataProviderABC
from ..market.enhanced_market_analyzer import EnhancedMarketAnalyzer

logger = logging.getLogger(__name__)

class EnhancedMarketDataProvider(MarketDataProviderABC):
    """
    Enhanced implementation of the MarketDataProvider protocol.
    
    This class provides real-time market data with enhanced analytics
    and price validation capabilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the market data provider."""
        self._config = config
        self._market_data_config = config["market_data"]
        self._update_interval = self._market_data_config["update_interval_seconds"]
        self._price_cache_ttl = self._market_data_config["price_cache_ttl"]
        self._liquidity_cache_ttl = self._market_data_config["liquidity_cache_ttl"]
        
        self._callbacks = []  # List of update callbacks
        self._tasks = set()  # Active tasks
        self._lock = asyncio.Lock()
        self._initialized = False
        
        # Initialize enhanced analyzer
        self._analyzer = EnhancedMarketAnalyzer()
        
        # Cache for market data
        self._last_update = None
        self._market_condition = {}
        self._price_cache = {}  # token -> price
        self._liquidity_cache = {}  # pool -> liquidity
    
    async def initialize(self) -> None:
        """Initialize the market data provider."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing enhanced market data provider")
            
            # Initialize analyzer
            await self._analyzer.initialize()
            
            # Initialize caches
            self._last_update = datetime.now()
            self._market_condition = await self._fetch_initial_market_data()
            
            self._initialized = True
            logger.info("Enhanced market data provider initialized")
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            # Stop monitoring first
            await self.stop_monitoring()
            
            # Clean up analyzer
            await self._analyzer.cleanup()
            
            # Cancel and wait for all tasks
            if self._tasks:
                for task in self._tasks:
                    if not task.done():
                        task.cancel()
                
                # Wait for all tasks to complete
                if self._tasks:
                    await asyncio.gather(*self._tasks, return_exceptions=True)
                self._tasks.clear()
            
            # Clear caches
            self._price_cache.clear()
            self._liquidity_cache.clear()
            self._market_condition.clear()
            
            self._initialized = False
            logger.info("Enhanced market data provider cleaned up")
    
    async def get_current_market_condition(self) -> Dict[str, Any]:
        """
        Get the current market condition.
        
        Returns:
            Current market state and prices
        """
        if not self._initialized:
            raise RuntimeError("Market data provider not initialized")
        
        async with self._lock:
            return self._market_condition.copy()
    
    async def register_market_update_callback(
        self,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register a callback for market updates.
        
        Args:
            callback: Function to call when market updates occur
        """
        if not self._initialized:
            raise RuntimeError("Market data provider not initialized")
        
        self._callbacks.append(callback)
        logger.debug(f"Registered market update callback {callback.__name__}")
    
    async def start_monitoring(
        self,
        update_interval_seconds: Optional[float] = None
    ) -> None:
        """
        Start monitoring market conditions.
        
        Args:
            update_interval_seconds: Time between updates in seconds
        """
        if not self._initialized:
            await self.initialize()
        
        if update_interval_seconds is not None:
            self._update_interval = update_interval_seconds
        
        # Start update task if not running
        if not any(not task.done() for task in self._tasks):
            update_task = asyncio.create_task(self._update_loop())
            self._tasks.add(update_task)
            update_task.add_done_callback(self._tasks.discard)
            
            logger.info(
                f"Started market monitoring with {self._update_interval}s interval"
            )
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring market conditions."""
        # Cancel all running tasks
        if self._tasks:
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
            
            logger.info("Stopped market monitoring")
    
    async def _update_loop(self):
        """Background task for updating market data."""
        logger.info("Starting market data update loop")
        
        while True:
            try:
                # Fetch new market data
                new_condition = await self._fetch_market_data()
                
                async with self._lock:
                    # Update caches
                    self._market_condition = new_condition
                    self._last_update = datetime.now()
                    
                    # Update price cache
                    for token, price in new_condition.get("prices", {}).items():
                        self._price_cache[token] = price
                    
                    # Update liquidity cache
                    for pool, liquidity in new_condition.get("liquidity", {}).items():
                        self._liquidity_cache[pool] = liquidity
                
                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        await callback(new_condition)
                    except Exception as e:
                        logger.error(
                            f"Error in market update callback {callback.__name__}: {e}",
                            exc_info=True
                        )
                
                # Sleep until next update
                await asyncio.sleep(self._update_interval)
                
            except asyncio.CancelledError:
                logger.info("Market data update loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in market data update loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _fetch_initial_market_data(self) -> Dict[str, Any]:
        """
        Fetch initial market data.
        
        Returns:
            Initial market state
        """
        try:
            timestamp = datetime.now()
            
            # Initialize with test data
            test_market_data = {
                "token_pair": ("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", # WETH
                             "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"), # USDC
                "liquidity": {
                    "uniswap_v3": 1000000,
                    "sushiswap": 800000,
                    "baseswap": 500000
                }
            }
            
            test_prices = {
                "uniswap_v3": 3500.50,
                "sushiswap": 3500.45,
                "baseswap": 3500.55
            }
            
            # Get initial analysis
            analysis = await self._analyzer.analyze_market_data(
                market_data=test_market_data,
                prices=list(test_prices.values()),
                sources=list(test_prices.keys())
            )
            return {
                "timestamp": timestamp.isoformat(),
                "analysis": analysis,
                "prices": test_prices,
                "liquidity": test_market_data["liquidity"]
            }
        except Exception as e:
            logger.error(f"Error fetching initial market data: {e}", exc_info=True)
            raise
    
    async def _fetch_market_data(self) -> Dict[str, Any]:
        """
        Fetch current market data.
        
        Returns:
            Current market state
        """
        try:
            timestamp = datetime.now()
            # Get updated analysis
            analysis = await self._analyzer.analyze_market_data(
                market_data=self._market_condition,
                prices=list(self._price_cache.values()),
                sources=list(self._price_cache.keys())
            )
            return {
                "timestamp": timestamp.isoformat(),
                "analysis": analysis,
                "prices": self._price_cache.copy(),
                "liquidity": self._liquidity_cache.copy()
            }
        except Exception as e:
            logger.error(f"Error fetching market data: {e}", exc_info=True)
            raise