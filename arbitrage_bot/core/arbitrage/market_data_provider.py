"""
Market Data Provider

This module contains the implementation of the MarketDataProvider,
which provides market conditions and token prices for the arbitrage system.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Set, AsyncIterator
from decimal import Decimal

from web3 import Web3

from .interfaces import MarketDataProvider
from .models import MarketCondition

logger = logging.getLogger(__name__)


class BaseMarketDataProvider(MarketDataProvider):
    """
    Base implementation of the MarketDataProvider.
    
    This class provides market data such as token prices, gas prices,
    and overall market conditions for the arbitrage system.
    """
    
    def __init__(
        self,
        web3_manager: Any,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the market data provider.
        
        Args:
            web3_manager: Web3Manager instance for blockchain interactions
            config: Configuration dictionary
        """
        self.web3_manager = web3_manager
        self.config = config or {}
        
        # Configuration
        self.update_interval = self.config.get("market_update_interval_seconds", 10)
        self.gas_price_weight = self.config.get("gas_price_weight", 0.4)
        self.liquidity_weight = self.config.get("liquidity_weight", 0.3)
        self.volatility_weight = self.config.get("volatility_weight", 0.3)
        
        # Token price cache
        self._token_prices: Dict[str, float] = {}
        self._token_price_timestamp: Dict[str, float] = {}
        self._token_price_ttl = self.config.get("token_price_ttl_seconds", 60)
        
        # Market condition cache
        self._current_market_condition: Optional[MarketCondition] = None
        self._market_condition_timestamp = 0
        self._market_condition_ttl = self.config.get("market_condition_ttl_seconds", 30)
        
        # Token liquidity cache
        self._token_liquidity: Dict[str, float] = {}
        
        # Historical data for volatility calculation
        self._token_price_history: Dict[str, List[Tuple[float, float]]] = {}
        self._max_price_history_length = self.config.get("max_price_history_length", 100)
        
        # Shutdown event
        self._shutdown_event = asyncio.Event()
        
        # Active subscribers
        self._subscribers: Set[asyncio.Queue[MarketCondition]] = set()
        
        logger.info("BaseMarketDataProvider initialized")
    
    async def get_market_condition(self) -> MarketCondition:
        """
        Get current market conditions.
        
        Returns:
            Current market conditions
        """
        # Check if cached market condition is still valid
        current_time = time.time()
        if (self._current_market_condition and 
            current_time - self._market_condition_timestamp < self._market_condition_ttl):
            return self._current_market_condition
        
        # Update market condition
        try:
            gas_price_wei = await self._get_gas_price()
            gas_price_gwei = gas_price_wei / 1e9
            
            eth_price_usd = await self.get_token_price("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", "USD")
            
            # Calculate network congestion (0-1 scale)
            # Higher gas price means more congestion
            base_gas_price = self.config.get("base_gas_price_gwei", 20)
            max_gas_price = self.config.get("max_gas_price_gwei", 500)
            network_congestion = min(1.0, max(0.0, (gas_price_gwei - base_gas_price) / (max_gas_price - base_gas_price)))
            
            # Calculate volatility index (0-1 scale)
            volatility_index = await self._calculate_volatility_index()
            
            # Get liquidity levels for key tokens
            liquidity_levels = await self._get_token_liquidity_levels()
            
            # Create market condition
            market_condition = MarketCondition(
                timestamp=current_time,
                gas_price_gwei=gas_price_gwei,
                eth_price_usd=eth_price_usd,
                network_congestion=network_congestion,
                volatility_index=volatility_index,
                liquidity_levels=liquidity_levels
            )
            
            # Cache the result
            self._current_market_condition = market_condition
            self._market_condition_timestamp = current_time
            
            # Notify subscribers
            await self._notify_subscribers(market_condition)
            
            return market_condition
            
        except Exception as e:
            logger.error(f"Error getting market condition: {e}")
            
            # Return last known condition or create a default one
            if self._current_market_condition:
                return self._current_market_condition
            
            return MarketCondition(
                timestamp=current_time,
                gas_price_gwei=50.0,  # Default conservative value
                eth_price_usd=None,
                network_congestion=0.5,  # Medium congestion
                volatility_index=0.5,    # Medium volatility
                liquidity_levels={}
            )
    
    async def get_token_price(
        self,
        token_address: str,
        quote_currency: str = "USD"
    ) -> Optional[float]:
        """
        Get the price of a token.
        
        Args:
            token_address: Address of the token
            quote_currency: Currency to quote the price in
            
        Returns:
            Token price or None if not available
        """
        token_address = token_address.lower()
        cache_key = f"{token_address}_{quote_currency}"
        
        # Check if cached price is still valid
        current_time = time.time()
        if (cache_key in self._token_prices and 
            current_time - self._token_price_timestamp.get(cache_key, 0) < self._token_price_ttl):
            return self._token_prices[cache_key]
        
        try:
            # For real implementation, you would call a price oracle or API here
            # For this example, we'll simulate price fetching
            price = await self._fetch_token_price(token_address, quote_currency)
            
            if price is not None:
                # Cache the result
                self._token_prices[cache_key] = price
                self._token_price_timestamp[cache_key] = current_time
                
                # Record in price history for volatility calculation
                if token_address not in self._token_price_history:
                    self._token_price_history[token_address] = []
                
                self._token_price_history[token_address].append((current_time, price))
                
                # Trim history if needed
                if len(self._token_price_history[token_address]) > self._max_price_history_length:
                    self._token_price_history[token_address] = self._token_price_history[token_address][-self._max_price_history_length:]
            
            return price
            
        except Exception as e:
            logger.error(f"Error getting token price for {token_address}: {e}")
            return None
    
    async def subscribe_to_market_updates(
        self,
        token_addresses: Optional[List[str]] = None
    ) -> AsyncIterator[MarketCondition]:
        """
        Subscribe to market condition updates.
        
        Args:
            token_addresses: List of token addresses to monitor,
                             or None for all supported tokens
            
        Returns:
            Async iterator of market condition updates
        """
        # Create a queue for this subscriber
        queue = asyncio.Queue()
        self._subscribers.add(queue)
        
        try:
            # Send initial market condition
            market_condition = await self.get_market_condition()
            await queue.put(market_condition)
            
            # Keep yielding market conditions until closed
            while not self._shutdown_event.is_set():
                try:
                    condition = await queue.get()
                    yield condition
                    queue.task_done()
                except asyncio.CancelledError:
                    break
                
        finally:
            # Remove subscriber when done
            if queue in self._subscribers:
                self._subscribers.remove(queue)
    
    async def start_updates(self) -> None:
        """Start periodic market updates."""
        if not self._shutdown_event.is_set():
            # Start update task
            asyncio.create_task(self._update_loop())
            logger.info("Market data updates started")
    
    async def stop_updates(self) -> None:
        """Stop periodic market updates."""
        self._shutdown_event.set()
        logger.info("Market data updates stopped")
    
    async def _update_loop(self) -> None:
        """Background task for periodic market updates."""
        try:
            logger.info("Starting market update loop")
            while not self._shutdown_event.is_set():
                try:
                    # Update market condition
                    await self.get_market_condition()
                    
                    # Wait for next update
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.update_interval
                        )
                    except asyncio.TimeoutError:
                        continue
                    
                except Exception as e:
                    logger.error(f"Error in market update: {e}")
                    await asyncio.sleep(5)
            
        except asyncio.CancelledError:
            logger.info("Market update loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in market update loop: {e}")
    
    async def _notify_subscribers(self, market_condition: MarketCondition) -> None:
        """Notify all subscribers of a new market condition."""
        for queue in self._subscribers:
            try:
                # Use put_nowait to avoid blocking
                queue.put_nowait(market_condition)
            except asyncio.QueueFull:
                # Skip if queue is full
                pass
    
    async def _get_gas_price(self) -> int:
        """Get current gas price in wei."""
        try:
            # Use web3_manager to get gas price
            if hasattr(self.web3_manager, "get_gas_price"):
                return await self.web3_manager.get_gas_price()
            
            # Fallback to direct web3 call
            return self.web3_manager.w3.eth.gas_price
            
        except Exception as e:
            logger.error(f"Error getting gas price: {e}")
            # Return default value
            return int(50e9)  # 50 Gwei
    
    async def _calculate_volatility_index(self) -> float:
        """Calculate market volatility index (0-1 scale)."""
        try:
            # Get key tokens for volatility calculation
            key_tokens = self.config.get("volatility_tokens", [
                "0x4200000000000000000000000000000000000006",  # WETH
                "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC
                "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"   # USDT
            ])
            
            volatility_scores = []
            
            for token in key_tokens:
                token = token.lower()
                if token in self._token_price_history and len(self._token_price_history[token]) > 1:
                    history = self._token_price_history[token]
                    
                    # Calculate price changes
                    price_changes = []
                    for i in range(1, len(history)):
                        prev_price = history[i-1][1]
                        curr_price = history[i][1]
                        if prev_price > 0:
                            change_pct = abs(curr_price - prev_price) / prev_price
                            price_changes.append(change_pct)
                    
                    if price_changes:
                        # Calculate average change
                        avg_change = sum(price_changes) / len(price_changes)
                        
                        # Normalize to 0-1 scale
                        # 0.1 (10%) change is considered high volatility
                        volatility_score = min(1.0, avg_change / 0.1)
                        volatility_scores.append(volatility_score)
            
            # Return average volatility or default if no data
            if volatility_scores:
                return sum(volatility_scores) / len(volatility_scores)
            
            return 0.5  # Default medium volatility
            
        except Exception as e:
            logger.error(f"Error calculating volatility index: {e}")
            return 0.5  # Default medium volatility
    
    async def _get_token_liquidity_levels(self) -> Dict[str, float]:
        """Get liquidity levels for key tokens (0-1 scale)."""
        try:
            # Get key tokens for liquidity calculation
            key_tokens = self.config.get("liquidity_tokens", [
                "0x4200000000000000000000000000000000000006",  # WETH
                "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC
                "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"   # USDT
            ])
            
            liquidity_levels = {}
            
            for token in key_tokens:
                token = token.lower()
                
                # For real implementation, you would fetch actual liquidity data
                # For this example, we'll use cached values or defaults
                if token in self._token_liquidity:
                    liquidity_levels[token] = self._token_liquidity[token]
                else:
                    # Default to medium liquidity
                    liquidity_levels[token] = 0.7
            
            return liquidity_levels
            
        except Exception as e:
            logger.error(f"Error getting token liquidity levels: {e}")
            return {}
    
    async def _fetch_token_price(
        self,
        token_address: str,
        quote_currency: str
    ) -> Optional[float]:
        """
        Fetch token price from external sources.
        
        Args:
            token_address: Address of the token
            quote_currency: Currency to quote the price in
            
        Returns:
            Token price or None if not available
        """
        # In a real implementation, this would call price oracles or APIs
        # For this example, we'll use default values for common tokens
        
        token_address = token_address.lower()
        
        # Check if price feed integration is available
        if hasattr(self.web3_manager, "get_token_price"):
            price = await self.web3_manager.get_token_price(token_address, quote_currency)
            if price is not None:
                return price
        
        # Fallback to default values for common tokens
        if quote_currency.upper() == "USD":
            if token_address == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" or token_address == "0x4200000000000000000000000000000000000006":  # ETH/WETH
                return 3000.0  # Default ETH price in USD
            elif token_address == "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913":  # USDC
                return 1.0
            elif token_address == "0x50c5725949a6f0c72e6c4a641f24049a917db0cb":  # USDT
                return 1.0
        
        # For other tokens or quote currencies, return None
        return None


async def create_market_data_provider(
    web3_manager: Any,
    config: Dict[str, Any] = None
) -> BaseMarketDataProvider:
    """
    Create and initialize a market data provider.
    
    Args:
        web3_manager: Web3Manager instance for blockchain interactions
        config: Configuration dictionary
        
    Returns:
        Initialized market data provider
    """
    provider = BaseMarketDataProvider(
        web3_manager=web3_manager,
        config=config
    )
    
    # Start updates
    await provider.start_updates()
    
    return provider