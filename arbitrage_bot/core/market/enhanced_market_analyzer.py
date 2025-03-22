"""
Enhanced Market Analyzer Module

This module provides advanced market analysis functionality with:
- Parallel price fetching
- Multi-source price validation
- Liquidity depth analysis
- Slippage impact calculations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, NamedTuple
from decimal import Decimal
from eth_typing import ChecksumAddress
from web3 import Web3

from ...utils.async_manager import AsyncLock
from ..interfaces import PriceData, TokenPair, LiquidityData
from ..ml.model_interface import MLSystem
from ..memory.memory_bank import MemoryBank
from .price_validator import PriceValidator

logger = logging.getLogger(__name__)

class MarketDepth(NamedTuple):
    """Market depth information for a token pair."""
    liquidity: Decimal
    volume_24h: Decimal
    price_impact_1k: Decimal
    price_impact_10k: Decimal
    price_impact_100k: Decimal

class OpportunityScore(NamedTuple):
    """Comprehensive opportunity scoring."""
    profit_potential: Decimal
    execution_risk: Decimal
    market_impact: Decimal
    confidence: Decimal
    gas_cost_estimate: int

class EnhancedMarketAnalyzer:
    """Enhanced market analysis with parallel processing and validation."""

    def __init__(
        self,
        web3: Web3,
        ml_system: MLSystem,
        memory_bank: MemoryBank,
        price_validator: PriceValidator,
        min_profit_threshold: Decimal = Decimal('0.01'),  # 1% minimum profit
        max_price_impact: Decimal = Decimal('0.02'),      # 2% maximum price impact
        confidence_threshold: Decimal = Decimal('0.8')    # 80% confidence required
    ):
        """Initialize the enhanced market analyzer."""
        self.web3 = web3
        self.ml_system = ml_system
        self.memory_bank = memory_bank
        self.price_validator = price_validator
        
        # Configuration
        self.min_profit_threshold = min_profit_threshold
        self.max_price_impact = max_price_impact
        self.confidence_threshold = confidence_threshold
        
        # Thread safety
        self._price_lock = AsyncLock()
        self._depth_lock = AsyncLock()
        
        # Cache settings
        self._price_cache: Dict[str, Tuple[PriceData, int]] = {}  # (price_data, timestamp)
        self._depth_cache: Dict[str, Tuple[MarketDepth, int]] = {}  # (depth_data, timestamp)
        self._cache_ttl = 30  # 30 seconds TTL

    async def fetch_dex_prices(self, token_pair: TokenPair) -> Dict[str, PriceData]:
        """
        Fetch prices from multiple DEXs in parallel.
        
        Args:
            token_pair: Token pair to fetch prices for
            
        Returns:
            Dictionary of DEX names to price data
        """
        async with self._price_lock:
            # Get all configured DEXs
            dex_list = await self.memory_bank.get_active_dexes()
            
            # Create tasks for parallel execution
            tasks = []
            for dex in dex_list:
                tasks.append(asyncio.create_task(
                    dex.get_price(token_pair.token0, token_pair.token1)
                ))
            
            # Wait for all price fetches to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            prices = {}
            for dex, result in zip(dex_list, results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch price from {dex.name}: {result}")
                    continue
                prices[dex.name] = result
            
            return prices

    async def analyze_market_depth(
        self,
        token_pair: TokenPair,
        dex_name: str
    ) -> MarketDepth:
        """
        Analyze market depth for a token pair on a specific DEX.
        
        Args:
            token_pair: Token pair to analyze
            dex_name: DEX to analyze
            
        Returns:
            Market depth information
        """
        async with self._depth_lock:
            # Check cache
            cache_key = f"{dex_name}:{token_pair.token0}:{token_pair.token1}"
            cached = self._depth_cache.get(cache_key)
            if cached and (self.web3.eth.get_block('latest')['timestamp'] - cached[1]) < self._cache_ttl:
                return cached[0]
            
            # Get DEX interface
            dex = await self.memory_bank.get_dex(dex_name)
            
            # Fetch liquidity data
            liquidity = await dex.get_liquidity(token_pair)
            
            # Calculate price impacts
            impact_1k = await dex.calculate_price_impact(token_pair, Web3.to_wei(1000, 'ether'))
            impact_10k = await dex.calculate_price_impact(token_pair, Web3.to_wei(10000, 'ether'))
            impact_100k = await dex.calculate_price_impact(token_pair, Web3.to_wei(100000, 'ether'))
            
            # Get 24h volume
            volume = await dex.get_24h_volume(token_pair)
            
            depth = MarketDepth(
                liquidity=Decimal(str(liquidity)),
                volume_24h=Decimal(str(volume)),
                price_impact_1k=Decimal(str(impact_1k)),
                price_impact_10k=Decimal(str(impact_10k)),
                price_impact_100k=Decimal(str(impact_100k))
            )
            
            # Update cache
            self._depth_cache[cache_key] = (depth, self.web3.eth.get_block('latest')['timestamp'])
            
            return depth

    async def score_opportunity(
        self,
        token_pair: TokenPair,
        prices: Dict[str, PriceData],
        market_depths: Dict[str, MarketDepth]
    ) -> OpportunityScore:
        """
        Score an arbitrage opportunity using ML system and market data.
        
        Args:
            token_pair: Token pair to analyze
            prices: Price data from different DEXs
            market_depths: Market depth data from different DEXs
            
        Returns:
            Opportunity score with multiple metrics
        """
        # Get historical data
        historical_data = await self.memory_bank.get_token_metrics(token_pair)
        
        # Prepare features for ML model
        features = {
            'price_differences': [abs(p1.price - p2.price) for p1 in prices.values() for p2 in prices.values() if p1 != p2],
            'liquidity_levels': [depth.liquidity for depth in market_depths.values()],
            'volume_24h': [depth.volume_24h for depth in market_depths.values()],
            'price_impacts': [depth.price_impact_10k for depth in market_depths.values()],
            'historical_success_rate': historical_data.get('success_rate', 0),
            'historical_profit_avg': historical_data.get('average_profit', 0),
            'historical_gas_costs': historical_data.get('average_gas_cost', 0)
        }
        
        # Get ML predictions
        predictions = await self.ml_system.predict_opportunity(features)
        
        return OpportunityScore(
            profit_potential=Decimal(str(predictions['profit_potential'])),
            execution_risk=Decimal(str(predictions['execution_risk'])),
            market_impact=Decimal(str(predictions['market_impact'])),
            confidence=Decimal(str(predictions['confidence'])),
            gas_cost_estimate=int(predictions['estimated_gas_cost'])
        )

    async def find_best_opportunity(
        self,
        token_pairs: List[TokenPair]
    ) -> Tuple[TokenPair, Dict[str, PriceData], OpportunityScore]:
        """
        Find the best arbitrage opportunity among token pairs.
        
        Args:
            token_pairs: List of token pairs to analyze
            
        Returns:
            Tuple of (best token pair, price data, opportunity score)
        """
        best_score = None
        best_pair = None
        best_prices = None
        
        for pair in token_pairs:
            # Fetch prices in parallel
            prices = await self.fetch_dex_prices(pair)
            
            # Validate prices
            if not await self.price_validator.validate_prices(pair, prices):
                logger.warning(f"Price validation failed for {pair}")
                continue
            
            # Analyze market depth
            depths = {}
            for dex_name in prices.keys():
                depths[dex_name] = await self.analyze_market_depth(pair, dex_name)
            
            # Score opportunity
            score = await self.score_opportunity(pair, prices, depths)
            
            # Check if this is the best opportunity so far
            if (
                score.confidence >= self.confidence_threshold and
                score.profit_potential >= self.min_profit_threshold and
                score.market_impact <= self.max_price_impact and
                (not best_score or score.profit_potential > best_score.profit_potential)
            ):
                best_score = score
                best_pair = pair
                best_prices = prices
        
        if not best_pair:
            raise ValueError("No viable arbitrage opportunities found")
        
        return best_pair, best_prices, best_score

    async def monitor_market_conditions(self):
        """Continuously monitor market conditions and update strategies."""
        while True:
            try:
                # Update market metrics
                await self.memory_bank.update_market_metrics()
                
                # Adjust thresholds based on market conditions
                await self._adjust_thresholds()
                
                # Sleep for monitoring interval
                await asyncio.sleep(60)  # 1 minute interval
                
            except Exception as e:
                logger.error(f"Error in market monitoring: {e}")
                await asyncio.sleep(5)  # Short sleep on error

    async def _adjust_thresholds(self):
        """Adjust thresholds based on market conditions."""
        market_metrics = await self.memory_bank.get_market_metrics()
        
        # Adjust profit threshold based on gas prices
        if market_metrics.get('network_congestion', 0) > 0.8:  # High congestion
            self.min_profit_threshold = Decimal('0.015')  # Increase to 1.5%
        else:
            self.min_profit_threshold = Decimal('0.01')   # Normal 1%
            
        # Adjust price impact threshold based on volatility
        if market_metrics.get('market_volatility', 0) > 0.5:  # High volatility
            self.max_price_impact = Decimal('0.015')     # More conservative
        else:
            self.max_price_impact = Decimal('0.02')      # Normal threshold