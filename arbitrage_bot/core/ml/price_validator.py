"""
Price Validator Implementation

This module provides functionality for validating prices across multiple sources
and detecting price manipulation attempts.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class PriceValidator:
    """Validates prices from multiple sources."""
    
    def __init__(self):
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing price validator")
            
            try:
                self._initialized = True
                logger.info("Price validator initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize price validator: {e}", exc_info=True)
                raise
    
    async def validate_prices(
        self,
        prices: List[float],
        sources: List[str],
        confidence_threshold: float = 0.95
    ) -> Dict[str, Any]:
        """
        Validate prices from multiple sources.
        
        Args:
            prices: List of prices to validate
            sources: List of price sources
            confidence_threshold: Minimum confidence required
            
        Returns:
            Dictionary containing validation results
        """
        if not self._initialized:
            raise RuntimeError("Price validator not initialized")
        
        try:
            # Handle empty or invalid inputs
            if not prices or not sources or len(prices) != len(sources):
                return {
                    "is_valid": False,
                    "confidence": 0.0,
                    "outliers": [],
                    "reason": "Invalid or empty price data"
                }
            
            # Basic validation logic
            mean_price = sum(prices) / len(prices)
            if mean_price <= 0:
                return {
                    "is_valid": False,
                    "confidence": 0.0,
                    "outliers": [],
                    "reason": "Invalid mean price"
                }
            
            # Calculate deviations
            deviations = [abs(p - mean_price) / mean_price for p in prices]
            
            # Identify outliers (prices that deviate more than 5%)
            outliers = [i for i, d in enumerate(deviations) if d > 0.05]
            
            # Calculate confidence score
            confidence = 1.0 - (len(outliers) / len(prices)) if prices else 0.0
            
            # Build validation results
            results = {
                "is_valid": confidence >= confidence_threshold,
                "confidence": confidence,
                "outliers": [
                    {
                        "index": i,
                        "source": sources[i],
                        "price": prices[i],
                        "deviation": deviations[i]
                    }
                    for i in outliers
                ],
                "mean_price": mean_price,
                "sample_size": len(prices)
            }
            
            # Log validation results
            if not results["is_valid"]:
                logger.warning(
                    "Price validation failed",
                    extra={
                        "confidence": confidence,
                        "outlier_count": len(outliers),
                        "sample_size": len(prices)
                    }
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating prices: {e}", exc_info=True)
            raise
    
    async def cleanup(self) -> None:
        async with self._lock:
            if not self._initialized:
                return
            
            logger.info("Cleaning up price validator")
            
            try:
                self._initialized = False
                logger.info("Price validator cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up price validator: {e}", exc_info=True)
                raise
