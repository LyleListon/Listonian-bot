"""Market analysis and trend detection."""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean, median, stdev
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
        self.w3 = web3_manager
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
            try:
                token_ids = {
                    "WETH": "ethereum",
                    "USDC": "usd-coin"
                }
                
                from ...utils.mcp_client import use_mcp_tool
                response = await use_mcp_tool(
                    "crypto-price",
                    "get_prices",
                    {
                        "coins": list(token_ids.values()),
                        "include_24h_change": True
                    }
                )
                
                # Process each token
                for symbol, token_id in token_ids.items():
                    if token_id in response:
                        price = Decimal(str(response[token_id]["usd"]))
                        volume = Decimal(str(response[token_id].get("volume_24h", 0)))
                        
                        # Get market analysis
                        market_response = await use_mcp_tool(
                            "market-analysis",
                            "assess_market_conditions",
                            {
                                "token": token_id,
                                "metrics": ["volatility", "volume", "trend"]
                            }
                        )
                        
                        # Get pool liquidity
                        if symbol in tokens:
                            token_config = tokens[symbol]
                            pool_info = await self._get_pool_liquidity(token_config["address"])
                            liquidity = Decimal(str(pool_info["liquidity_usd"]))
                        else:
                            liquidity = Decimal("0")
                        
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
                logger.error(f"Failed to get prices from MCP: {e}")
                
            self.last_update = current_time
            
        except Exception as e:
            logger.error(f"Failed to update market conditions: {e}")

    async def _get_pool_liquidity(self, token_address: str) -> Dict[str, Any]:
        """Get pool liquidity information."""
        try:
            # Get WETH address
            weth_address = self.config["tokens"]["WETH"]["address"]
            
            # Create pool contract
            pool_abi = []  # Load pool ABI
            with open("abi/aerodrome_pool.json", "r") as f:
                pool_abi = json.load(f)
                
            # Get pool address from factory
            factory_address = self.config["dexes"]["aerodrome"]["factory"]
            factory_abi = []  # Load factory ABI
            with open("abi/aerodrome_factory.json", "r") as f:
                factory_abi = json.load(f)
                
            factory = self.w3.get_contract(factory_address, factory_abi)
            
            # Try both stable and volatile pools
            pool_address = await factory.functions.getPool(
                weth_address,
                token_address,
                True
            ).call()
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                pool_address = await factory.functions.getPool(
                    weth_address,
                    token_address,
                    False
                ).call()
                
            if pool_address == "0x0000000000000000000000000000000000000000":
                return {"liquidity_usd": 0}
                
            # Get pool info
            pool = self.w3.get_contract(pool_address, pool_abi)
            reserves = await pool.functions.getReserves().call()
            
            # Calculate USD value
            eth_price = self.market_conditions.get("WETH", None)
            if eth_price:
                weth_value = Web3.from_wei(reserves[0], "ether") * eth_price.price
                token_value = Web3.from_wei(reserves[1], "ether")  # Assuming 18 decimals
                total_value = weth_value + token_value
            else:
                total_value = 0
                
            return {
                "address": pool_address,
                "reserve0": reserves[0],
                "reserve1": reserves[1],
                "liquidity_usd": total_value
            }
            
        except Exception as e:
            logger.error(f"Failed to get pool liquidity: {e}")
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

    def get_market_condition(self, symbol: str) -> Optional[MarketCondition]:
        """Get current market condition for a token."""
        return self.market_conditions.get(symbol)

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

async def create_market_analyzer(
    web3_manager: Web3Manager,
    config: Dict[str, Any]
) -> MarketAnalyzer:
    """Create and initialize market analyzer."""
    try:
        analyzer = MarketAnalyzer(web3_manager, config)
        asyncio.create_task(analyzer.start_monitoring())
        return analyzer
    except Exception as e:
        logger.error(f"Failed to create market analyzer: {e}")
        raise
