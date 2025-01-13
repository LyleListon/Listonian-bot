"""Market analysis and trend detection."""

import logging
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean, median, stdev
from web3 import Web3
from ..web3.web3_manager import Web3Manager

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
    """Analyzes market conditions and trends."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize market analyzer.

        Args:
            web3_manager: Web3Manager instance
            config: Configuration dictionary
        """
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        
        # Price history
        self.price_history: Dict[str, List[PricePoint]] = {}  # token -> price points
        self.market_conditions: Dict[str, MarketCondition] = {}
        
        # Configuration
        self.update_interval = int(config.get("market_update_interval", 60))  # 1 minute
        self.history_length = int(config.get("price_history_hours", 24)) * 3600
        self.min_data_points = int(config.get("min_data_points", 10))
        self.trend_threshold = float(config.get("trend_threshold", 0.02))  # 2%
        
        # Performance metrics
        self.prediction_accuracy = 1.0
        self.last_update = 0
        
        logger.info("Market analyzer initialized")

    async def start_monitoring(self):
        """Start market monitoring loop."""
        try:
            while True:
                try:
                    # Update market conditions
                    await self._update_market_conditions()
                    
                    # Clean old data
                    self._clean_old_data()
                    
                    # Update metrics
                    self._update_metrics()
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    
                await asyncio.sleep(self.update_interval)
                
        except Exception as e:
            logger.error(f"Market monitoring failed: {e}")
            raise

    async def _update_market_conditions(self):
        """Update market conditions for tracked tokens."""
        try:
            current_time = time.time()
            if current_time - self.last_update < self.update_interval:
                return

            # Get token configurations
            tokens = self.config.get("tokens", {})
            
            # Get current prices from MCP
            token_ids = {
                "WETH": "ethereum",
                "USDC": "usd-coin"
            }
            
            try:
                response = await self.web3_manager.use_mcp_tool(
                    "crypto-price",
                    "get_prices",
                    {
                        "coins": list(token_ids.values()),
                        "include_24h_change": True
                    }
                )
                
                if not response:
                    logger.warning("Empty response from crypto-price MCP tool")
                    return
                    
                # Log raw response at debug level
                logger.debug(f"Raw price data: {json.dumps(response, indent=2)}")
                
                # Process and validate response
                if not isinstance(response, dict):
                    logger.warning("Invalid response format - not a dictionary")
                    return
                    
                # Handle both direct price data and nested 'prices' field
                prices = response.get('prices', response)
                if not isinstance(prices, dict):
                    logger.warning("Invalid response format - prices data is not a dictionary")
                    return
                    
                processed_response = {}
                for symbol, token_id in token_ids.items():
                    if token_id not in prices:
                        logger.warning(f"No price data for {symbol} ({token_id})")
                        continue
                        
                    token_data = prices[token_id]
                    if not isinstance(token_data, dict):
                        logger.warning(f"Invalid price data format for {symbol}: {token_data}")
                        continue
                        
                    # Handle both price_usd and usd field names
                    price = token_data.get('price_usd', token_data.get('usd'))
                    if price is None:
                        logger.warning(f"No price data found for {symbol}")
                        continue
                        
                    processed_response[token_id] = {
                        'usd': price,
                        'volume_24h': token_data.get('volume_24h', 0),
                        'change_24h': token_data.get('change_24h', 0)
                    }
                    logger.info(f"Got price for {symbol}: ${price:,.2f}")
                
                if not processed_response:
                    logger.warning("No valid price data found in response")
                    return
                
                response = processed_response
                
                # Process each token
                for symbol, token_id in token_ids.items():
                    try:
                        if token_id not in response:
                            logger.warning(f"No price data for {symbol} ({token_id})")
                            continue
                            
                        token_data = response[token_id]
                        if not isinstance(token_data, dict) or "usd" not in token_data:
                            logger.warning(f"Invalid price data format for {symbol}")
                            continue
                            
                        price = Decimal(str(token_data["usd"]))
                        volume = Decimal(str(token_data.get("volume_24h", 0)))
                        
                        # Get market analysis
                        market_response = await self.web3_manager.use_mcp_tool(
                            "market-analysis",
                            "assess_market_conditions",
                            {
                                "token": token_id,
                                "metrics": ["volatility", "volume", "trend"]
                            }
                        )
                        
                        if not market_response:
                            logger.warning(f"Empty market analysis response for {symbol}")
                            market_response = {
                                "metrics": {
                                    "volatility": 0.0,
                                    "volume": 0.0,
                                    "trend": "sideways"
                                }
                            }
                        
                        # Get pool liquidity from configured DEXs
                        liquidity = Decimal("0")
                        if symbol in tokens:
                            token_config = tokens[symbol]
                            total_liquidity = Decimal("0")
                            
                            # Get liquidity from each configured DEX
                            for dex_name, dex_config in self.config.get("dexes", {}).items():
                                try:
                                    if dex_name.lower() in ["baseswap", "pancakeswap"]:  # Only use configured DEXs
                                        pool_info = await self._get_pool_liquidity(token_config["address"], dex_name)
                                        total_liquidity += Decimal(str(pool_info["liquidity_usd"]))
                                except Exception as e:
                                    logger.warning(f"Failed to get {dex_name} pool liquidity: {e}")
                            
                            liquidity = total_liquidity
                        
                        # Create price point
                        point = PricePoint(
                            timestamp=current_time,
                            price=price,
                            volume=volume,
                            liquidity=liquidity
                        )
                        
                        # Add to history
                        if symbol not in self.price_history:
                            self.price_history[symbol] = []
                        self.price_history[symbol].append(point)
                        
                        # Calculate trend
                        trend = self._calculate_trend(symbol)
                        
                        # Calculate volatility
                        prices = [p.price for p in self.price_history[symbol]]
                        if len(prices) >= 2:
                            volatility = float(stdev(prices) / mean(prices))
                        else:
                            volatility = 0.0
                        
                        # Calculate price impact
                        price_impact = self._calculate_price_impact(symbol, liquidity)
                        
                        # Update market condition
                        self.market_conditions[symbol] = MarketCondition(
                            price=price,
                            trend=trend,
                            volume_24h=volume,
                            liquidity=liquidity,
                            volatility_24h=volatility,
                            price_impact=price_impact,
                            last_updated=current_time
                        )
                        
                        logger.info(
                            f"Market Update - {symbol}:\n"
                            f"  Price: ${price:,.2f}\n"
                            f"  Trend: {trend.direction} ({trend.strength:.1%})\n"
                            f"  Volume: ${volume:,.0f}\n"
                            f"  Liquidity: ${liquidity:,.0f}\n"
                            f"  Volatility: {volatility:.1%}\n"
                            f"  Price Impact: {price_impact:.1%}"
                        )
                    except Exception as e:
                        logger.error(f"Error processing token {symbol}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Failed to get prices from MCP: {e}")
                
            self.last_update = current_time
            
        except Exception as e:
            logger.error(f"Failed to update market conditions: {e}")

    async def _get_pool_liquidity(self, token_address: str, dex_name: str) -> Dict[str, Any]:
        """Get pool liquidity information for a specific DEX."""
        try:
            # Get WETH address
            weth_address = self.config["tokens"]["WETH"]["address"]
            
            # Get DEX config
            dex_config = self.config["dexes"][dex_name]
            
            # Load appropriate ABI based on DEX
            if dex_name.lower() == "baseswap":
                with open("abi/baseswap_pair.json", "r") as f:
                    pool_abi = json.load(f)
                with open("abi/baseswap_factory.json", "r") as f:
                    factory_abi = json.load(f)
            elif dex_name.lower() == "pancakeswap":
                with open("abi/pancakeswap_v3_pool.json", "r") as f:
                    pool_abi = json.load(f)
                with open("abi/pancakeswap_v3_factory.json", "r") as f:
                    factory_abi = json.load(f)
            else:
                logger.warning(f"Unsupported DEX: {dex_name}")
                return {"liquidity_usd": 0}
            
            # Get factory contract
            factory = self.w3.eth.contract(address=dex_config["factory"], abi=factory_abi)
            
            # Get pool address based on DEX type
            if dex_name.lower() == "baseswap":
                pool_address = await factory.functions.getPair(weth_address, token_address).call()
            else:  # PancakeSwap V3
                pool_address = await factory.functions.getPool(weth_address, token_address, dex_config["fee"]).call()
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                return {"liquidity_usd": 0}
            
            # Get pool info
            pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            # Get liquidity based on DEX type
            if dex_name.lower() == "baseswap":
                reserves = await pool.functions.getReserves().call()
                eth_price = self.market_conditions.get("WETH", None)
                if eth_price:
                    weth_value = Web3.from_wei(reserves[0], "ether") * eth_price.price
                    token_value = Web3.from_wei(reserves[1], "ether")
                    total_value = weth_value + token_value
                else:
                    total_value = 0
            else:  # PancakeSwap V3
                slot0 = await pool.functions.slot0().call()
                liquidity = await pool.functions.liquidity().call()
                eth_price = self.market_conditions.get("WETH", None)
                if eth_price and liquidity > 0:
                    # Simplified V3 liquidity calculation
                    total_value = Web3.from_wei(liquidity, "ether") * eth_price.price
                else:
                    total_value = 0
            
            return {
                "address": pool_address,
                "liquidity_usd": total_value
            }
            
        except Exception as e:
            logger.warning(f"Failed to get {dex_name} pool liquidity: {e}")
            return {"liquidity_usd": 0}

    def _calculate_trend(self, symbol: str) -> MarketTrend:
        """Calculate market trend for a token."""
        try:
            points = self.price_history.get(symbol, [])
            if len(points) < self.min_data_points:
                return MarketTrend(
                    direction="sideways",
                    strength=0.0,
                    duration=0.0,
                    volatility=0.0,
                    confidence=0.0
                )
                
            # Get recent points
            current_time = time.time()
            recent_points = [
                p for p in points
                if current_time - p.timestamp <= 3600  # Last hour
            ]
            
            if not recent_points:
                return MarketTrend(
                    direction="sideways",
                    strength=0.0,
                    duration=0.0,
                    volatility=0.0,
                    confidence=0.0
                )
                
            # Calculate trend
            prices = [float(p.price) for p in recent_points]
            times = [p.timestamp for p in recent_points]
            
            # Linear regression
            n = len(prices)
            sum_x = sum(times)
            sum_y = sum(prices)
            sum_xy = sum(x * y for x, y in zip(times, prices))
            sum_xx = sum(x * x for x in times)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
            
            # Calculate trend metrics
            price_change = (prices[-1] - prices[0]) / prices[0]
            duration = times[-1] - times[0]
            volatility = stdev(prices) / mean(prices) if len(prices) > 1 else 0
            
            # Determine direction and strength
            if abs(price_change) < self.trend_threshold:
                direction = "sideways"
                strength = abs(slope)
            else:
                direction = "up" if slope > 0 else "down"
                strength = abs(slope) / mean(prices)
                
            # Calculate confidence
            confidence = 1.0 - min(1.0, volatility * 2)  # Lower confidence with higher volatility
            
            return MarketTrend(
                direction=direction,
                strength=float(strength),
                duration=float(duration),
                volatility=float(volatility),
                confidence=float(confidence)
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate trend for {symbol}: {e}")
            return MarketTrend(
                direction="sideways",
                strength=0.0,
                duration=0.0,
                volatility=0.0,
                confidence=0.0
            )

    def _calculate_price_impact(self, symbol: str, liquidity: Decimal) -> float:
        """Calculate estimated price impact for standard trade size."""
        try:
            # Get token config
            token_config = self.config["tokens"].get(symbol)
            if not token_config:
                return 1.0
                
            # Get trade size from config
            trade_size_usd = Decimal(str(self.config.get("max_trade_size_usd", 1000)))
            
            # Calculate impact
            if liquidity > 0:
                impact = float(trade_size_usd / liquidity)
                return min(1.0, impact)  # Cap at 100%
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"Failed to calculate price impact for {symbol}: {e}")
            return 1.0

    def _clean_old_data(self):
        """Remove old price points."""
        try:
            cutoff = time.time() - self.history_length
            
            for symbol in self.price_history:
                self.price_history[symbol] = [
                    p for p in self.price_history[symbol]
                    if p.timestamp >= cutoff
                ]
                
        except Exception as e:
            logger.error(f"Failed to clean old data: {e}")

    def _update_metrics(self):
        """Update performance metrics."""
        try:
            # Calculate prediction accuracy
            # TODO: Implement prediction tracking
            pass
            
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    async def get_market_condition(self, symbol: str = None) -> Optional[Dict[str, Any]]:
        """
        Get current market condition for a token or overall market.
        
        Args:
            symbol: Optional token symbol. If None, returns overall market condition.
            
        Returns:
            Optional[Dict[str, Any]]: Market condition metrics
        """
        try:
            # Update market conditions if needed
            current_time = time.time()
            if current_time - self.last_update > self.update_interval:
                await self._update_market_conditions()
                
            if symbol:
                condition = self.market_conditions.get(symbol)
                if condition:
                    return {
                        'price': float(condition.price),
                        'volume': float(condition.volume_24h),
                        'liquidity': float(condition.liquidity),
                        'volatility': condition.volatility_24h,
                        'trend': condition.trend.direction,
                        'trend_strength': float(condition.trend.strength),
                        'confidence': float(condition.trend.confidence)
                    }
            else:
                # Get overall market condition using market-analysis server
                market_response = await self.web3_manager.use_mcp_tool(
                    "market-analysis",
                    "assess_market_conditions",
                    {
                        "token": "bitcoin",  # Use as market indicator
                        "metrics": ["volatility", "volume", "liquidity", "trend"]
                    }
                )
                return market_response['metrics']
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get market condition for {symbol}: {e}")
            return None

    def should_execute(
        self,
        symbol: str,
        trade_size_usd: Decimal,
        min_confidence: float = 0.8
    ) -> Tuple[bool, str]:
        """Determine if market conditions are suitable for trading."""
        try:
            condition = self.market_conditions.get(symbol)
            if not condition:
                return False, "No market data available"
                
            # Check data freshness
            if time.time() - condition.last_updated > self.update_interval * 2:
                return False, "Market data too old"
                
            # Check confidence
            if condition.trend.confidence < min_confidence:
                return False, f"Low trend confidence: {condition.trend.confidence:.1%}"
                
            # Check volatility
            if condition.volatility_24h > 0.5:  # 50% daily volatility
                return False, f"High volatility: {condition.volatility_24h:.1%}"
                
            # Check liquidity
            min_liquidity = trade_size_usd * Decimal("50")  # 50x trade size
            if condition.liquidity < min_liquidity:
                return False, f"Insufficient liquidity: ${condition.liquidity:,.0f}"
                
            # Check price impact
            max_impact = float(self.config.get("max_price_impact", 0.01))  # 1%
            if condition.price_impact > max_impact:
                return False, f"High price impact: {condition.price_impact:.1%}"
                
            return True, "Market conditions favorable"
            
        except Exception as e:
            logger.error(f"Failed to check execution conditions: {e}")
            return False, f"Error: {str(e)}"

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            "prediction_accuracy": self.prediction_accuracy,
            "tracked_tokens": len(self.market_conditions),
            "data_points": sum(len(h) for h in self.price_history.values()),
            "last_update": self.last_update
        }

    async def wait_for_data(self, timeout: int = 30) -> bool:
        """Wait for initial market data to be available.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if data is available, False if timeout occurred
        """
        start_time = time.time()
        dots = 0
        while not self.market_conditions and time.time() - start_time < timeout:
            dots = (dots + 1) % 4
            logger.info(f"Waiting for market data{'.' * dots}")
            await asyncio.sleep(1)
            
            # Try to force an update
            try:
                await self._update_market_conditions()
            except Exception as e:
                logger.warning(f"Error during market update: {e}")
                
        return bool(self.market_conditions)

    async def get_market_metrics(self) -> Dict[str, Any]:
        """Get current market metrics for all tracked tokens."""
        metrics = {}
        for symbol, condition in self.market_conditions.items():
            if condition:
                metrics[symbol] = {
                    'price': float(condition.price),
                    'volume_24h': float(condition.volume_24h),
                    'liquidity': float(condition.liquidity),
                    'volatility': condition.volatility_24h,
                    'trend': {
                        'direction': condition.trend.direction,
                        'strength': float(condition.trend.strength),
                        'confidence': float(condition.trend.confidence)
                    },
                    'last_updated': datetime.fromtimestamp(condition.last_updated).isoformat()
                }
        return metrics

