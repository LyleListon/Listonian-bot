"""
Price Validator Implementation

This module provides functionality for validating prices across multiple sources
and detecting price manipulation attempts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

class PriceValidator:
    """
    Validator for token prices.
    
    This class provides:
    - Price consistency checks
    - Manipulation detection
    - Price impact validation
    - Slippage protection
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the price validator.
        
        Args:
            config: Validator configuration
        """
        self._config = config
        
        # Configuration
        self._max_price_deviation = config.get("max_price_deviation", 0.01)  # 1%
        self._min_liquidity_usd = config.get("min_liquidity_usd", 10000)
        self._price_history_minutes = config.get("price_history_minutes", 60)
        self._suspicious_change_threshold = config.get("suspicious_change_threshold", 0.05)  # 5%
        
        # State
        self._lock = asyncio.Lock()
        self._initialized = False
        self._price_history = {}  # token -> list of (timestamp, price) tuples
        self._last_cleanup = datetime.now()
    
    async def initialize(self) -> None:
        """Initialize the price validator."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing price validator")
            self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            self._initialized = False
            self._price_history.clear()
    
    async def validate_prices(
        self,
        token_pair: Tuple[str, str],
        prices: Dict[str, float],
        liquidity: Dict[str, float]
    ) -> tuple[bool, Optional[str], float]:
        """
        Validate prices from multiple sources.
        
        Args:
            token_pair: Pair of token addresses
            prices: Prices from different sources
            liquidity: Liquidity from different sources
            
        Returns:
            Tuple of (is_valid, error_message, confidence)
        """
        if not self._initialized:
            raise RuntimeError("Price validator not initialized")
        
        async with self._lock:
            try:
                # Check price consistency
                if not prices:
                    return False, "No prices available", 0.0
                if not liquidity:
                    return False, "No liquidity data available", 0.0
                mean_price = sum(prices.values()) / len(prices)
                
                for source, price in prices.items():
                    deviation = abs(price - mean_price) / mean_price
                    if deviation > self._max_price_deviation:
                        return False, f"Price deviation too high on {source}: {deviation:.2%}", 0.0
                
                # Check liquidity
                total_liquidity = sum(liquidity.values())
                if total_liquidity < self._min_liquidity_usd:
                    return False, f"Insufficient liquidity: ${total_liquidity:,.2f}", 0.0
                
                # Check for manipulation
                is_suspicious, reason = await self._check_manipulation(
                    token_pair[0],
                    mean_price
                )
                if is_suspicious:
                    return False, f"Suspicious price activity: {reason}", 0.0
                
                # Calculate confidence score
                confidence = self._calculate_confidence(
                    prices=prices,
                    liquidity=liquidity,
                    mean_price=mean_price
                )
                
                # Update price history
                await self._update_price_history(
                    token=token_pair[0],
                    price=mean_price
                )
                
                return True, None, confidence
                
            except Exception as e:
                logger.error(f"Error validating prices: {e}", exc_info=True)
                raise
    
    async def validate_price_impact(
        self,
        token_pair: Tuple[str, str],
        amount_in_wei: int,
        expected_price: float,
        actual_price: float
    ) -> tuple[bool, Optional[str]]:
        """
        Validate price impact of a trade.
        
        Args:
            token_pair: Pair of token addresses
            amount_in_wei: Trade amount in wei
            expected_price: Expected execution price
            actual_price: Actual execution price
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self._initialized:
            raise RuntimeError("Price validator not initialized")
        
        price_impact = abs(actual_price - expected_price) / expected_price
        
        if price_impact > self._max_price_deviation:
            return False, f"Price impact too high: {price_impact:.2%}"
        
        return True, None
    
    async def _check_manipulation(
        self,
        token: str,
        current_price: float
    ) -> tuple[bool, Optional[str]]:
        """Check for price manipulation."""
        history = self._price_history.get(token, [])
        if not history:
            return False, None
        
        # Get recent price changes
        now = datetime.now()
        recent_changes = []
        
        for timestamp, price in reversed(history):
            if now - timestamp > timedelta(minutes=5):
                break
            
            change = abs(current_price - price) / price
            recent_changes.append(change)
        
        if recent_changes:
            # Check for sudden price changes
            max_change = max(recent_changes)
            if max_change > self._suspicious_change_threshold:
                return True, f"Sudden price change of {max_change:.2%}"
            
            # Check for price oscillation
            if len(recent_changes) >= 3:
                oscillations = sum(
                    1 for i in range(len(recent_changes)-2)
                    if (recent_changes[i] > recent_changes[i+1] and
                        recent_changes[i+1] < recent_changes[i+2])
                    or (recent_changes[i] < recent_changes[i+1] and
                        recent_changes[i+1] > recent_changes[i+2])
                )
                
                if oscillations >= 2:
                    return True, "Suspicious price oscillation"
        
        return False, None
    
    def _calculate_confidence(
        self,
        prices: Dict[str, float],
        liquidity: Dict[str, float],
        mean_price: float
    ) -> float:
        """Calculate confidence score for prices."""
        # Start with base confidence
        confidence = 1.0
        
        # Reduce confidence based on price deviations
        max_deviation = max(
            abs(price - mean_price) / mean_price
            for price in prices.values()
        )
        confidence *= (1.0 - max_deviation)
        
        # Reduce confidence for low liquidity
        total_liquidity = sum(liquidity.values())
        if total_liquidity < self._min_liquidity_usd * 2:
            liquidity_factor = total_liquidity / (self._min_liquidity_usd * 2)
            confidence *= liquidity_factor
        
        # Reduce confidence if few price sources
        if len(prices) < 3:
            confidence *= len(prices) / 3
        
        return confidence
    
    async def _update_price_history(
        self,
        token: str,
        price: float
    ) -> None:
        """Update price history for a token."""
        now = datetime.now()
        
        # Add new price
        if token not in self._price_history:
            self._price_history[token] = []
        self._price_history[token].append((now, price))
        
        # Clean up old prices periodically
        if (now - self._last_cleanup).total_seconds() > 300:  # Every 5 minutes
            await self._cleanup_price_history()
    
    async def _cleanup_price_history(self) -> None:
        """Clean up old price history."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=self._price_history_minutes)
        
        for token in list(self._price_history.keys()):
            history = self._price_history[token]
            
            # Remove old prices
            while history and history[0][0] < cutoff:
                history.pop(0)
            
            # Remove empty histories
            if not history:
                del self._price_history[token]
        
        self._last_cleanup = now