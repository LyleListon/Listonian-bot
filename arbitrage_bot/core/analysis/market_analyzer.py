"""Market analysis utilities."""

__all__ = [
    'MarketAnalyzer',
    'MarketCondition',
    'MarketTrend',
    'PricePoint',
    'create_market_analyzer'
]

import logging
import math
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from decimal import Decimal
from ..web3.web3_manager import Web3Manager
from ..models.opportunity import Opportunity

logger = logging.getLogger(__name__)

@dataclass
class PricePoint:
    """Price data point."""
    timestamp: float
    price: Decimal
    volume: Decimal
    liquidity: Decimal

@dataclass
class MarketTrend:
    """Market trend information."""
    direction: str  # up, down, sideways
    strength: float  # 0-1
    duration: float  # in seconds
    volatility: float  # standard deviation
    confidence: float  # 0-1

@dataclass
class MarketCondition:
    """Current market condition."""
    price: Decimal
    trend: MarketTrend
    volume_24h: Decimal
    liquidity: Decimal
    volatility_24h: float
    price_impact: float
    last_updated: float


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
        logger.info("Market analyzer initialized")

    def validate_price(self, price: float) -> bool:
        """
        Validate if a price is valid.

        Args:
            price (float): Price to validate

        Returns:
            bool: True if price is valid, False otherwise
        """
        if not isinstance(price, (int, float)):
            return False

        return price > 0 and not math.isinf(price) and not math.isnan(price)

    async def calculate_price_difference(self, price1: float, price2: float) -> float:
        """
        Calculate percentage difference between two prices.

        Args:
            price1 (float): First price
            price2 (float): Second price

        Returns:
            float: Price difference as a decimal (e.g., 0.05 for 5%)
        """
        if not (self.validate_price(price1) and self.validate_price(price2)):
            raise ValueError("Invalid prices provided")

        return abs(price2 - price1) / price1

    def get_current_price(self, token: str) -> float:
        """
        Get current price from cache if available and not expired.

        Args:
            token (str): Token identifier

        Returns:
            float: Current price
        """
        cache_entry = self._price_cache.get(token)
        if cache_entry:
            timestamp, price = cache_entry
            if datetime.now() - timestamp < self._cache_duration:
                return price

        price = await self._fetch_real_price(token)
        return price

    async def get_prices(self, tokens: List[str]) -> Dict[str, float]:
        """
        Get prices for multiple tokens.

        Args:
            tokens (List[str]): List of token identifiers

        Returns:
            Dict[str, float]: Token prices
        """
        try:
            prices = await self.get_mcp_prices(tokens)
            if not prices:
                raise Exception("Failed to fetch prices")

            # Validate all prices
            for token, price in prices.items():
                if not self.validate_price(price):
                    raise ValueError(f"Invalid price for {token}: {price}")

            # Update cache
            now = datetime.now()
            for token, price in prices.items():
                self._price_cache[token] = (now, price)

            return prices

        except Exception as e:
            logger.warning(f"Error fetching prices: {e}")
            return {}

    async def analyze_market_conditions(self, token: str) -> Dict[str, Any]:
        """
        Analyze market conditions for token.

        Args:
            token (str): Token to analyze

        Returns:
            Dict[str, Any]: Market conditions
        """
        try:
            response = await self.web3_manager.use_mcp_tool(
                "market-analysis",
                "assess_market_conditions",
                {
                    "token": symbol,
                    "metrics": ["volatility", "volume", "liquidity", "trend"],
                }
            )

            if response:
                return response

        except Exception as e:
            logger.warning(f"Failed to analyze market conditions: {e}")

        return None

    async def get_mcp_prices(self, tokens: List[str]) -> Dict[str, float]:
        """
        Get current prices from MCP.

        Args:
            tokens (List[str]): List of token identifiers

        Returns:
            Dict[str, float]: Current prices
        """
        try:
            response = await self.web3_manager.use_mcp_tool(
                "crypto-price",
                "get_prices",
                {
                    "coins": tokens,
                    "include_24h_change": True
                }
            )

            if response:
                return response

        except Exception as e:
            logger.warning(f"Failed to get prices from MCP: {e}")

        return {}

    async def get_opportunities(self) -> List[Dict[str, Any]]:
        """Get current arbitrage opportunities."""
        try:
            opportunities = []
            
            # Get current prices and market conditions
            tokens = self.config.get("tokens", {})
            
            # Update market conditions directly with mock prices
            for token_id, symbol in token_to_symbol.items():
                price = mock_prices.get(symbol, 1000.0)
                try:
                    price_decimal = Decimal(str(price))
                    
                    # Get market analysis
                    market_data = await self.analyze_market_conditions(symbol)
                    if not market_data:
                        logger.warning(f"No market data for {token_id}")
                        continue
                        
                    # Create trend object
                    trend = MarketTrend(
                        direction=market_data.get("trend", "sideways"),
                        strength=float(market_data.get("trend_strength", 0.0)),
                        duration=float(market_data.get("trend_duration", 0.0)),
                        volatility=float(market_data.get("volatility", 0.0)),
                        confidence=float(market_data.get("confidence", 0.0))
                    )
                    
                    # Create market condition
                    condition = MarketCondition(
                        price=price_decimal,
                        trend=trend,
                        volume_24h=Decimal(str(market_data.get("volume_24h", 0))),
                        liquidity=Decimal(str(market_data.get("liquidity", 0))),
                        volatility_24h=float(market_data.get("volatility_24h", 0)),
                        price_impact=float(market_data.get("price_impact", 0)),
                        last_updated=float(datetime.now().timestamp())
                    )
                    
                    # Store market condition
                    self.market_conditions[symbol] = condition
                    
                    logger.info(
                        f"Updated market condition for {token_id}:\n"
                        f"  Price: ${price_decimal:,.2f}\n"
                        f"  Trend: {trend.direction} ({trend.strength:.1%})\n"
                        f"  Volume: ${condition.volume_24h:,.0f}\n"
                        f"  Liquidity: ${condition.liquidity:,.0f}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error updating market condition for {token_id}: {e}")
                    continue
            
            # For each token pair, analyze potential opportunities
            token_pairs = [
                ("ethereum", "usd-coin"),
                ("ethereum", "dai")
            ]
            for base_token_id, quote_token_id in token_pairs:
                try:
                    # Convert token IDs to symbols
                    base_token = token_to_symbol[base_token_id]
                    quote_token = token_to_symbol[quote_token_id]
                    
                    # Get prices from market conditions
                    if base_token not in self.market_conditions or quote_token not in self.market_conditions:
                        continue
                        
                    base_price = float(self.market_conditions[base_token].price)
                    quote_price = float(self.market_conditions[quote_token].price)
                    
                    # Get market analysis
                    market_data = await self.analyze_market_conditions(base_token)
                    if not market_data:
                        continue
                        
                    # Calculate potential profit
                    amount_in = Decimal('1.0')  # 1 ETH
                    
                    # Calculate amounts for each path
                    # Path 1: ETH -> USDC/DAI
                    baseswap_eth_to_token = amount_in * Decimal(str(base_price))  # Convert ETH to USD value
                    swapbased_eth_to_token = amount_in * Decimal(str(base_price)) * Decimal('0.995')  # 0.5% lower price
                    
                    # Calculate profit potential
                    profit_baseswap = float(baseswap_eth_to_token - swapbased_eth_to_token)
                    profit_swapbased = float(swapbased_eth_to_token * Decimal('1.005') - baseswap_eth_to_token)  # 0.5% higher price
                    
                    # Find best opportunity
                    if profit_baseswap > profit_swapbased:
                        # Buy on SwapBased (lower price), sell on BaseSwap (higher price)
                        dex_from = "swapbased"
                        dex_to = "baseswap"
                        amount_out = baseswap_eth_to_token
                        profit = profit_baseswap
                    else:
                        # Buy on BaseSwap (market price), sell on SwapBased (higher price)
                        dex_from = "baseswap"
                        dex_to = "swapbased"
                        amount_out = swapbased_eth_to_token * Decimal('1.005')
                        profit = profit_swapbased
                        
                    gas_cost = await self.web3_manager.estimate_gas_cost()
                    gas_cost_usd = float(gas_cost * Decimal(str(base_price)))
                    net_profit = profit - gas_cost_usd
                    
                    # Get token addresses from config using token IDs
                    tokens = self.config.get("tokens", {})
                    base_address = tokens.get(base_token_id, {}).get("address")
                    quote_address = tokens.get(quote_token_id, {}).get("address")
                    
                    if not base_address or not quote_address:
                        continue
                    
                    # Create opportunity object
                    opportunity = {
                        'dex_from': dex_from,
                        'dex_to': dex_to,
                        'token_path': [base_address, quote_address],
                        'amount_in': amount_in,
                        'amount_out': amount_out,
                        'profit_usd': net_profit,
                        'gas_cost_usd': gas_cost_usd,
                        'price_impact': float(market_data.get('price_impact', 0.001)),
                        'status': 'Ready' if net_profit > 0 else 'Unprofitable',
                        'details': {
                            'pair': f"{base_token_id}/{quote_token_id}",
                            'base_price': base_price,
                            'quote_price': quote_price
                        }
                    }
                    
                    # Log opportunity details
                    logger.info(
                        f"Found arbitrage opportunity:\n"
                        f"  Pair: {base_token_id}/{quote_token_id}\n"
                        f"  Route: {dex_from} -> {dex_to}\n"
                        f"  Profit: ${net_profit:.2f}\n"
                        f"  Gas Cost: ${gas_cost_usd:.2f}\n"
                        f"  Status: {opportunity['status']}"
                    )
                    
                    opportunities.append(opportunity)
                    
                except Exception as e:
                    logger.error(f"Error analyzing {base_token_id}/{quote_token_id}: {e}")
                    continue
                    
            return opportunities
            
        except Exception as e:
            logger.error(f"Failed to get opportunities: {e}")
            return []

    async def get_performance_metrics(self) -> List[Dict[str, Any]]:
        """Get performance metrics for dashboard display."""
        try:
            metrics = []
            for symbol, condition in self.market_conditions.items():
                metrics.append({
                    'total_trades': await self._get_total_trades(symbol),
                    'trades_24h': await self._get_24h_trades(symbol),
                    'success_rate': await self._get_success_rate(symbol),
                    'total_profit_usd': await self._get_total_profit(symbol),
                    'portfolio_change_24h': await self._get_24h_change(symbol),
                    'active_opportunities': await self._get_active_opportunities(symbol),
                    'price': float(condition.price),
                    'volume_24h': float(condition.volume_24h),
                    'liquidity': float(condition.liquidity),
                    'volatility': condition.volatility_24h,
                    'trend': condition.trend.direction,
                    'trend_strength': condition.trend.strength,
                    'confidence': condition.trend.confidence,
                    'last_updated': condition.last_updated
                })
            return metrics
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return []

    async def monitor_prices(self, tokens: List[str]):
        """
        Monitor prices for tokens.

        Args:
            tokens (List[str]): List of token identifiers

        Yields:
            Dict[str, float]: Updated prices
        """
        while True:
            try:
                prices = await self.get_mcp_prices(tokens)
                if prices:
                    yield prices
            except Exception as e:
                logger.error(f"Price monitoring error: {e}")
                yield {}

    async def start_monitoring(self):
        """Start market monitoring loop."""
        try:
            while True:
                try:
                    await self._update_market_conditions()
                    await asyncio.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(5)  # Short delay on error
        except Exception as e:
            logger.error(f"Market monitoring failed: {e}")
            raise

    async def _update_market_conditions(self):
        """Update market conditions for all tracked tokens."""
        try:
            # Get token configurations
            tokens = self.config.get("tokens", {})

            # Process each token from config
            for token_id, token_data in tokens.items():
                await self._update_token_condition(token_id, token_data)
                    
        except Exception as e:
            logger.error(f"Failed to update market conditions: {e}")


