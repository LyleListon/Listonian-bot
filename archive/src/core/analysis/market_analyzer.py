"""Market analysis utilities."""

import logging
import math
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from ..web3.web3_manager import Web3Manager
from ..models.market_models import MarketTrend, MarketCondition, PricePoint
from ..models.opportunity import Opportunity
from ...utils.config_loader import load_config

logger = logging.getLogger(__name__)

async def create_market_analyzer(
    web3_manager: Optional[Web3Manager] = None,
    config: Optional[Dict[str, Any]] = None
) -> 'MarketAnalyzer':
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
            config = load_config()
            
        analyzer = MarketAnalyzer(web3_manager=web3_manager, config=config)
        await analyzer.start_monitoring()
        logger.info("Market analyzer created and initialized")
        return analyzer
        
    except Exception as e:
        logger.error(f"Failed to create market analyzer: {e}")
        raise

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
        self._monitoring = False
        self._monitoring_task = None
        logger.info("Market analyzer initialized")

    async def get_opportunities(self) -> List[Opportunity]:
        """Get current arbitrage opportunities."""
        opportunities = []
        try:
            # Get all enabled DEXes
            dexes = [{"name": name, **dex} for name, dex in self.config['dexes'].items() if dex.get('enabled', True)]
            
            # For each token pair
            for token1 in self.TOKEN_MAPPING.values():
                for token2 in self.TOKEN_MAPPING.values():
                    if token1 != token2:
                        # Get prices from each DEX
                        prices = {}
                        for dex in dexes:
                            try:
                                price = await self._get_price(token1, token2, dex['name'])
                                if price:
                                    prices[dex['name']] = price
                                    logger.info(f"{token1}/{token2} price on {dex['name']}: {price:.8f}")
                            except Exception as e:
                                logger.debug(f"Failed to get price for {token1}/{token2} on {dex['name']}: {e}")
                                continue
                        
                        # Find arbitrage opportunities
                        if len(prices) >= 2:
                            min_price = min(prices.values())
                            max_price = max(prices.values())
                            
                            if max_price > min_price:
                                # Calculate profit percentage
                                profit_pct = (max_price - min_price) / min_price * 100
                                logger.info(f"Potential profit for {token1}/{token2}: {profit_pct:.2f}%")
                                
                                # Only include if profit meets minimum threshold
                                min_profit = float(self.config.get('min_profit_threshold', 0.5))
                                if profit_pct >= min_profit:
                                    buy_dex = [name for name, price in prices.items() if price == min_price][0]
                                    sell_dex = [name for name, price in prices.items() if price == max_price][0]
                                    
                                    opportunity = Opportunity(
                                        token_in=token1,
                                        token_out=token2,
                                        buy_dex=buy_dex,
                                        sell_dex=sell_dex,
                                        profit_percentage=profit_pct,
                                        timestamp=datetime.now().timestamp()
                                    )
                                    logger.info(f"Found opportunity: Buy {token1} on {buy_dex}, Sell on {sell_dex}, Profit: {profit_pct:.2f}%")
                                    opportunities.append(opportunity)
                        
        except Exception as e:
            logger.error(f"Error finding opportunities: {e}")
            
        return opportunities

    async def start_monitoring(self):
        """Start market monitoring loop."""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Market monitoring started")

    async def stop_monitoring(self):
        """Stop market monitoring loop."""
        if not self._monitoring:
            return

        self._monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Market monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        try:
            while self._monitoring:
                try:
                    # Update market conditions
                    for token_id, symbol in self.TOKEN_MAPPING.items():
                        try:
                            market_data = await self.analyze_market_conditions(symbol)
                            if market_data:
                                trend = MarketTrend(
                                    direction=market_data.get("trend", "sideways"),
                                    strength=float(market_data.get("trend_strength", 0.0)),
                                    duration=float(market_data.get("trend_duration", 0.0)),
                                    volatility=float(market_data.get("volatility", 0.0)),
                                    confidence=float(market_data.get("confidence", 0.0))
                                )
                                
                                condition = MarketCondition(
                                    price=Decimal(str(market_data.get("price", 0))),
                                    trend=trend,
                                    volume_24h=Decimal(str(market_data.get("volume_24h", 0))),
                                    liquidity=Decimal(str(market_data.get("liquidity", 0))),
                                    volatility_24h=float(market_data.get("volatility_24h", 0)),
                                    price_impact=float(market_data.get("price_impact", 0)),
                                    last_updated=float(datetime.now().timestamp())
                                )
                                
                                self.market_conditions[symbol] = condition
                                logger.debug(f"Updated market condition for {symbol}")
                                
                        except Exception as e:
                            logger.error(f"Error updating market condition for {symbol}: {e}")
                            continue

                    await asyncio.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(5)  # Short delay on error
                    
        except asyncio.CancelledError:
            logger.info("Market monitoring cancelled")
            raise
        except Exception as e:
            logger.error(f"Market monitoring failed: {e}")
            raise
        finally:
            self._monitoring = False
            logger.info("Market monitoring stopped")

    async def analyze_market_conditions(self, token: str) -> Dict[str, Any]:
        """Analyze market conditions for token."""
        try:            
            symbol = self.TOKEN_MAPPING.get(token, token)

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

    async def _get_price(self, token1: str, token2: str, dex_name: str) -> Optional[float]:
        """Get price of token2 in terms of token1 from specified DEX."""
        try:
            # Get token addresses
            token1_addr = self.config['tokens'][token1]['address']
            token2_addr = self.config['tokens'][token2]['address']
            
            # Get DEX instance
            dex_config = self.config['dexes'][dex_name.lower()]
            dex_class = self._get_dex_class(dex_name)
            if not dex_class:
                return None
                
            dex = dex_class(self.web3_manager, dex_config)
            await dex.initialize()
            
            # Get reserves
            reserves = await dex.get_reserves(token1_addr, token2_addr)
            if not reserves:
                return None
                
            # Calculate price
            return float(reserves['reserve1']) / float(reserves['reserve0'])
            
        except Exception as e:
            if "pair not found" not in str(e).lower():  # Don't log common "pair not found" errors
                logger.debug(f"Failed to get price from {dex_name}: {e}")
            return None

    def _get_dex_class(self, dex_name: str):
        """Get DEX class based on name."""
        try:
            if dex_name.lower() == 'baseswap':
                from ..dex.baseswap import BaseSwapDEX
                return BaseSwapDEX
            elif dex_name.lower() == 'swapbased':
                from ..dex.swapbased import SwapBasedDEX
                return SwapBasedDEX
            elif dex_name.lower() == 'pancakeswap':
                from ..dex.pancakeswap import PancakeSwapDEX
                return PancakeSwapDEX
            return None
        except Exception as e:
            logger.error(f"Failed to get DEX class for {dex_name}: {e}")
            return None

    # ... rest of the methods remain unchanged ...
    async def get_performance_metrics(self) -> List[Dict[str, Any]]:
        """Get performance metrics for dashboard."""
        try:
            # Get opportunities
            opportunities = await self.get_opportunities()
            
            # Initialize BaseSwap
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            # Get trade history
            weth_address = self.config['tokens']['WETH']['address']
            trades = await baseswap.get_trades(weth_address)
            
            # Calculate trade metrics
            now = datetime.now().timestamp()
            trades_24h = len([t for t in trades if now - t['timestamp'] <= 86400])
            total_trades = len(trades)
            
            # Calculate success rate (trades with profit)
            successful_trades = len([t for t in trades if t.get('profit', 0) > 0])
            success_rate = successful_trades / total_trades if total_trades > 0 else 0.0
            
            total_profit_usd = sum(t.get('profit', 0) for t in trades)
            portfolio_change_24h = sum(t.get('profit', 0) for t in trades if now - t['timestamp'] <= 86400)
            
            # Get DEX metrics
            dex_metrics = {}
            for dex_name in self.config['dexes']:
                if self.config['dexes'][dex_name].get('enabled', True):
                    dex_metrics[dex_name] = {
                        'active': True,
                        'liquidity': float(await self._get_liquidity(dex_name)),
                        'volume_24h': float(await self._get_24h_volume(dex_name))
                    }
            
            # Return metrics in expected format
            return [{
                'timestamp': datetime.now().timestamp(),
                'total_trades': total_trades,
                'trades_24h': trades_24h,
                'success_rate': success_rate,
                'total_profit_usd': total_profit_usd,
                'portfolio_change_24h': portfolio_change_24h,
                'active_opportunities': len(opportunities),
                'dex_metrics': dex_metrics,
                'market_conditions': {k: v.__dict__ for k, v in self.market_conditions.items()}
            }]
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            # Return default metrics
            return [{
                'timestamp': datetime.now().timestamp(),
                'total_trades': 0,
                'trades_24h': 0,
                'success_rate': 0.0,
                'total_profit_usd': 0.0,
                'portfolio_change_24h': 0.0,
                'active_opportunities': 0,
                'dex_metrics': {}
            }]

    async def _get_24h_volume(self, token: str) -> Decimal:
        """Get 24h trading volume for token."""
        try:
            # Get volume from BaseSwap
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'].get(token, {}).get('address')
            if not token_address:
                return Decimal('0')
                
            volume = await baseswap.get_24h_volume(weth_address, token_address)
            return Decimal(str(volume)) if volume else Decimal('0')
            
        except Exception as e:
            logger.error(f"Failed to get 24h volume: {e}")
            return Decimal('0')

    async def _get_liquidity(self, token: str) -> Decimal:
        """Get current liquidity for token."""
        try:
            # Get liquidity from BaseSwap
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'].get(token, {}).get('address')
            if not token_address:
                return Decimal('0')
                
            reserves = await baseswap.get_reserves(weth_address, token_address)
            return Decimal(str(reserves['reserve0'])) if reserves else Decimal('0')
            
        except Exception as e:
            logger.error(f"Failed to get liquidity: {e}")
            return Decimal('0')

    async def _get_volatility(self, token: str) -> float:
        """Get current volatility for token."""
        try:
            # Calculate volatility from price history
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'].get(token, {}).get('address')
            if not token_address:
                return 0.0
                
            # Get last 10 prices
            prices = []
            for _ in range(10):
                reserves = await baseswap.get_reserves(weth_address, token_address)
                if reserves:
                    prices.append(float(reserves['reserve1']) / float(reserves['reserve0']))
                await asyncio.sleep(1)
                
            # Calculate standard deviation
            return math.sqrt(sum((x - sum(prices)/len(prices))**2 for x in prices)/len(prices)) if prices else 0.0
        except Exception as e:
            logger.error(f"Failed to get volatility: {e}")
            return 0.0

    async def _get_market_trend(self, token: str) -> str:
        """Get current market trend for token."""
        try:
            # Calculate trend from price history
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'].get(token, {}).get('address')
            if not token_address:
                return "sideways"
                
            # Get last 2 prices
            prices = []
            for _ in range(2):
                reserves = await baseswap.get_reserves(weth_address, token_address)
                if reserves:
                    prices.append(float(reserves['reserve1']) / float(reserves['reserve0']))
                await asyncio.sleep(1)
                
            # Determine trend
            return "up" if len(prices) == 2 and prices[1] > prices[0] else "down" if len(prices) == 2 and prices[1] < prices[0] else "sideways"
        except Exception as e:
            logger.error(f"Failed to get market trend: {e}")
            return "sideways"

    async def _get_trend_strength(self, token: str) -> float:
        """Get current trend strength for token."""
        try:
            # Calculate trend strength from price history
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'].get(token, {}).get('address')
            if not token_address:
                return 0.0
                
            # Get last 5 prices
            prices = []
            for _ in range(5):
                reserves = await baseswap.get_reserves(weth_address, token_address)
                if reserves:
                    prices.append(float(reserves['reserve1']) / float(reserves['reserve0']))
                await asyncio.sleep(1)
                
            # Calculate trend strength as normalized price change
            return abs((prices[-1] - prices[0]) / prices[0]) if len(prices) > 1 else 0.0
        except Exception as e:
            logger.error(f"Failed to get trend strength: {e}")
            return 0.0

    async def _get_24h_volatility(self, token: str) -> float:
        """Get 24h volatility for token."""
        try:
            # Calculate 24h volatility from price history
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'].get(token, {}).get('address')
            if not token_address:
                return 0.0
                
            # Get last 24 hourly prices
            prices = []
            for _ in range(24):
                reserves = await baseswap.get_reserves(weth_address, token_address)
                if reserves:
                    prices.append(float(reserves['reserve1']) / float(reserves['reserve0']))
                await asyncio.sleep(1)
                
            # Calculate standard deviation
            return math.sqrt(sum((x - sum(prices)/len(prices))**2 for x in prices)/len(prices)) if prices else 0.0
        except Exception as e:
            logger.error(f"Failed to get 24h volatility: {e}")
            return 0.0

    async def _get_price_impact(self, token: str) -> float:
        """Get estimated price impact for token."""
        try:
            # Calculate price impact from liquidity
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'].get(token, {}).get('address')
            if not token_address:
                return 0.0
                
            # Get reserves
            reserves = await baseswap.get_reserves(weth_address, token_address)
            if not reserves:
                return 0.0
                
            # Calculate price impact based on liquidity
            liquidity = float(reserves['reserve0'])
            trade_size = 1000  # Assume $1000 trade
            return trade_size / liquidity if liquidity > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Failed to get price impact: {e}")
            return 0.0

    async def _calculate_confidence(self, token: str) -> float:
        """Calculate confidence score for market data."""
        try:
            # Calculate confidence based on liquidity and volume
            from ..dex.baseswap import BaseSwapDEX
            baseswap = BaseSwapDEX(self.web3_manager, self.config['dexes']['baseswap'])
            await baseswap.initialize()
            
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'].get(token, {}).get('address')
            if not token_address:
                return 0.0
                
            # Get metrics
            volume = await self._get_24h_volume(token)
            liquidity = await self._get_liquidity(token)
            volatility = await self._get_volatility(token)
            
            # Calculate confidence score
            volume_score = min(float(volume) / 1000000, 1.0)  # Scale by $1M
            liquidity_score = min(float(liquidity) / 500000, 1.0)  # Scale by $500K
            volatility_score = max(1.0 - float(volatility), 0.0)  # Lower volatility = higher confidence
            return (volume_score + liquidity_score + volatility_score) / 3
        except Exception as e:
            logger.error(f"Failed to calculate confidence: {e}")
            return 0.0
