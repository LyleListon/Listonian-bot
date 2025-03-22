"""
Price Validator Module

This module provides comprehensive price validation functionality:
- Multi-source price validation
- Manipulation detection
- Historical price analysis
- Liquidity shift monitoring
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, NamedTuple
from decimal import Decimal
from eth_typing import ChecksumAddress
from web3 import Web3

from ...utils.async_manager import AsyncLock
from ..interfaces import PriceData, TokenPair
from ..memory.memory_bank import MemoryBank

logger = logging.getLogger(__name__)

class PriceDeviation(NamedTuple):
    """Price deviation metrics."""
    mean_deviation: Decimal
    max_deviation: Decimal
    suspicious_pairs: List[Tuple[str, str]]  # Pairs of DEX names with suspicious deviations

class LiquidityShift(NamedTuple):
    """Liquidity shift detection metrics."""
    volume_change: Decimal
    time_window: int
    is_suspicious: bool

class PriceValidator:
    """Validates prices and detects manipulation attempts."""

    def __init__(
        self,
        web3: Web3,
        memory_bank: MemoryBank,
        max_price_deviation: Decimal = Decimal('0.02'),    # 2% maximum deviation
        min_liquidity_threshold: Decimal = Decimal('1000'),  # Minimum liquidity in base token
        suspicious_shift_threshold: Decimal = Decimal('0.1')  # 10% sudden liquidity shift
    ):
        """Initialize the price validator."""
        self.web3 = web3
        self.memory_bank = memory_bank
        
        # Configuration
        self.max_price_deviation = max_price_deviation
        self.min_liquidity_threshold = min_liquidity_threshold
        self.suspicious_shift_threshold = suspicious_shift_threshold
        
        # Thread safety
        self._validation_lock = AsyncLock()
        
        # Cache settings
        self._recent_prices: Dict[str, List[Tuple[Decimal, int]]] = {}  # token_pair -> [(price, timestamp)]
        self._liquidity_history: Dict[str, List[Tuple[Decimal, int]]] = {}  # pool_id -> [(liquidity, timestamp)]
        self._cache_ttl = 3600  # 1 hour for historical data

    async def validate_prices(
        self,
        token_pair: TokenPair,
        prices: Dict[str, PriceData]
    ) -> bool:
        """
        Validate prices from multiple sources.
        
        Args:
            token_pair: Token pair to validate
            prices: Dictionary of DEX names to price data
            
        Returns:
            True if prices are valid, False otherwise
        """
        async with self._validation_lock:
            try:
                # Check minimum sources
                if len(prices) < 2:
                    logger.warning(f"Insufficient price sources for {token_pair}")
                    return False
                
                # Calculate price deviation
                deviation = await self._calculate_deviation(prices)
                if deviation.max_deviation > self.max_price_deviation:
                    logger.warning(
                        f"Excessive price deviation detected for {token_pair}: "
                        f"{deviation.max_deviation:.2%}"
                    )
                    return False
                
                # Check for suspicious pairs
                if deviation.suspicious_pairs:
                    logger.warning(
                        f"Suspicious price pairs detected for {token_pair}: "
                        f"{deviation.suspicious_pairs}"
                    )
                    return False
                
                # Validate against historical prices
                if not await self._validate_historical_prices(token_pair, prices):
                    logger.warning(f"Historical price validation failed for {token_pair}")
                    return False
                
                # Check liquidity shifts
                for dex_name, price_data in prices.items():
                    shift = await self._detect_liquidity_shift(token_pair, dex_name)
                    if shift.is_suspicious:
                        logger.warning(
                            f"Suspicious liquidity shift detected for {token_pair} on {dex_name}: "
                            f"{shift.volume_change:.2%} change in {shift.time_window}s"
                        )
                        return False
                
                # Update price history
                await self._update_price_history(token_pair, prices)
                
                return True
                
            except Exception as e:
                logger.error(f"Price validation error for {token_pair}: {e}")
                return False

    async def _calculate_deviation(
        self,
        prices: Dict[str, PriceData]
    ) -> PriceDeviation:
        """Calculate price deviation metrics."""
        price_values = [p.price for p in prices.values()]
        mean_price = sum(price_values) / len(price_values)
        
        # Calculate deviations
        deviations = [abs(p - mean_price) / mean_price for p in price_values]
        mean_dev = sum(deviations) / len(deviations)
        max_dev = max(deviations)
        
        # Identify suspicious pairs
        suspicious = []
        dex_names = list(prices.keys())
        for i in range(len(dex_names)):
            for j in range(i + 1, len(dex_names)):
                price1 = prices[dex_names[i]].price
                price2 = prices[dex_names[j]].price
                if abs(price1 - price2) / mean_price > self.max_price_deviation:
                    suspicious.append((dex_names[i], dex_names[j]))
        
        return PriceDeviation(
            mean_deviation=Decimal(str(mean_dev)),
            max_deviation=Decimal(str(max_dev)),
            suspicious_pairs=suspicious
        )

    async def _validate_historical_prices(
        self,
        token_pair: TokenPair,
        current_prices: Dict[str, PriceData]
    ) -> bool:
        """Validate prices against historical data."""
        # Get historical prices
        history = self._recent_prices.get(str(token_pair), [])
        if not history:
            return True  # No history to validate against
        
        # Calculate historical metrics
        recent_prices = [p[0] for p in history[-10:]]  # Last 10 prices
        mean_historical = sum(recent_prices) / len(recent_prices)
        
        # Check current prices against historical mean
        current_mean = sum(p.price for p in current_prices.values()) / len(current_prices)
        deviation = abs(current_mean - mean_historical) / mean_historical
        
        return deviation <= self.max_price_deviation * Decimal('1.5')  # Allow 50% more deviation for historical

    async def _detect_liquidity_shift(
        self,
        token_pair: TokenPair,
        dex_name: str
    ) -> LiquidityShift:
        """Detect suspicious liquidity shifts."""
        # Get liquidity history
        pool_id = f"{dex_name}:{token_pair}"
        history = self._liquidity_history.get(pool_id, [])
        if len(history) < 2:
            return LiquidityShift(Decimal('0'), 0, False)
        
        # Calculate volume change
        recent_volume = history[-1][0]
        previous_volume = history[-2][0]
        time_diff = history[-1][1] - history[-2][1]
        
        volume_change = abs(recent_volume - previous_volume) / previous_volume
        
        return LiquidityShift(
            volume_change=volume_change,
            time_window=time_diff,
            is_suspicious=volume_change > self.suspicious_shift_threshold
        )

    async def _update_price_history(
        self,
        token_pair: TokenPair,
        prices: Dict[str, PriceData]
    ):
        """Update price history cache."""
        current_time = self.web3.eth.get_block('latest')['timestamp']
        mean_price = sum(p.price for p in prices.values()) / len(prices)
        
        pair_key = str(token_pair)
        if pair_key not in self._recent_prices:
            self._recent_prices[pair_key] = []
        
        self._recent_prices[pair_key].append((mean_price, current_time))
        
        # Cleanup old entries
        self._recent_prices[pair_key] = [
            (p, t) for p, t in self._recent_prices[pair_key]
            if current_time - t <= self._cache_ttl
        ]

    async def update_liquidity_history(
        self,
        token_pair: TokenPair,
        dex_name: str,
        liquidity: Decimal
    ):
        """Update liquidity history for a pool."""
        current_time = self.web3.eth.get_block('latest')['timestamp']
        pool_id = f"{dex_name}:{token_pair}"
        
        if pool_id not in self._liquidity_history:
            self._liquidity_history[pool_id] = []
        
        self._liquidity_history[pool_id].append((liquidity, current_time))
        
        # Cleanup old entries
        self._liquidity_history[pool_id] = [
            (l, t) for l, t in self._liquidity_history[pool_id]
            if current_time - t <= self._cache_ttl
        ]