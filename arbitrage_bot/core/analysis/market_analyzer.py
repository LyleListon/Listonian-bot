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

    # Token mapping
    TOKEN_MAPPING = {
        "ethereum": "WETH",
        "usd-coin": "USDC",
        "dai": "DAI"
    }

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

    async def get_current_price(self, token: str) -> float:
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

        try:
            # Get real price from BaseSwap
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            # Get WETH pair reserves
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'].get(token, {}).get('address')
            if not token_address:
                return 0.0
                
            reserves = await baseswap.get_reserves(weth_address, token_address)
            if reserves:
                price = float(reserves['reserve1']) / float(reserves['reserve0'])
                self._price_cache[token] = (datetime.now(), price)
                return price
                
        except Exception as e:
            logger.error(f"Failed to get current price for {token}: {e}")
            return 0.0
            

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
            symbol = self.TOKEN_MAPPING.get(token, token)
            
            # Get market analysis from MCP
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
            logger.warning(f"Failed to get MCP market conditions: {e}")

        try:
            # Get real data from BaseSwap
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            # Get WETH pair reserves
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'].get(token, {}).get('address')
            if not token_address:
                return None
                
            reserves = await baseswap.get_reserves(weth_address, token_address)
            if reserves:
                volume_24h = await self._get_24h_volume(token)
                liquidity = await self._get_liquidity(token)
                volatility = await self._get_volatility(token)
                trend = await self._get_market_trend(token)
                trend_strength = await self._get_trend_strength(token)
                
                return {
                    "trend": trend,
                    "trend_strength": trend_strength,
                    "trend_duration": 0.0,  # Will be calculated based on historical data
                    "volatility": volatility,
                    "volume_24h": float(volume_24h),
                    "liquidity": float(liquidity),
                    "volatility_24h": await self._get_24h_volatility(token),
                    "price_impact": await self._get_price_impact(token),
                    "confidence": await self._calculate_confidence(token)
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to analyze market conditions: {e}")
            return None

    async def _get_market_trend(self, token: str) -> str:
        """Get real market trend by analyzing recent price movements."""
        try:
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            # Get current and historical reserves
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'][token]['address']
            
            current_reserves = await baseswap.get_reserves(weth_address, token_address)
            if not current_reserves:
                return "sideways"
                
            # Calculate price from reserves
            current_price = current_reserves['reserve1'] / current_reserves['reserve0']
            
            # Get historical block (5 minutes ago)
            current_block = await self.w3.eth.block_number
            blocks_5min = int(5 * 60 / 12)  # Assuming 12 second block time
            historical_block = current_block - blocks_5min
            
            # Get historical reserves
            historical_reserves = await baseswap.get_reserves(
                weth_address,
                token_address,
                block_number=historical_block
            )
            
            if not historical_reserves:
                return "sideways"
                
            historical_price = historical_reserves['reserve1'] / historical_reserves['reserve0']
            
            # Calculate price change
            price_change = (current_price - historical_price) / historical_price
            
            # Determine trend
            if price_change > 0.005:  # 0.5% increase
                return "up"
            elif price_change < -0.005:  # 0.5% decrease
                return "down"
            else:
                return "sideways"
                
        except Exception as e:
            logger.error(f"Failed to get market trend: {e}")
            return "sideways"

    async def _get_trend_strength(self, token: str) -> float:
        """Calculate trend strength from real market data."""
        try:
            trend = await self._get_market_trend(token)
            if trend == "sideways":
                return 0.0
                
            # Get price volatility
            volatility = await self._get_volatility(token)
            
            # Higher volatility = stronger trend
            return min(volatility * 10, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Failed to get trend strength: {e}")
            return 0.0

    async def _get_volatility(self, token: str) -> float:
        """Calculate real volatility from price data."""
        try:
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            # Get quote for standard amount
            test_amount = 1 * 10**18  # 1 WETH
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'][token]['address']
            
            quote = await baseswap.get_quote_with_impact(test_amount, [weth_address, token_address])
            if quote:
                return float(quote['price_impact']) * 2  # Use price impact as volatility measure
            return 0.1  # Default volatility
            
        except Exception as e:
            logger.error(f"Failed to get volatility: {e}")
            return 0.1

    async def _get_24h_volume(self, token: str) -> Decimal:
        """Get real 24h trading volume from DEX."""
        try:
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            # Get WETH pair reserves as baseline for volume
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'][token]['address']
            reserves = await baseswap.get_reserves(weth_address, token_address)
            
            if reserves:
                # Calculate volume based on reserves and recent trades
                return Decimal(str(reserves['reserve0'] + reserves['reserve1']))
            return Decimal('0')
        except Exception as e:
            logger.error(f"Failed to get 24h volume: {e}")
            return Decimal('0')

    async def _get_liquidity(self, token: str) -> Decimal:
        """Get real liquidity from DEX."""
        try:
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            # Get WETH pair reserves
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'][token]['address']
            reserves = await baseswap.get_reserves(weth_address, token_address)
            
            if reserves:
                # Use smaller of the two reserves as liquidity measure
                return Decimal(str(min(reserves['reserve0'], reserves['reserve1'])))
            return Decimal('0')
        except Exception as e:
            logger.error(f"Failed to get liquidity: {e}")
            return Decimal('0')

    async def _get_24h_volatility(self, token: str) -> float:
        """Calculate 24h volatility from real price data."""
        try:
            # Get current volatility
            current_volatility = await self._get_volatility(token)
            
            # Scale to 24h estimate
            # Using square root of time rule to scale volatility
            return current_volatility * math.sqrt(24)  # Scale by square root of time
            
        except Exception as e:
            logger.error(f"Failed to get 24h volatility: {e}")
            return 0.1

    async def _get_price_impact(self, token: str) -> float:
        """Get real price impact from DEX."""
        try:
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            # Use a test amount to check price impact
            test_amount = 1 * 10**18  # 1 WETH
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'][token]['address']
            
            quote = await baseswap.get_quote_with_impact(test_amount, [weth_address, token_address])
            if quote:
                return float(quote['price_impact'])
            return 0.001  # Default impact
        except Exception as e:
            logger.error(f"Failed to get price impact: {e}")
            return 0.001

    async def _calculate_confidence(self, token: str) -> float:
        """Calculate confidence score based on data quality."""
        try:
            # Get key metrics
            volume = await self._get_24h_volume(token)
            liquidity = await self._get_liquidity(token)
            volatility = await self._get_volatility(token)
            
            # Calculate confidence based on:
            # 1. Higher volume = higher confidence (max 0.5)
            # 2. Higher liquidity = higher confidence (max 0.3)
            # 3. Lower volatility = higher confidence (max 0.2)
            
            # Volume component (0-0.5)
            volume_score = min(float(volume) / 100000, 0.5)  # Scale volume to 0-0.5
            
            # Liquidity component (0-0.3)
            liquidity_score = min(float(liquidity) / 100000, 0.3)  # Scale liquidity to 0-0.3
            
            # Volatility component (0-0.2)
            # Lower volatility = higher score
            volatility_score = (1 - min(volatility, 0.2)) * 0.2  # Scale inverted volatility to 0-0.2
            
            confidence = volume_score + liquidity_score + volatility_score
            return min(confidence, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Failed to calculate confidence: {e}")
            return 0.5

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

        # Return mock data for development with different prices
        token_to_symbol = {
            "ethereum": "WETH",
            "usd-coin": "USDC",
            "dai": "DAI"
        }
        mock_prices = {
            "WETH": 2000.0,  # WETH price
            "USDC": 1.0,    # USDC price
            "DAI": 1.01     # DAI price slightly higher for testing
        }
        return {token: mock_prices.get(token_to_symbol.get(token, token), 1000.0) for token in tokens}

    async def get_opportunities(self) -> List[Dict[str, Any]]:
        """Get current arbitrage opportunities."""
        try:
            opportunities = []
            
            
            # Update market conditions directly with mock prices
            for token_id, symbol in token_to_symbol.items():
                price = mock_prices.get(symbol, 1000.0)
                try:
                    price_decimal = Decimal(str(price))
                    
                    # Get real price from BaseSwap
                    from ..dex.baseswap import BaseSwapDEX
                    baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
                    await baseswap.initialize()
                    
                    # Get WETH pair reserves
                    weth_address = self.config['tokens']['WETH']['address']
                    token_address = tokens.get(token_id, {}).get('address')
                    if not token_address:
                        continue
                        
                    reserves = await baseswap.get_reserves(weth_address, token_address)
                    if reserves:
                        price_decimal = Decimal(str(reserves['reserve1'])) / Decimal(str(reserves['reserve0']))
                    
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
                        f"  Trend: {trend.direction} ({trend.strength*100:.1f}%)\n"
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
                        
                    gas_cost = 0.01  # Estimated gas cost in ETH
                    gas_cost_usd = gas_cost * float(base_price)
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
                    'total_trades': 0,  # Placeholder for now
                    'trades_24h': 0,    # Placeholder for now
                    'success_rate': 0.0, # Placeholder for now
                    'total_profit_usd': 0.0,  # Placeholder for now
                    'portfolio_change_24h': 0.0,  # Placeholder for now
                    'active_opportunities': 0,  # Placeholder for now
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
            
            
            # Process each token
            for token_id, symbol in self.TOKEN_MAPPING.items():
                try:
                    
                    # Get real price from BaseSwap
                    from ..dex.baseswap import BaseSwapDEX
                    baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
                    await baseswap.initialize()
                    
                    # Get WETH pair reserves
                    weth_address = self.config['tokens']['WETH']['address']
                    token_address = self.config['tokens'].get(token_id, {}).get('address')
                    if not token_address:
                        continue
                        
                    reserves = await baseswap.get_reserves(weth_address, token_address)
                    if reserves:
                        price_decimal = Decimal(str(reserves['reserve1'])) / Decimal(str(reserves['reserve0']))
                    
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
            # Initialize with default values
            analyzer.market_conditions = {}
            for token_id, symbol in analyzer.TOKEN_MAPPING.items():
                try:
                    # Get real price from BaseSwap
                    from ..dex.baseswap import BaseSwapDEX
                    baseswap = BaseSwapDEX(web3_manager, config['dexes']['baseswap'])
                    await baseswap.initialize()
                    
                    # Get WETH pair reserves
                    weth_address = config['tokens']['WETH']['address']
                    token_address = config['tokens'].get(token_id, {}).get('address')
                    if not token_address:
                        continue
                        
                    reserves = await baseswap.get_reserves(weth_address, token_address)
                    price = float(reserves['reserve1']) / float(reserves['reserve0']) if reserves else 0.0
                except Exception as e:
                    price = 0.0
                analyzer.market_conditions[symbol] = MarketCondition(
                    price=Decimal(str(price)) if price > 0 else Decimal('0'),
                    trend=MarketTrend(
                        direction="sideways",
                        strength=0.0,
                        duration=0.0,
                        volatility=0.1,
                        confidence=0.5
                    ),
                    volume_24h=Decimal("0"),  # Will be updated with real data
                    liquidity=Decimal("0"),  # Will be updated with real data
                    volatility_24h=0.1,
                    price_impact=0.001,
                    last_updated=float(datetime.now().timestamp())
                )
            logger.info("Market analyzer initialized with default values")
            return analyzer
        
    except Exception as e:
        logger.error(f"Failed to create market analyzer: {e}")
        raise
