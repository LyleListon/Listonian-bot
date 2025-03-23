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
        if not self._initialized:
            raise RuntimeError("Price validator not initialized")
        
        try:
            # Basic validation logic
            mean_price = sum(prices) / len(prices)
            deviations = [abs(p - mean_price) / mean_price for p in prices]
            outliers = [i for i, d in enumerate(deviations) if d > 0.05]
            
            results = {
                "is_valid": len(outliers) < len(prices) // 3,
                "confidence": 1.0 - (len(outliers) / len(prices)),
                "outliers": [{"index": i, "source": sources[i]} for i in outliers]
            }
            
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
