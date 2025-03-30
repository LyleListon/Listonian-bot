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
from ..web3.web3_manager import Web3Manager

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
        
        # Initialize enhanced analyzer and web3
        self._analyzer = EnhancedMarketAnalyzer(config)
        # Construct the config dict expected by Web3Manager
        web3_config = {
            "rpc_url": config.get("provider_url"), # Map provider_url to rpc_url
            "chain_id": config.get("chain_id"),
            # Include other relevant settings if needed, or let Web3Manager use defaults
            "retry_count": config.get("web3", {}).get("retry_count"),
            "retry_delay": config.get("web3", {}).get("retry_delay"),
            "timeout": config.get("web3", {}).get("timeout"),
        }
        # Filter out None values in case top-level keys were missing
        web3_config = {k: v for k, v in web3_config.items() if v is not None}
        self._web3 = Web3Manager(web3_config)
        
        # Cache for market data
        self._last_update = None
        self._market_condition = {}
        self._price_cache = {}  # token -> price
        self._liquidity_cache = {}  # pool -> liquidity
        self._retry_count = config.get("retry_count", 3)
        self._retry_delay = config.get("retry_delay", 1.0)
    
    async def initialize(self) -> None:
        """Initialize the market data provider."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing enhanced market data provider")
            
            # Initialize components
            await self._analyzer.initialize()
            await self._web3.initialize()
            
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
    
    async def _fetch_dex_price(
self,
        dex_name: str,
        factory: str,
        weth_address: str,
        usdc_address: str,
        amount: str
    ) -> Optional[float]:
        """
        Fetch price from a specific DEX with retries.
        
        Args:
            dex_name: Name of the DEX
            factory: Factory contract address
            weth_address: WETH token address
            usdc_address: USDC token address
            amount: Amount to quote in wei
            
        Returns:
            Price in USD or None if unavailable
        """
        for attempt in range(self._retry_count):
            try:
                # Verify DEX configuration
                # Get DEX version from config
                # Normalize dex_name to match config keys (e.g., "BaseSwap V3" -> "baseswap")
                config_key = dex_name.lower().replace(" ", "_").replace("_v3", "").replace("_v2", "")
                dex_config = self._config.get("dexes", {}).get(config_key)
                version = dex_config.get("version", "v3") if dex_config else "v3" # Default to v3 if not specified

                if not all([factory, weth_address, usdc_address]):
                    logger.debug(f"Skipping {dex_name}: missing required addresses")
                    return None
                
                price = await self._web3.get_quote(
                    factory=factory,
                    token_in=weth_address,
                    token_out=usdc_address,
                    amount=amount,
                    version=version,
                )
                return price / 1e6  # Convert to USD
            except Exception as e:
                if attempt == self._retry_count - 1:
                    logger.debug(f"Failed to fetch {dex_name} price after {self._retry_count} attempts: {e}")
                    return None
                await asyncio.sleep(self._retry_delay * (attempt + 1))  # Exponential backoff
    
    async def _fetch_initial_market_data(self) -> Dict[str, Any]:
        """
        Fetch initial market data.
        
        Returns:
            Initial market state
        """
        try:
            timestamp = datetime.now()
            
            # Get token addresses from config
            weth_address = self._config["tokens"]["WETH"]["address"]
            usdc_address = self._config["tokens"]["USDC"]["address"]
            
            # Fetch prices from DEXes
            prices = {}
            liquidity = {}
            
            dex_configs = {k: v for k, v in self._config["dexes"].items() if v is not None}
            
            # BaseSwap V3
            baseswap_config = dex_configs.get("baseswap") # Use correct key
            logger.debug(f"Initial fetch - BaseSwap config retrieved: {baseswap_config}")
            if baseswap_config and baseswap_config.get("enabled", False):
                baseswap_price = await self._fetch_dex_price(
                    "BaseSwap V3",
                    baseswap_config.get("factory"),
                    weth_address,
                    usdc_address,
                    "1000000000000000000"  # 1 WETH
              )
                if baseswap_price is not None:
                    prices["baseswap_v3"] = baseswap_price
                    # Assuming get_pool_liquidity also needs factory, weth, usdc
                    try:
                        liquidity["baseswap_v3"] = await self._web3.get_pool_liquidity(
                            baseswap_config.get("factory"),
                            weth_address,
                            usdc_address
                        )
                    except Exception as liq_error:
                         logger.warning(f"Failed to get BaseSwap V3 liquidity: {liq_error}")
                         liquidity["baseswap_v3"] = 0 # Default liquidity if fetch fails
                    self._price_cache["baseswap_v3"] = baseswap_price
            else:
                logger.info("BaseSwap V3 is disabled in config, skipping initial fetch.")
            
            # Aerodrome V3
            aerodrome_config = dex_configs.get("aerodrome") # Use correct key
            logger.debug(f"Initial fetch - Aerodrome config retrieved: {aerodrome_config}")
            if aerodrome_config and aerodrome_config.get("enabled", False):
                aerodrome_price = await self._fetch_dex_price(
                    "Aerodrome V3",
                    aerodrome_config.get("factory"),
                    weth_address,
                    usdc_address,
                    "1000000000000000000"  # 1 WETH
                 )
    
                if aerodrome_price is not None:
                        prices["aerodrome_v3"] = aerodrome_price
                        try:
                            liquidity["aerodrome_v3"] = await self._web3.get_pool_liquidity(
                                aerodrome_config.get("factory"),
                                weth_address,
                                usdc_address
                            )
                        except Exception as liq_error:
                             logger.warning(f"Failed to get Aerodrome V3 liquidity: {liq_error}")
                             liquidity["aerodrome_v3"] = 0 # Default liquidity if fetch fails
                        self._price_cache["aerodrome_v3"] = aerodrome_price
            else:
                 logger.info("Aerodrome V3 is disabled in config, skipping initial fetch.")
            
            # Get initial analysis
            market_data = {"token_pair": (weth_address, usdc_address), "liquidity": liquidity}
            analysis = await self._analyzer.analyze_market_data(market_data, list(prices.values()), list(prices.keys()))
            
            return {
                "timestamp": timestamp.isoformat(),
                "analysis": analysis,
                "prices": prices,
                "liquidity": liquidity
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
            
            # Get token addresses from config
            weth_address = self._config["tokens"]["WETH"]["address"]
            usdc_address = self._config["tokens"]["USDC"]["address"]
            
            # Fetch prices from DEXes
            prices = {}
            liquidity = {}
            
            dex_configs = {k: v for k, v in self._config["dexes"].items() if v is not None}
            
            # BaseSwap V3
            baseswap_config = dex_configs.get("baseswap") # Use correct key
            logger.debug(f"Update fetch - BaseSwap config retrieved: {baseswap_config}")
            if baseswap_config and baseswap_config.get("enabled", False):
                baseswap_price = await self._fetch_dex_price(
                    "BaseSwap V3",
                    baseswap_config.get("factory"),
                    weth_address,
                    usdc_address,
                    "1000000000000000000"  # 1 WETH
               )
                if baseswap_price is not None:
                    prices["baseswap_v3"] = baseswap_price
                    try:
                        liquidity["baseswap_v3"] = await self._web3.get_pool_liquidity(
                            baseswap_config.get("factory"),
                            weth_address,
                            usdc_address
                     )   
                    except Exception as liq_error:
                         logger.warning(f"Failed to get BaseSwap V3 liquidity: {liq_error}")
                         liquidity["baseswap_v3"] = 0 # Default liquidity if fetch fails
                    self._price_cache["baseswap_v3"] = baseswap_price
            else:
                logger.debug("BaseSwap V3 is disabled in config, skipping update fetch.")
            
            # Aerodrome V3
            aerodrome_config = dex_configs.get("aerodrome") # Use correct key
            logger.debug(f"Update fetch - Aerodrome config retrieved: {aerodrome_config}")
            if aerodrome_config and aerodrome_config.get("enabled", False):
                aerodrome_price = await self._fetch_dex_price(
                    "Aerodrome V3",
                    aerodrome_config.get("factory"),
                    weth_address,
                    usdc_address,
                    "1000000000000000000"  # 1 WETH
                 )
       
                if aerodrome_price is not None:
                        prices["aerodrome_v3"] = aerodrome_price
                        try:
                            liquidity["aerodrome_v3"] = await self._web3.get_pool_liquidity(
                                    aerodrome_config.get("factory"),
                                    weth_address,
                                    usdc_address
                             )
                        except Exception as liq_error:
                             logger.warning(f"Failed to get Aerodrome V3 liquidity: {liq_error}")
                             liquidity["aerodrome_v3"] = 0 # Default liquidity if fetch fails
                        self._price_cache["aerodrome_v3"] = aerodrome_price
            else:
                 logger.debug("Aerodrome V3 is disabled in config, skipping update fetch.")
            
            # Get updated analysis
            market_data = {"token_pair": (weth_address, usdc_address), "liquidity": liquidity}
            analysis = await self._analyzer.analyze_market_data(market_data, list(prices.values()), list(prices.keys()))
            
            return {
                "timestamp": timestamp.isoformat(),
                "analysis": analysis,
                "prices": prices,
                "liquidity": liquidity
            }
        except Exception as e:
            logger.error(f"Error fetching market data: {e}", exc_info=True)
            raise