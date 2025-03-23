import asyncio
import logging
from typing import Dict, Any, List, Optional

from ..ml.model_interface import MLSystem
from ..ml.price_validator import PriceValidator

logger = logging.getLogger(__name__)

class EnhancedMarketAnalyzer:
    """Enhanced market analyzer with ML capabilities."""
    
    def __init__(self):
        self._initialized = False
        self._lock = asyncio.Lock()
        self._ml_system = MLSystem()
        self._price_validator = PriceValidator()
    
    async def initialize(self) -> None:
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing enhanced market analyzer")
            
            try:
                # Initialize components
                await self._ml_system.initialize()
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
            price_validation = await self._price_validator.validate_prices(
                prices=prices,
                sources=sources
            )
            
            if not price_validation["is_valid"]:
                logger.warning(
                    "Price validation failed",
                    extra={
                        "validation": price_validation,
                        "prices": prices,
                        "sources": sources
                    }
                )
                return {
                    "is_valid": False,
                    "reason": "Price validation failed",
                    "validation": price_validation
                }
            
            # Analyze market data
            analysis = await self._ml_system.analyze_market_data(market_data)
            
            return {
                "is_valid": True,
                "analysis": analysis,
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
                await self._ml_system.cleanup()
                await self._price_validator.cleanup()
                
                self._initialized = False
                logger.info("Enhanced market analyzer cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up enhanced market analyzer: {e}", exc_info=True)
                raise
