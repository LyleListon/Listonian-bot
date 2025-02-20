"""Market analysis utilities."""

__all__ = [
    'MarketAnalyzer',
    'create_market_analyzer'
]

import logging
import math
import time
import eventlet
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
        logger.debug("Market analyzer initialized")

    def set_dex_manager(self, dex_manager: Any):
        """Set the DEX manager instance."""
        self.dex_manager = dex_manager
        logger.debug("DEX manager set in market analyzer")

    def get_market_condition(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get current market condition for token."""
        try:
            # If token is a string (symbol), get token data from config
            if isinstance(token, str):
                token_data = self.config.get('tokens', {}).get(token)
                if not token_data:
                    raise ValueError(f"Token {token} not found in config")
            else:
                token_data = token

            # Get real price data
            if not token_data or 'address' not in token_data:
                raise ValueError(f"Invalid token data: {token_data}")
            price = eventlet.spawn(self._fetch_real_price, token_data).wait()
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
            logger.error(f"Failed to get market condition: {e}")
            return None

    def _get_dex_instance(self, dex_name: str) -> Any:
        """Get DEX instance by name."""
        if not self.dex_manager:
            raise ValueError("DEX manager not set")
        return self.dex_manager.get_dex(dex_name)

    def _fetch_real_price(self, token: Dict[str, Any]) -> float:
        """Fetch real price data from all enabled DEXes."""
        try:
            # Ensure token address is valid
            address = token['address']
            if not address or not self.w3.is_address(address):
                raise ValueError(f"Invalid token address: {address}")

            # Get all enabled DEXes
            enabled_dexes = [
                name for name, config in self.config.get('dexes', {}).items()
                if config.get('enabled', False)
            ]

            if not enabled_dexes:
                raise ValueError("No enabled DEXes found in config")

            prices = []
            errors = []

            # Try to get price from each enabled DEX
            for dex_name in enabled_dexes:
                try:
                    dex = self._get_dex_instance(dex_name)
                    if not dex:
                        logger.debug(f"Failed to get {dex_name} instance")
                        continue

                    # Ensure DEX is initialized
                    if not dex.initialized:
                        if not eventlet.spawn(dex.initialize).wait():
                            logger.debug(f"Failed to initialize {dex_name}")
                            continue

                    price = eventlet.spawn(dex.get_token_price, address).wait()
                    if self.validate_price(price):
                        prices.append(price)
                    else:
                        logger.debug(f"Invalid price from {dex_name}: {price}")

                except Exception as e:
                    errors.append(f"{dex_name}: {str(e)}")
                    continue

            if not prices:
                error_msg = "Failed to get valid price from any DEX"
                if errors:
                    error_msg += f". Errors: {'; '.join(errors)}"
                raise ValueError(error_msg)

            # Calculate median price to filter out outliers
            prices.sort()
            mid = len(prices) // 2
            if len(prices) % 2 == 0:
                return (prices[mid - 1] + prices[mid]) / 2
            else:
                return prices[mid]

        except Exception as e:
            logger.error(f"Error fetching real price: {e}")
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

    def get_current_price(self, token: str) -> float:
        """Get current price, using cache if available."""
        cached_price = self.get_cached_price(token)
        if cached_price is not None:
            return cached_price

        token_data = self.config.get('tokens', {}).get(token)
        if not token_data:
            raise ValueError(f"Token {token} not found in config")

        price = eventlet.spawn(self._fetch_real_price, token_data).wait()
        if not self.validate_price(price):
            raise ValueError(f"Invalid price received for {token}: {price}")

        self._price_cache[token] = (datetime.now(), price)
        return price

    def calculate_price_difference(self, price1: float, price2: float) -> float:
        """Calculate percentage difference between two prices."""
        if not (self.validate_price(price1) and self.validate_price(price2)):
            raise ValueError("Invalid prices provided")
        return abs(price2 - price1) / price1

    def get_opportunities(self) -> List[Opportunity]:
        """Get current arbitrage opportunities."""
        try:
            opportunities = []
            tokens = self.config.get("tokens", {})
            
            for token_id, token_data in tokens.items():
                if not token_data or 'address' not in token_data:
                    logger.debug(f"Invalid token data for {token_id}")
                    continue
                    
                # Get all enabled DEXes
                enabled_dexes = [
                    name for name, config in self.config.get('dexes', {}).items()
                    if config.get('enabled', False)
                ]

                if not enabled_dexes:
                    logger.debug("No enabled DEXes found in config")
                    continue

                # Get prices from all enabled DEXes
                prices = {}
                for dex_name in enabled_dexes:
                    try:
                        dex = self._get_dex_instance(dex_name)
                        if not dex:
                            logger.debug(f"Failed to get {dex_name} instance")
                            continue
                            
                        # Ensure DEX is initialized
                        if not dex.initialized and not eventlet.spawn(dex.initialize).wait():
                            logger.debug(f"Failed to initialize {dex_name}")
                            continue
                            
                        price = eventlet.spawn(dex.get_token_price, token_data['address']).wait()
                        if self.validate_price(price):
                            prices[dex_name] = Decimal(str(price))
                        else:
                            logger.debug(f"Invalid price from {dex_name}: {price}")
                    except Exception as e:
                        logger.debug(f"Failed to get price from {dex_name}: {e}")
                
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
            logger.error(f"Failed to get opportunities: {e}")
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
            logger.error(f"Failed to get performance metrics: {e}")
            return {}


def create_market_analyzer(
    web3_manager: Optional[Web3Manager] = None,
    config: Optional[Dict[str, Any]] = None,
    dex_manager: Optional[Any] = None
) -> MarketAnalyzer:
    """Create and initialize a market analyzer instance."""
    try:
        if not web3_manager:
            web3_manager = Web3Manager()
            eventlet.spawn(web3_manager.connect).wait()
            
        if not config:
            from ...utils.config_loader import load_config
            config = load_config()
            
        analyzer = MarketAnalyzer(web3_manager=web3_manager, config=config)
        
        # Set DEX manager if provided
        if dex_manager:
            analyzer.set_dex_manager(dex_manager)
            
        logger.debug("Market analyzer created and initialized successfully")
        return analyzer
        
    except Exception as e:
        logger.error(f"Failed to create market analyzer: {e}")
        raise
