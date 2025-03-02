"""
Cross-DEX Arbitrage Detector

This module contains the implementation of the CrossDexDetector,
which identifies arbitrage opportunities across different decentralized exchanges.
"""

import asyncio
import logging
import time
import uuid
from decimal import Decimal
from typing import Dict, List, Any, Optional, Set, Tuple, cast

from ....dex.interfaces import DEX, PriceSource
from ...interfaces import (
    OpportunityDetector,
    MarketDataProvider
)
from ...models import (
    ArbitrageOpportunity,
    ArbitrageRoute,
    ArbitrageStep,
    TokenPair,
    TokenAmount,
    DEXPair,
    MarketCondition,
    StrategyType,
    OpportunityStatus
)

logger = logging.getLogger(__name__)


class CrossDexDetector(OpportunityDetector):
    """
    Detector for cross-DEX arbitrage opportunities.
    
    This detector identifies price discrepancies for the same token pair
    across different DEXs and calculates potential arbitrage profits.
    """
    
    def __init__(
        self,
        dexes: List[DEX],
        config: Dict[str, Any] = None
    ):
        """
        Initialize the cross-DEX detector.
        
        Args:
            dexes: List of DEXs to monitor
            config: Configuration dictionary
        """
        self.dexes = dexes
        self.config = config or {}
        
        # Configuration
        self.min_profit_percentage = Decimal(self.config.get("min_profit_percentage", "0.05"))  # 0.05%
        self.max_slippage = Decimal(self.config.get("max_slippage", "0.5"))  # 0.5%
        self.min_liquidity_usd = Decimal(self.config.get("min_liquidity_usd", "10000"))  # $10,000
        self.gas_cost_buffer_percentage = Decimal(self.config.get("gas_cost_buffer_percentage", "50"))  # 50%
        self.batch_size = int(self.config.get("batch_size", 50))
        self.max_pairs_per_dex = int(self.config.get("max_pairs_per_dex", 200))
        self.confidence_threshold = Decimal(self.config.get("confidence_threshold", "0.7"))  # 70% confidence
        
        # Cache for token pairs with timestamps
        self._token_pair_cache: Dict[str, Tuple[List[TokenPair], float]] = {}
        self._price_cache: Dict[str, Tuple[Decimal, float]] = {}
        self._cache_ttl = float(self.config.get("cache_ttl_seconds", 5.0))
        
        # Locks
        self._cache_lock = asyncio.Lock()
        
        logger.info(f"CrossDexDetector initialized with {len(dexes)} DEXs")
    
    async def detect_opportunities(
        self,
        market_condition: MarketCondition,
        max_results: int = 10,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """
        Detect cross-DEX arbitrage opportunities.
        
        Args:
            market_condition: Current market condition
            max_results: Maximum number of opportunities to return
            **kwargs: Additional parameters
            
        Returns:
            List of arbitrage opportunities
        """
        logger.info("Detecting cross-DEX arbitrage opportunities")
        
        # Extract parameters from kwargs or use defaults
        token_filter = kwargs.get("token_filter")
        dex_filter = kwargs.get("dex_filter")
        min_profit_wei = int(kwargs.get("min_profit_wei", self.config.get("min_profit_wei", 0)))
        
        # Get all token pairs from DEXs
        token_pairs_by_dex = await self._get_token_pairs_by_dex(
            token_filter=token_filter,
            dex_filter=dex_filter
        )
        
        # Group token pairs by address pair
        grouped_pairs = self._group_token_pairs(token_pairs_by_dex)
        
        # Find arbitrage opportunities
        raw_opportunities = await self._find_arbitrage_opportunities(
            grouped_pairs=grouped_pairs,
            market_condition=market_condition,
            min_profit_wei=min_profit_wei
        )
        
        # Sort opportunities by expected profit and limit to max_results
        sorted_opportunities = sorted(
            raw_opportunities,
            key=lambda o: o.expected_profit,
            reverse=True
        )
        
        return sorted_opportunities[:max_results]
    
    async def _get_token_pairs_by_dex(
        self,
        token_filter: Optional[Set[str]] = None,
        dex_filter: Optional[Set[str]] = None
    ) -> Dict[DEX, List[TokenPair]]:
        """
        Get token pairs from each DEX with caching.
        
        Args:
            token_filter: Optional set of token addresses to filter by
            dex_filter: Optional set of DEX IDs to filter by
            
        Returns:
            Dictionary mapping DEXs to their token pairs
        """
        result: Dict[DEX, List[TokenPair]] = {}
        
        # Filter DEXs if dex_filter is provided
        dexes_to_use = []
        if dex_filter:
            dexes_to_use = [dex for dex in self.dexes if dex.id in dex_filter]
        else:
            dexes_to_use = self.dexes
        
        # Get token pairs from each DEX with caching
        tasks = []
        for dex in dexes_to_use:
            task = asyncio.create_task(self._get_token_pairs_from_dex(
                dex=dex,
                token_filter=token_filter
            ))
            tasks.append((dex, task))
        
        # Wait for all tasks to complete
        for dex, task in tasks:
            try:
                token_pairs = await task
                if token_pairs:
                    result[dex] = token_pairs
            except Exception as e:
                logger.error(f"Error getting token pairs from {dex.id}: {e}")
        
        return result
    
    async def _get_token_pairs_from_dex(
        self,
        dex: DEX,
        token_filter: Optional[Set[str]] = None
    ) -> List[TokenPair]:
        """
        Get token pairs from a single DEX with caching.
        
        Args:
            dex: DEX to get token pairs from
            token_filter: Optional set of token addresses to filter by
            
        Returns:
            List of token pairs from the DEX
        """
        cache_key = f"{dex.id}_{hash(frozenset(token_filter)) if token_filter else 'all'}"
        
        # Check cache
        async with self._cache_lock:
            cached = self._token_pair_cache.get(cache_key)
            current_time = time.time()
            
            if cached and (current_time - cached[1] < self._cache_ttl):
                return cached[0]
        
        # Get token pairs from DEX
        try:
            # Ensure DEX is price source
            if not isinstance(dex, PriceSource):
                logger.warning(f"DEX {dex.id} is not a PriceSource, skipping")
                return []
            
            # Get all pairs from DEX
            price_source = cast(PriceSource, dex)
            token_pairs = await price_source.get_token_pairs(
                max_pairs=self.max_pairs_per_dex
            )
            
            # Filter by tokens if specified
            if token_filter:
                token_pairs = [
                    pair for pair in token_pairs
                    if pair.token0_address in token_filter or pair.token1_address in token_filter
                ]
            
            # Update cache
            async with self._cache_lock:
                self._token_pair_cache[cache_key] = (token_pairs, time.time())
            
            return token_pairs
            
        except Exception as e:
            logger.error(f"Error getting token pairs from {dex.id}: {e}")
            return []
    
    def _group_token_pairs(
        self,
        token_pairs_by_dex: Dict[DEX, List[TokenPair]]
    ) -> Dict[str, Dict[DEX, TokenPair]]:
        """
        Group token pairs by token address pair.
        
        Args:
            token_pairs_by_dex: Dictionary mapping DEXs to their token pairs
            
        Returns:
            Dictionary mapping token address pairs to DEXs and token pairs
        """
        grouped_pairs: Dict[str, Dict[DEX, TokenPair]] = {}
        
        for dex, token_pairs in token_pairs_by_dex.items():
            for token_pair in token_pairs:
                # Create a unique key for the token pair
                # Ensure token0 is always the "smaller" address to make consistent keys
                if token_pair.token0_address.lower() < token_pair.token1_address.lower():
                    key = f"{token_pair.token0_address.lower()}_{token_pair.token1_address.lower()}"
                else:
                    key = f"{token_pair.token1_address.lower()}_{token_pair.token0_address.lower()}"
                
                # Add to grouped pairs
                if key not in grouped_pairs:
                    grouped_pairs[key] = {}
                
                grouped_pairs[key][dex] = token_pair
        
        return grouped_pairs
    
    async def _find_arbitrage_opportunities(
        self,
        grouped_pairs: Dict[str, Dict[DEX, TokenPair]],
        market_condition: MarketCondition,
        min_profit_wei: int
    ) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities from grouped token pairs.
        
        Args:
            grouped_pairs: Dictionary mapping token address pairs to DEXs and token pairs
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei
            
        Returns:
            List of arbitrage opportunities
        """
        opportunities: List[ArbitrageOpportunity] = []
        
        # Process token pairs in batches
        keys = list(grouped_pairs.keys())
        batches = [keys[i:i+self.batch_size] for i in range(0, len(keys), self.batch_size)]
        
        # Iterate through batches
        for batch in batches:
            batch_tasks = []
            for key in batch:
                dex_token_pairs = grouped_pairs[key]
                # Only process pairs available on at least 2 DEXs
                if len(dex_token_pairs) < 2:
                    continue
                
                task = asyncio.create_task(self._process_token_pair_group(
                    key=key,
                    dex_token_pairs=dex_token_pairs,
                    market_condition=market_condition,
                    min_profit_wei=min_profit_wei
                ))
                batch_tasks.append(task)
            
            # Wait for batch to complete
            if batch_tasks:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Error processing token pair group: {result}")
                    elif result:
                        opportunities.extend(result)
        
        return opportunities
    
    async def _process_token_pair_group(
        self,
        key: str,
        dex_token_pairs: Dict[DEX, TokenPair],
        market_condition: MarketCondition,
        min_profit_wei: int
    ) -> List[ArbitrageOpportunity]:
        """
        Process a group of token pairs on different DEXs to find arbitrage opportunities.
        
        Args:
            key: Token pair key
            dex_token_pairs: Dictionary mapping DEXs to token pairs
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei
            
        Returns:
            List of arbitrage opportunities
        """
        # Get prices from all DEXs for this token pair
        dex_prices: Dict[DEX, Tuple[Decimal, Decimal]] = {}
        dex_list = list(dex_token_pairs.keys())
        
        for dex in dex_list:
            token_pair = dex_token_pairs[dex]
            
            try:
                # Get prices from DEX
                if not isinstance(dex, PriceSource):
                    continue

                price_source = cast(PriceSource, dex)
                # Get price of token0 in terms of token1, and token1 in terms of token0
                token0_price, token1_price = await self._get_token_pair_prices(
                    price_source=price_source,
                    token_pair=token_pair
                )
                
                dex_prices[dex] = (token0_price, token1_price)
                
            except Exception as e:
                logger.error(f"Error getting prices from {dex.id} for pair {key}: {e}")
        
        # Need at least 2 DEXs with valid prices
        if len(dex_prices) < 2:
            return []
        
        # Find arbitrage opportunities
        opportunities = []
        
        # Compare each DEX pair to find arbitrage opportunities
        for i, dex_a in enumerate(dex_list):
            if dex_a not in dex_prices:
                continue
                
            for dex_b in dex_list[i+1:]:
                if dex_b not in dex_prices:
                    continue
                
                token_pair_a = dex_token_pairs[dex_a]
                token_pair_b = dex_token_pairs[dex_b]
                
                price_a_0, price_a_1 = dex_prices[dex_a]
                price_b_0, price_b_1 = dex_prices[dex_b]
                
                # Check for profitable opportunities, token0 -> token1 direction
                if price_a_0 > price_b_0:
                    # Buy on dex_b, sell on dex_a
                    opportunity = await self._create_opportunity(
                        dex_buy=dex_b,
                        dex_sell=dex_a,
                        token_pair_buy=token_pair_b,
                        token_pair_sell=token_pair_a,
                        buy_price=price_b_0,
                        sell_price=price_a_0,
                        direction="0_to_1",
                        market_condition=market_condition,
                        min_profit_wei=min_profit_wei
                    )
                    if opportunity:
                        opportunities.append(opportunity)
                
                # Check for profitable opportunities, token1 -> token0 direction
                if price_a_1 > price_b_1:
                    # Buy on dex_b, sell on dex_a
                    opportunity = await self._create_opportunity(
                        dex_buy=dex_b,
                        dex_sell=dex_a,
                        token_pair_buy=token_pair_b,
                        token_pair_sell=token_pair_a,
                        buy_price=price_b_1,
                        sell_price=price_a_1,
                        direction="1_to_0",
                        market_condition=market_condition,
                        min_profit_wei=min_profit_wei
                    )
                    if opportunity:
                        opportunities.append(opportunity)
        
        return opportunities
    
    async def _get_token_pair_prices(
        self,
        price_source: PriceSource,
        token_pair: TokenPair
    ) -> Tuple[Decimal, Decimal]:
        """
        Get prices for a token pair from a price source with caching.
        
        Args:
            price_source: Price source to get prices from
            token_pair: Token pair to get prices for
            
        Returns:
            Tuple of (token0_price, token1_price)
        """
        # Create cache keys
        cache_key_0 = f"{price_source.id}_{token_pair.token0_address}_{token_pair.token1_address}"
        cache_key_1 = f"{price_source.id}_{token_pair.token1_address}_{token_pair.token0_address}"
        
        # Check cache
        token0_price = None
        token1_price = None
        current_time = time.time()
        
        async with self._cache_lock:
            cached_0 = self._price_cache.get(cache_key_0)
            if cached_0 and (current_time - cached_0[1] < self._cache_ttl):
                token0_price = cached_0[0]
            
            cached_1 = self._price_cache.get(cache_key_1)
            if cached_1 and (current_time - cached_1[1] < self._cache_ttl):
                token1_price = cached_1[0]
        
        # Get prices if not cached
        if token0_price is None:
            try:
                token0_price = await price_source.get_token_price(
                    base_token_address=token_pair.token0_address,
                    quote_token_address=token_pair.token1_address
                )
                async with self._cache_lock:
                    self._price_cache[cache_key_0] = (token0_price, current_time)
            except Exception as e:
                logger.error(f"Error getting token0 price from {price_source.id}: {e}")
                token0_price = Decimal("0")
        
        if token1_price is None:
            try:
                token1_price = await price_source.get_token_price(
                    base_token_address=token_pair.token1_address,
                    quote_token_address=token_pair.token0_address
                )
                async with self._cache_lock:
                    self._price_cache[cache_key_1] = (token1_price, current_time)
            except Exception as e:
                logger.error(f"Error getting token1 price from {price_source.id}: {e}")
                token1_price = Decimal("0")
        
        return token0_price, token1_price
    
    async def _create_opportunity(
        self,
        dex_buy: DEX,
        dex_sell: DEX,
        token_pair_buy: TokenPair,
        token_pair_sell: TokenPair,
        buy_price: Decimal,
        sell_price: Decimal,
        direction: str,
        market_condition: MarketCondition,
        min_profit_wei: int
    ) -> Optional[ArbitrageOpportunity]:
        """
        Create an arbitrage opportunity if it's profitable.
        
        Args:
            dex_buy: DEX to buy on
            dex_sell: DEX to sell on
            token_pair_buy: Token pair on buy DEX
            token_pair_sell: Token pair on sell DEX
            buy_price: Price on buy DEX
            sell_price: Price on sell DEX
            direction: Trading direction (0_to_1 or 1_to_0)
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei
            
        Returns:
            ArbitrageOpportunity if profitable, None otherwise
        """
        # Determine token addresses based on direction
        if direction == "0_to_1":
            # token0 -> token1 (buy token1 with token0, then sell token1 for token0)
            input_token_address = token_pair_buy.token0_address
            output_token_address = token_pair_buy.token0_address
            intermediate_token_address = token_pair_buy.token1_address
        else:
            # token1 -> token0 (buy token0 with token1, then sell token0 for token1)
            input_token_address = token_pair_buy.token1_address
            output_token_address = token_pair_buy.token1_address
            intermediate_token_address = token_pair_buy.token0_address
        
        # Calculate price difference and potential profit
        price_diff_percentage = (sell_price - buy_price) / buy_price * Decimal("100")
        
        # Skip if price difference is too small
        if price_diff_percentage < self.min_profit_percentage:
            return None
        
        # Estimate gas costs
        # Use average gas costs from market condition or default values
        gas_price = market_condition.gas_price if market_condition.gas_price else 50 * 10**9  # 50 gwei
        priority_fee = market_condition.priority_fee if market_condition.priority_fee else 1.5 * 10**9  # 1.5 gwei
        
        # Estimate gas usage - these would be more accurate with actual execution data
        estimated_gas_buy = 150000  # Approximate gas for swap
        estimated_gas_sell = 150000  # Approximate gas for swap
        total_gas_estimate = estimated_gas_buy + estimated_gas_sell
        
        # Calculate gas cost
        gas_cost_wei = total_gas_estimate * (gas_price + priority_fee)
        
        # Add buffer for potential increases
        gas_cost_with_buffer = gas_cost_wei * (Decimal("100") + self.gas_cost_buffer_percentage) / Decimal("100")
        
        # Calculate token amounts for a sample trade to estimate profit
        # This uses a simplified approach - actual implementation would account for price impact
        input_amount_wei = 1 * 10**18  # 1 token as sample size
        intermediate_amount_wei = input_amount_wei * buy_price
        output_amount_wei = intermediate_amount_wei * sell_price
        expected_profit_wei = output_amount_wei - input_amount_wei
        
        # Check if profit exceeds gas costs and minimum profit threshold
        if expected_profit_wei <= gas_cost_with_buffer or expected_profit_wei < min_profit_wei:
            return None
        
        # Create arbitrage route
        steps = [
            # Step 1: Buy intermediate token on dex_buy
            ArbitrageStep(
                dex=DEXPair(id=dex_buy.id, name=dex_buy.name),
                input_token=TokenAmount(
                    address=input_token_address,
                    symbol=token_pair_buy.token0_symbol if direction == "0_to_1" else token_pair_buy.token1_symbol,
                    amount=input_amount_wei
                ),
                output_token=TokenAmount(
                    address=intermediate_token_address,
                    symbol=token_pair_buy.token1_symbol if direction == "0_to_1" else token_pair_buy.token0_symbol,
                    amount=intermediate_amount_wei
                ),
                action="swap",
                gas_estimate=estimated_gas_buy
            ),
            # Step 2: Sell intermediate token on dex_sell
            ArbitrageStep(
                dex=DEXPair(id=dex_sell.id, name=dex_sell.name),
                input_token=TokenAmount(
                    address=intermediate_token_address,
                    symbol=token_pair_sell.token1_symbol if direction == "0_to_1" else token_pair_sell.token0_symbol,
                    amount=intermediate_amount_wei
                ),
                output_token=TokenAmount(
                    address=output_token_address,
                    symbol=token_pair_sell.token0_symbol if direction == "0_to_1" else token_pair_sell.token1_symbol,
                    amount=output_amount_wei
                ),
                action="swap",
                gas_estimate=estimated_gas_sell
            )
        ]
        
        route = ArbitrageRoute(
            steps=steps,
            input_token=TokenAmount(
                address=input_token_address,
                symbol=token_pair_buy.token0_symbol if direction == "0_to_1" else token_pair_buy.token1_symbol,
                amount=input_amount_wei
            ),
            output_token=TokenAmount(
                address=output_token_address,
                symbol=token_pair_sell.token0_symbol if direction == "0_to_1" else token_pair_sell.token1_symbol,
                amount=output_amount_wei
            ),
            gas_estimate=total_gas_estimate
        )
        
        # Calculate profit margin as percentage
        profit_margin_percentage = Decimal("100") * (output_amount_wei - input_amount_wei) / input_amount_wei
        
        # Calculate profit after gas costs
        profit_after_gas = expected_profit_wei - gas_cost_wei
        
        # Create opportunity
        opportunity = ArbitrageOpportunity(
            id=str(uuid.uuid4()),
            route=route,
            expected_profit=expected_profit_wei,
            expected_profit_after_gas=profit_after_gas,
            profit_margin_percentage=profit_margin_percentage,
            gas_estimate=total_gas_estimate,
            gas_price=gas_price,
            priority_fee=priority_fee,
            strategy_type=StrategyType.CROSS_DEX,
            confidence_score=self._calculate_confidence_score(
                price_diff_percentage=price_diff_percentage,
                market_condition=market_condition,
                token_pair_buy=token_pair_buy,
                token_pair_sell=token_pair_sell
            ),
            status=OpportunityStatus.DETECTED,
            creation_timestamp=int(time.time()),
            metadata={
                "price_diff_percentage": float(price_diff_percentage),
                "buy_dex": dex_buy.id,
                "sell_dex": dex_sell.id,
                "buy_price": float(buy_price),
                "sell_price": float(sell_price),
                "direction": direction,
                "token_pair": f"{token_pair_buy.token0_symbol}/{token_pair_buy.token1_symbol}"
            }
        )
        
        return opportunity
    
    def _calculate_confidence_score(
        self,
        price_diff_percentage: Decimal,
        market_condition: MarketCondition,
        token_pair_buy: TokenPair,
        token_pair_sell: TokenPair
    ) -> Decimal:
        """
        Calculate confidence score for an arbitrage opportunity.
        
        Args:
            price_diff_percentage: Price difference percentage
            market_condition: Current market condition
            token_pair_buy: Token pair on buy DEX
            token_pair_sell: Token pair on sell DEX
            
        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence from price difference
        # Higher price difference = higher confidence
        base_confidence = min(price_diff_percentage / Decimal("5"), Decimal("1"))
        
        # Adjust for market volatility
        volatility_factor = Decimal("1")
        if market_condition.market_volatility:
            # Higher volatility = lower confidence
            volatility_factor = max(Decimal("1") - market_condition.market_volatility / Decimal("100"), Decimal("0.2"))
        
        # Adjust for liquidity
        liquidity_factor = Decimal("1")
        if token_pair_buy.liquidity_usd and token_pair_sell.liquidity_usd:
            # Higher liquidity = higher confidence
            buy_liquidity = min(token_pair_buy.liquidity_usd / self.min_liquidity_usd, Decimal("1"))
            sell_liquidity = min(token_pair_sell.liquidity_usd / self.min_liquidity_usd, Decimal("1"))
            liquidity_factor = (buy_liquidity + sell_liquidity) / Decimal("2")
        
        # Adjust for network congestion
        congestion_factor = Decimal("1")
        if market_condition.network_congestion:
            # Higher congestion = lower confidence
            congestion_factor = max(Decimal("1") - market_condition.network_congestion / Decimal("100"), Decimal("0.2"))
        
        # Calculate final confidence score
        confidence = base_confidence * volatility_factor * liquidity_factor * congestion_factor
        
        # Ensure score is between 0 and 1
        return max(min(confidence, Decimal("1")), Decimal("0"))


async def create_cross_dex_detector(
    dexes: List[DEX],
    config: Dict[str, Any] = None
) -> CrossDexDetector:
    """
    Factory function to create a cross-DEX detector.
    
    Args:
        dexes: List of DEXs to monitor
        config: Configuration dictionary
        
    Returns:
        Initialized cross-DEX detector
    """
    return CrossDexDetector(dexes=dexes, config=config)