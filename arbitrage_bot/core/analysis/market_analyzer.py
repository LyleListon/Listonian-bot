"""Market analysis utilities."""

__all__ = [
    'MarketAnalyzer',
    'create_market_analyzer'
]

import logging
import math
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from ..web3.web3_manager import Web3Manager
from ..models.opportunity import Opportunity
from ..models.market_models import MarketCondition, MarketTrend, PricePoint

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """Analyzes market conditions and opportunities."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize market analyzer."""
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        self._price_cache = {}
        self._cache_duration = timedelta(seconds=30)  # Cache prices for 30 seconds
        self.market_conditions = {}  # Store market conditions for each token
        self.dex_instances = {}  # Store DEX instances
        self.dex_manager = None  # Will be set by DEX manager
        self.initialized = False
        logger.debug("Market analyzer initialized")

    def set_dex_manager(self, dex_manager: Any):
        """Set the DEX manager instance."""
        self.dex_manager = dex_manager
        logger.debug("DEX manager set in market analyzer")

    async def initialize(self) -> bool:
        """Initialize the market analyzer."""
        try:
            if not self.dex_manager:
                logger.error("DEX manager not set")
                return False
            
            self.initialized = True
            return True
        except Exception as e:
            logger.error("Failed to initialize market analyzer: %s", str(e))
            return False

    async def get_market_condition(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get current market condition for token."""
        try:
            if not self.initialized:
                await self.initialize()

            # If token is a string (symbol), get token data from config
            if isinstance(token, str):
                token_data = self.config.get('tokens', {}).get(token)
                if not token_data:
                    logger.error("Token %s not found in config", token)
                    return None
            else:
                token_data = token

            # Get real price data
            if not token_data or 'address' not in token_data:
                logger.error("Invalid token data: %s", str(token_data))
                return None

            price = await self._fetch_real_price(token_data)
            price_decimal = Decimal(str(price))

            # Create market condition
            condition = {
                'price': float(price_decimal),
                'trend': {
                    'direction': 'sideways',
                    'strength': 0.0,
                    'duration': 0.0,
                    'volatility': 0.0,
                    'confidence': 0.0
                },
                'volume_24h': 0.0,
                'liquidity': 0.0,
                'volatility_24h': 0.0,
                'price_impact': 0.0,
                'last_updated': datetime.now().timestamp()
            }

            return condition

        except Exception as e:
            logger.error("Failed to get market condition: %s", str(e))
            return None

    def _get_dex_instance(self, dex_name: str) -> Any:
        """Get DEX instance by name."""
        if not self.dex_manager:
            raise ValueError("DEX manager not set")
        return self.dex_manager.get_dex(dex_name)

    async def _fetch_real_price(self, token: Dict[str, Any]) -> float:
        """Fetch real price data from all enabled DEXes."""
        try:
            if not self.initialized:
                await self.initialize()

            # Ensure token address is valid
            address = token['address']
            if not address or not self.w3.is_address(address):
                raise ValueError("Invalid token address: %s", address)

            # Get prices from enabled DEXes
            prices = await self.dex_manager.get_token_price(address)
            if not prices:
                raise ValueError("No valid prices found")

            # Calculate median price to filter out outliers
            price_list = list(prices.values())
            price_list.sort()
            mid = len(price_list) // 2
            if len(price_list) % 2 == 0:
                return float((price_list[mid - 1] + price_list[mid]) / 2)
            else:
                return float(price_list[mid])

        except Exception as e:
            logger.error("Error fetching real price: %s", str(e))
            raise

    def validate_price(self, price: float) -> bool:
        """Validate if a price is valid."""
        if not isinstance(price, (int, float)):
            return False
        return price > 0 and not math.isinf(price) and not math.isnan(price)

    def get_cached_price(self, token: str) -> Optional[float]:
        """Get price from cache if available and not expired."""
        cache_entry = self._price_cache.get(token)
        if cache_entry:
            timestamp, price = cache_entry
            if datetime.now() - timestamp < self._cache_duration:
                return price
        return None

    async def get_current_price(self, token: str) -> float:
        """Get current price, using cache if available."""
        if not self.initialized:
            await self.initialize()

        cached_price = self.get_cached_price(token)
        if cached_price is not None:
            return cached_price

        token_data = self.config.get('tokens', {}).get(token)
        if not token_data:
            raise ValueError("Token %s not found in config", token)

        price = await self._fetch_real_price(token_data)
        if not self.validate_price(price):
            raise ValueError("Invalid price received for %s: %s", token, str(price))

        self._price_cache[token] = (datetime.now(), price)
        return price

    def calculate_price_difference(self, price1: float, price2: float) -> float:
        """Calculate percentage difference between two prices."""
        if not (self.validate_price(price1) and self.validate_price(price2)):
            raise ValueError("Invalid prices provided")
        return abs(price2 - price1) / price1

    async def get_opportunities(self) -> List[Opportunity]:
        """Get current arbitrage opportunities."""
        try:
            if not self.initialized:
                await self.initialize()

            opportunities = []
            tokens = self.config.get("tokens", {})
            
            for token_id, token_data in tokens.items():
                if not token_data or 'address' not in token_data:
                    logger.debug("Invalid token data for %s", token_id)
                    continue

                # Get prices from enabled DEXes
                prices = await self.dex_manager.get_token_price(token_data['address'])
                
                # Find arbitrage opportunities
                if len(prices) >= 2:
                    min_price = min(prices.values())
                    max_price = max(prices.values())
                    price_diff = (max_price - min_price) / min_price
                    
                    # If price difference > 0.5%
                    if price_diff > Decimal("0.005"):
                        buy_dex = min(prices.items(), key=lambda x: x[1])[0]
                        sell_dex = max(prices.items(), key=lambda x: x[1])[0]
                        
                        opportunity = Opportunity(
                            token_id=token_id,
                            token_address=token_data['address'],
                            buy_dex=buy_dex,
                            sell_dex=sell_dex,
                            buy_price=min_price,
                            sell_price=max_price,
                            profit_margin=price_diff,
                            market_condition=None,  # No market condition needed for opportunities
                            timestamp=datetime.now().timestamp()
                        )
                        opportunities.append(opportunity)
            
            return opportunities
            
        except Exception as e:
            logger.error("Failed to get opportunities: %s", str(e))
            return []

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        try:
            return {
                'market_conditions': self.market_conditions,
                'dex_performance': {
                    dex: {'success_rate': 1.0, 'avg_response_time': 0}
                    for dex in self.config.get('dexes', {}).keys()
                },
                'timestamp': datetime.now().timestamp()
            }
        except Exception as e:
            logger.error("Failed to get performance metrics: %s", str(e))
            return {}


async def create_market_analyzer(
    web3_manager: Optional[Web3Manager] = None,
    config: Optional[Dict[str, Any]] = None,
    dex_manager: Optional[Any] = None
) -> MarketAnalyzer:
    """Create and initialize a market analyzer instance."""
    try:
        if not web3_manager:
            web3_manager = Web3Manager()
            web3_manager.connect()
            
        if not config:
            from ...utils.config_loader import load_config
            config = load_config()
            
        analyzer = MarketAnalyzer(web3_manager=web3_manager, config=config)
        
        # Set DEX manager if provided
        if dex_manager:
            analyzer.set_dex_manager(dex_manager)
            
        # Initialize the analyzer
        if not await analyzer.initialize():
            raise RuntimeError("Failed to initialize market analyzer")
            
        logger.debug("Market analyzer created and initialized successfully")
        return analyzer
        
    except Exception as e:
        logger.error("Failed to create market analyzer: %s", str(e))
        raise