async def create_market_analyzer(
    web3_manager: Web3Manager,
    config: Dict[str, Any]
) -> MarketAnalyzer:
    """Create and initialize market analyzer."""
    try:
        analyzer = MarketAnalyzer(web3_manager, config)
        
        # Force initial market update
        await analyzer._update_market_conditions()
        
        if not analyzer.market_conditions:
            logger.warning("Initial market update returned no data")
            
        # Start monitoring in background task
        monitoring_task = asyncio.create_task(analyzer.start_monitoring())
        
        # Wait for initial data with progress logging
        start_time = time.time()
        dots = 0
        while not analyzer.market_conditions and time.time() - start_time < 30:  # 30s timeout
            dots = (dots + 1) % 4
            logger.info(f"Waiting for market data{'.' * dots}")
            await asyncio.sleep(1)
            
            # Try to force an update
            try:
                await analyzer._update_market_conditions()
            except Exception as e:
                logger.warning(f"Error during market update: {e}")
        
        if not analyzer.market_conditions:
            logger.warning("Market analyzer initialized but no data available yet")
        else:
            logger.info("Market analyzer initialized with data")
            logger.info(f"Initial market conditions: {analyzer.market_conditions}")
            
        return analyzer
    except Exception as e:
        logger.error(f"Failed to create market analyzer: {e}")
        raise