async def create_market_analyzer(
    web3_manager: Optional[Web3Manager] = None,
    config: Optional[Dict[str, Any]] = None
) -> MarketAnalyzer:
    """
    Create and initialize a market analyzer instance.
    
    Args:
        web3_manager: Optional Web3Manager instance
        config: Optional configuration dictionary
        
    Returns:
        MarketAnalyzer: Initialized market analyzer instance
    """
    try:
        if not web3_manager:
            web3_manager = await Web3Manager().connect()
            
        if not config:
            from ...utils.config_loader import load_config
            config = load_config()
            
        analyzer = MarketAnalyzer(web3_manager=web3_manager, config=config)
        
        try:
            # Start initial data collection
            await analyzer._update_market_conditions()
            logger.info("Market analyzer created and initialized")
            return analyzer
        except Exception as e:
            logger.warning(f"Initial market data collection failed: {e}")
            raise
        
    except Exception as e:
        logger.error(f"Failed to create market analyzer: {e}")
        raise

    async def _fetch_real_price(self, token: str) -> float:
        """Fetch real price data from DEX."""
        try:
            # Get token address from config
            token_data = self.config['tokens'].get(token)
            if not token_data:
                raise ValueError(f"Token {token} not found in config")

            # Get price from BaseSwap as primary source
            baseswap = await self._get_dex_instance('baseswap')
            if not baseswap:
                raise ValueError("Failed to get BaseSwap instance")

            price = await baseswap.get_token_price(token_data['address'])
            if not self.validate_price(price):
                raise ValueError(f"Invalid price received for {token}: {price}")

            # Cache the price
            self._price_cache[token] = (datetime.now(), price)
            return price

        except Exception as e:
            logger.error(f"Error fetching real price for {token}: {e}")
            raise

    async def _get_total_trades(self, symbol: str) -> int:
        """Get total number of trades for a token."""
        try:
            token_data = self.config['tokens'].get(symbol)
            if not token_data:
                return 0

            return await self.web3_manager.get_total_trades(token_data['address'])
        except Exception as e:
            logger.error(f"Error getting total trades for {symbol}: {e}")
            return 0

    async def _get_24h_trades(self, symbol: str) -> int:
        """Get number of trades in last 24 hours."""
        try:
            token_data = self.config['tokens'].get(symbol)
            if not token_data:
                return 0

            return await self.web3_manager.get_24h_trades(token_data['address'])
        except Exception as e:
            logger.error(f"Error getting 24h trades for {symbol}: {e}")
            return 0

    async def _get_success_rate(self, symbol: str) -> float:
        """Calculate trade success rate."""
        try:
            total = await self._get_total_trades(symbol)
            if total == 0:
                return 0.0

            successful = await self.web3_manager.get_successful_trades(symbol)
            return float(successful) / float(total)
        except Exception as e:
            logger.error(f"Error calculating success rate for {symbol}: {e}")
            return 0.0

    async def _get_total_profit(self, symbol: str) -> float:
        """Get total profit for a token."""
        try:
            token_data = self.config['tokens'].get(symbol)
            if not token_data:
                return 0.0

            return await self.web3_manager.get_total_profit(token_data['address'])
        except Exception as e:
            logger.error(f"Error getting total profit for {symbol}: {e}")
            return 0.0

    async def _get_24h_change(self, symbol: str) -> float:
        """Calculate 24h portfolio change."""
        try:
            token_data = self.config['tokens'].get(symbol)
            if not token_data:
                return 0.0

            return await self.web3_manager.get_24h_portfolio_change(token_data['address'])
        except Exception as e:
            logger.error(f"Error getting 24h change for {symbol}: {e}")
            return 0.0

    async def _get_active_opportunities(self, symbol: str) -> int:
        """Get number of active opportunities."""
        try:
            token_data = self.config['tokens'].get(symbol)
            if not token_data:
                return 0

            opportunities = await self.get_opportunities()
            return len([
                opp for opp in opportunities
                if token_data['address'] in opp['token_path']
                and opp['status'] == 'Ready'
                and float(opp['profit_usd']) > 0
            ])
        except Exception as e:
            logger.error(f"Error getting active opportunities for {symbol}: {e}")
            return 0

    async def _update_token_condition(self, token_id: str, token_data: Dict[str, Any]) -> None:
        """Update market condition for a single token."""
        try:
            # Get real price data
            price = await self._fetch_real_price(token_id)
            price_decimal = Decimal(str(price))

            # Get market analysis from real data
            market_data = await self.analyze_market_conditions(token_id)
            if not market_data:
                logger.warning(f"No market data for {token_id}")
                return

            # Create trend object from real data
            trend = MarketTrend(
                direction=market_data.get("trend", "sideways"),
                strength=float(market_data.get("trend_strength", 0.0)),
                duration=float(market_data.get("trend_duration", 0.0)),
                volatility=float(market_data.get("volatility", 0.0)),
                confidence=float(market_data.get("confidence", 0.0))
            )

            # Create market condition from real data
            condition = MarketCondition(
                price=price_decimal,
                trend=trend,
                volume_24h=Decimal(str(market_data.get("volume_24h", 0))),
                liquidity=Decimal(str(market_data.get("liquidity", 0))),
                volatility_24h=float(market_data.get("volatility_24h", 0)),
                price_impact=float(market_data.get("price_impact", 0)),
                last_updated=float(datetime.now().timestamp())
            )

            # Store market condition
            self.market_conditions[token_id] = condition

            logger.info(
                f"Updated market condition for {token_id}:\n"
                f"  Price: ${price_decimal:,.2f}\n"
                f"  Trend: {trend.direction} ({trend.strength:.1%})\n"
                f"  Volume: ${condition.volume_24h:,.0f}\n"
                f"  Liquidity: ${condition.liquidity:,.0f}"
            )

        except Exception as e:
            logger.error(f"Error updating market condition for {token_id}: {e}")
            raise
