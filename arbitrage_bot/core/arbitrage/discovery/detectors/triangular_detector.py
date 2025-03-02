"""
Triangular Arbitrage Detector

This module contains the implementation of the TriangularDetector,
which identifies triangular arbitrage opportunities within a single DEX.
"""

import asyncio
import logging
import time
import uuid
from decimal import Decimal
from typing import Dict, List, Any, Optional, Set, Tuple, cast, DefaultDict
from collections import defaultdict

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


class TriangularDetector(OpportunityDetector):
    """
    Detector for triangular arbitrage opportunities.
    
    This detector identifies price discrepancies within a single DEX by trading
    through multiple tokens in a cycle and calculating the potential profit.
    """
    
    def __init__(
        self,
        dexes: List[DEX],
        config: Dict[str, Any] = None
    ):
        """
        Initialize the triangular detector.
        
        Args:
            dexes: List of DEXs to monitor
            config: Configuration dictionary
        """
        self.dexes = dexes
        self.config = config or {}
        
        # Configuration
        self.min_profit_percentage = Decimal(self.config.get("min_profit_percentage", "0.1"))  # 0.1%
        self.max_slippage = Decimal(self.config.get("max_slippage", "0.5"))  # 0.5%
        self.min_liquidity_usd = Decimal(self.config.get("min_liquidity_usd", "10000"))  # $10,000
        self.gas_cost_buffer_percentage = Decimal(self.config.get("gas_cost_buffer_percentage", "50"))  # 50%
        self.batch_size = int(self.config.get("batch_size", 20))
        self.max_path_length = int(self.config.get("max_path_length", 3))  # Maximum tokens in a path (typically 3 for triangular)
        self.confidence_threshold = Decimal(self.config.get("confidence_threshold", "0.7"))  # 70% confidence
        self.base_tokens = set(self.config.get("base_tokens", []))  # List of base tokens to use as starting points
        
        # Cache for token pairs and prices with timestamps
        self._token_pair_cache: Dict[str, Tuple[List[TokenPair], float]] = {}
        self._price_cache: Dict[str, Tuple[Decimal, float]] = {}
        self._token_graph_cache: Dict[str, Tuple[DefaultDict[str, List[Tuple[str, TokenPair]]], float]] = {}
        self._cache_ttl = float(self.config.get("cache_ttl_seconds", 5.0))
        
        # Locks
        self._cache_lock = asyncio.Lock()
        
        logger.info(f"TriangularDetector initialized with {len(dexes)} DEXs")
    
    async def detect_opportunities(
        self,
        market_condition: MarketCondition,
        max_results: int = 10,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """
        Detect triangular arbitrage opportunities.
        
        Args:
            market_condition: Current market condition
            max_results: Maximum number of opportunities to return
            **kwargs: Additional parameters
            
        Returns:
            List of arbitrage opportunities
        """
        logger.info("Detecting triangular arbitrage opportunities")
        
        # Extract parameters from kwargs or use defaults
        token_filter = kwargs.get("token_filter")
        dex_filter = kwargs.get("dex_filter")
        min_profit_wei = int(kwargs.get("min_profit_wei", self.config.get("min_profit_wei", 0)))
        base_tokens = kwargs.get("base_tokens", self.base_tokens)
        
        # Process each DEX separately
        all_opportunities = []
        
        # Filter DEXs if dex_filter is provided
        dexes_to_use = []
        if dex_filter:
            dexes_to_use = [dex for dex in self.dexes if dex.id in dex_filter]
        else:
            dexes_to_use = self.dexes
        
        # Process each DEX in parallel
        tasks = []
        for dex in dexes_to_use:
            task = asyncio.create_task(self._process_single_dex(
                dex=dex,
                token_filter=token_filter,
                base_tokens=base_tokens,
                market_condition=market_condition,
                min_profit_wei=min_profit_wei
            ))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error processing DEX: {result}")
            elif result:
                all_opportunities.extend(result)
        
        # Sort opportunities by expected profit and limit to max_results
        sorted_opportunities = sorted(
            all_opportunities,
            key=lambda o: o.expected_profit,
            reverse=True
        )
        
        return sorted_opportunities[:max_results]
    
    async def _process_single_dex(
        self,
        dex: DEX,
        token_filter: Optional[Set[str]],
        base_tokens: Optional[Set[str]],
        market_condition: MarketCondition,
        min_profit_wei: int
    ) -> List[ArbitrageOpportunity]:
        """
        Process a single DEX to find triangular arbitrage opportunities.
        
        Args:
            dex: DEX to process
            token_filter: Optional set of token addresses to filter by
            base_tokens: Optional set of base tokens to use as starting points
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei
            
        Returns:
            List of arbitrage opportunities
        """
        # Ensure DEX is a price source
        if not isinstance(dex, PriceSource):
            logger.warning(f"DEX {dex.id} is not a PriceSource, skipping")
            return []
        
        price_source = cast(PriceSource, dex)
        
        # Get token pairs and build token graph
        token_graph = await self._build_token_graph(price_source, token_filter)
        
        # If no base tokens specified, use tokens with the most connections
        actual_base_tokens = base_tokens or await self._get_most_connected_tokens(token_graph, 5)
        
        # Find triangular opportunities
        opportunities = []
        
        # Process base tokens in batches
        base_token_list = list(actual_base_tokens)
        batches = [base_token_list[i:i+self.batch_size] for i in range(0, len(base_token_list), self.batch_size)]
        
        for batch in batches:
            batch_tasks = []
            for base_token in batch:
                task = asyncio.create_task(self._find_triangular_paths(
                    dex=price_source,
                    token_graph=token_graph,
                    base_token=base_token,
                    market_condition=market_condition,
                    min_profit_wei=min_profit_wei
                ))
                batch_tasks.append(task)
            
            if batch_tasks:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Error finding triangular paths: {result}")
                    elif result:
                        opportunities.extend(result)
        
        return opportunities
    
    async def _build_token_graph(
        self,
        price_source: PriceSource,
        token_filter: Optional[Set[str]]
    ) -> DefaultDict[str, List[Tuple[str, TokenPair]]]:
        """
        Build a graph of tokens connected by trading pairs.
        
        Args:
            price_source: Price source to get token pairs from
            token_filter: Optional set of token addresses to filter by
            
        Returns:
            Graph of tokens as adjacency list
        """
        cache_key = f"{price_source.id}_graph_{hash(frozenset(token_filter)) if token_filter else 'all'}"
        
        # Check cache
        async with self._cache_lock:
            cached = self._token_graph_cache.get(cache_key)
            current_time = time.time()
            
            if cached and (current_time - cached[1] < self._cache_ttl):
                return cached[0]
        
        # Get token pairs
        token_pairs = await self._get_token_pairs_from_dex(price_source, token_filter)
        
        # Build graph
        graph: DefaultDict[str, List[Tuple[str, TokenPair]]] = defaultdict(list)
        
        for pair in token_pairs:
            token0 = pair.token0_address.lower()
            token1 = pair.token1_address.lower()
            
            # Add edges in both directions
            graph[token0].append((token1, pair))
            graph[token1].append((token0, pair))
        
        # Update cache
        async with self._cache_lock:
            self._token_graph_cache[cache_key] = (graph, time.time())
        
        return graph
    
    async def _get_token_pairs_from_dex(
        self,
        price_source: PriceSource,
        token_filter: Optional[Set[str]]
    ) -> List[TokenPair]:
        """
        Get token pairs from a single DEX with caching.
        
        Args:
            price_source: Price source to get token pairs from
            token_filter: Optional set of token addresses to filter by
            
        Returns:
            List of token pairs from the DEX
        """
        cache_key = f"{price_source.id}_pairs_{hash(frozenset(token_filter)) if token_filter else 'all'}"
        
        # Check cache
        async with self._cache_lock:
            cached = self._token_pair_cache.get(cache_key)
            current_time = time.time()
            
            if cached and (current_time - cached[1] < self._cache_ttl):
                return cached[0]
        
        # Get token pairs from DEX
        try:
            # Get all pairs from DEX
            token_pairs = await price_source.get_token_pairs(max_pairs=1000)
            
            # Filter by tokens if specified
            if token_filter:
                token_pairs = [
                    pair for pair in token_pairs
                    if pair.token0_address.lower() in token_filter or pair.token1_address.lower() in token_filter
                ]
            
            # Update cache
            async with self._cache_lock:
                self._token_pair_cache[cache_key] = (token_pairs, time.time())
            
            return token_pairs
            
        except Exception as e:
            logger.error(f"Error getting token pairs from {price_source.id}: {e}")
            return []
    
    async def _get_most_connected_tokens(
        self,
        token_graph: DefaultDict[str, List[Tuple[str, TokenPair]]],
        count: int = 5
    ) -> Set[str]:
        """
        Get the most connected tokens in the graph.
        
        Args:
            token_graph: Graph of tokens
            count: Number of tokens to return
            
        Returns:
            Set of most connected token addresses
        """
        # Count connections for each token
        connection_counts = {token: len(connections) for token, connections in token_graph.items()}
        
        # Sort by connection count and limit to count
        sorted_tokens = sorted(connection_counts.items(), key=lambda x: x[1], reverse=True)
        most_connected = [token for token, _ in sorted_tokens[:count]]
        
        return set(most_connected)
    
    async def _find_triangular_paths(
        self,
        dex: PriceSource,
        token_graph: DefaultDict[str, List[Tuple[str, TokenPair]]],
        base_token: str,
        market_condition: MarketCondition,
        min_profit_wei: int
    ) -> List[ArbitrageOpportunity]:
        """
        Find triangular arbitrage paths starting from a base token.
        
        Args:
            dex: DEX to use for pricing
            token_graph: Graph of tokens
            base_token: Base token to start from
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei
            
        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        base_token = base_token.lower()
        
        # Ensure base token is in the graph
        if base_token not in token_graph:
            return []
        
        # Find all 2-hop paths from base_token back to base_token
        # Note: We specifically target 3-token paths (triangular arbitrage)
        for token1_addr, pair1 in token_graph[base_token]:
            for token2_addr, pair2 in token_graph[token1_addr]:
                # Check if we have a path back to base_token
                if token2_addr != base_token and base_token in [addr for addr, _ in token_graph[token2_addr]]:
                    # Find the pair connecting token2 and base_token
                    pair3 = None
                    for addr, pair in token_graph[token2_addr]:
                        if addr == base_token:
                            pair3 = pair
                            break
                    
                    if pair3:
                        # We have a triangular path
                        path = [(base_token, token1_addr, pair1), 
                                (token1_addr, token2_addr, pair2), 
                                (token2_addr, base_token, pair3)]
                        
                        # Calculate profitability
                        opportunity = await self._calculate_triangular_profit(
                            dex=dex,
                            path=path,
                            market_condition=market_condition,
                            min_profit_wei=min_profit_wei
                        )
                        
                        if opportunity:
                            opportunities.append(opportunity)
        
        return opportunities
    
    async def _calculate_triangular_profit(
        self,
        dex: PriceSource,
        path: List[Tuple[str, str, TokenPair]],
        market_condition: MarketCondition,
        min_profit_wei: int
    ) -> Optional[ArbitrageOpportunity]:
        """
        Calculate profit for a triangular arbitrage path.
        
        Args:
            dex: DEX to use for pricing
            path: Path of token pairs
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei
            
        Returns:
            ArbitrageOpportunity if profitable, None otherwise
        """
        # Extract tokens and pairs
        base_token = path[0][0]
        intermediate_token1 = path[0][1]
        intermediate_token2 = path[1][1]
        
        pair1 = path[0][2]
        pair2 = path[1][2]
        pair3 = path[2][2]
        
        # Get token information (symbols, etc.)
        base_token_symbol = None
        token1_symbol = None
        token2_symbol = None
        
        if base_token == pair1.token0_address.lower():
            base_token_symbol = pair1.token0_symbol
            token1_symbol = pair1.token1_symbol
        else:
            base_token_symbol = pair1.token1_symbol
            token1_symbol = pair1.token0_symbol
            
        if intermediate_token1 == pair2.token0_address.lower():
            token2_symbol = pair2.token1_symbol
        else:
            token2_symbol = pair2.token0_symbol
        
        # Calculate price ratio for each step
        try:
            # Step 1: base_token -> intermediate_token1
            step1_price = await self._get_price_for_pair(
                dex=dex,
                from_token=base_token,
                to_token=intermediate_token1,
                pair=pair1
            )
            
            # Step 2: intermediate_token1 -> intermediate_token2
            step2_price = await self._get_price_for_pair(
                dex=dex,
                from_token=intermediate_token1,
                to_token=intermediate_token2,
                pair=pair2
            )
            
            # Step 3: intermediate_token2 -> base_token
            step3_price = await self._get_price_for_pair(
                dex=dex,
                from_token=intermediate_token2,
                to_token=base_token,
                pair=pair3
            )
            
            # Calculate overall price ratio
            overall_ratio = step1_price * step2_price * step3_price
            
            # If ratio > 1, then profitable (minus gas, slippage)
            profit_percentage = (overall_ratio - Decimal("1")) * Decimal("100")
            
            # Skip if profit is too small
            if profit_percentage < self.min_profit_percentage:
                return None
            
            # Calculate token amounts for a sample trade
            input_amount_wei = int(1 * 10**18)  # 1 token as sample
            
            # Calculate amounts for each step
            intermediate1_amount_wei = int(input_amount_wei * step1_price)
            intermediate2_amount_wei = int(intermediate1_amount_wei * step2_price)
            output_amount_wei = int(intermediate2_amount_wei * step3_price)
            
            # Calculate profit
            expected_profit_wei = output_amount_wei - input_amount_wei
            
            # Estimate gas costs
            # Use average gas costs from market condition or default values
            gas_price = market_condition.gas_price if market_condition.gas_price else 50 * 10**9  # 50 gwei
            priority_fee = market_condition.priority_fee if market_condition.priority_fee else 1.5 * 10**9  # 1.5 gwei
            
            # Estimate gas usage
            estimated_gas_step1 = 150000  # Approximate gas for swap
            estimated_gas_step2 = 150000  # Approximate gas for swap
            estimated_gas_step3 = 150000  # Approximate gas for swap
            total_gas_estimate = estimated_gas_step1 + estimated_gas_step2 + estimated_gas_step3
            
            # Calculate gas cost
            gas_cost_wei = total_gas_estimate * (gas_price + priority_fee)
            
            # Add buffer for potential increases
            gas_cost_with_buffer = gas_cost_wei * (Decimal("100") + self.gas_cost_buffer_percentage) / Decimal("100")
            
            # Check if profit exceeds gas costs and minimum profit threshold
            if expected_profit_wei <= gas_cost_with_buffer or expected_profit_wei < min_profit_wei:
                return None
            
            # Create arbitrage route
            steps = [
                # Step 1: base_token -> intermediate_token1
                ArbitrageStep(
                    dex=DEXPair(id=dex.id, name=dex.name),
                    input_token=TokenAmount(
                        address=base_token,
                        symbol=base_token_symbol or "unknown",
                        amount=input_amount_wei
                    ),
                    output_token=TokenAmount(
                        address=intermediate_token1,
                        symbol=token1_symbol or "unknown",
                        amount=intermediate1_amount_wei
                    ),
                    action="swap",
                    gas_estimate=estimated_gas_step1
                ),
                # Step 2: intermediate_token1 -> intermediate_token2
                ArbitrageStep(
                    dex=DEXPair(id=dex.id, name=dex.name),
                    input_token=TokenAmount(
                        address=intermediate_token1,
                        symbol=token1_symbol or "unknown",
                        amount=intermediate1_amount_wei
                    ),
                    output_token=TokenAmount(
                        address=intermediate_token2,
                        symbol=token2_symbol or "unknown",
                        amount=intermediate2_amount_wei
                    ),
                    action="swap",
                    gas_estimate=estimated_gas_step2
                ),
                # Step 3: intermediate_token2 -> base_token
                ArbitrageStep(
                    dex=DEXPair(id=dex.id, name=dex.name),
                    input_token=TokenAmount(
                        address=intermediate_token2,
                        symbol=token2_symbol or "unknown",
                        amount=intermediate2_amount_wei
                    ),
                    output_token=TokenAmount(
                        address=base_token,
                        symbol=base_token_symbol or "unknown",
                        amount=output_amount_wei
                    ),
                    action="swap",
                    gas_estimate=estimated_gas_step3
                )
            ]
            
            route = ArbitrageRoute(
                steps=steps,
                input_token=TokenAmount(
                    address=base_token,
                    symbol=base_token_symbol or "unknown",
                    amount=input_amount_wei
                ),
                output_token=TokenAmount(
                    address=base_token,
                    symbol=base_token_symbol or "unknown",
                    amount=output_amount_wei
                ),
                gas_estimate=total_gas_estimate
            )
            
            # Calculate profit margin as percentage
            profit_margin_percentage = profit_percentage
            
            # Calculate profit after gas costs
            profit_after_gas = expected_profit_wei - gas_cost_wei
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                profit_percentage=profit_percentage,
                market_condition=market_condition,
                path_pairs=[pair1, pair2, pair3]
            )
            
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
                strategy_type=StrategyType.TRIANGULAR,
                confidence_score=confidence_score,
                status=OpportunityStatus.DETECTED,
                creation_timestamp=int(time.time()),
                metadata={
                    "profit_percentage": float(profit_percentage),
                    "dex": dex.id,
                    "path": f"{base_token_symbol or 'unknown'} -> {token1_symbol or 'unknown'} -> {token2_symbol or 'unknown'} -> {base_token_symbol or 'unknown'}",
                    "step1_price": float(step1_price),
                    "step2_price": float(step2_price),
                    "step3_price": float(step3_price),
                    "overall_ratio": float(overall_ratio)
                }
            )
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error calculating triangular profit: {e}")
            return None
    
    async def _get_price_for_pair(
        self,
        dex: PriceSource,
        from_token: str,
        to_token: str,
        pair: TokenPair
    ) -> Decimal:
        """
        Get the price ratio for a token pair with caching.
        
        Args:
            dex: DEX to get price from
            from_token: Address of token to trade from
            to_token: Address of token to trade to
            pair: Token pair
            
        Returns:
            Price ratio (how much of to_token you get for 1 from_token)
        """
        # Create cache key
        cache_key = f"{dex.id}_{from_token}_{to_token}"
        
        # Check cache
        async with self._cache_lock:
            cached = self._price_cache.get(cache_key)
            current_time = time.time()
            
            if cached and (current_time - cached[1] < self._cache_ttl):
                return cached[0]
        
        # Get price from DEX
        try:
            if from_token.lower() == pair.token0_address.lower() and to_token.lower() == pair.token1_address.lower():
                # from_token is token0, to_token is token1
                price = await dex.get_token_price(
                    base_token_address=from_token,
                    quote_token_address=to_token
                )
            else:
                # from_token is token1, to_token is token0
                price = await dex.get_token_price(
                    base_token_address=from_token,
                    quote_token_address=to_token
                )
            
            # Update cache
            async with self._cache_lock:
                self._price_cache[cache_key] = (price, time.time())
            
            return price
            
        except Exception as e:
            logger.error(f"Error getting price from {dex.id} for {from_token} -> {to_token}: {e}")
            # Return 0 price to indicate no profitable trade
            return Decimal("0")
    
    def _calculate_confidence_score(
        self,
        profit_percentage: Decimal,
        market_condition: MarketCondition,
        path_pairs: List[TokenPair]
    ) -> Decimal:
        """
        Calculate confidence score for a triangular arbitrage opportunity.
        
        Args:
            profit_percentage: Profit percentage
            market_condition: Current market condition
            path_pairs: List of token pairs in the path
            
        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence from profit percentage
        # Higher profit = higher confidence
        base_confidence = min(profit_percentage / Decimal("5"), Decimal("1"))
        
        # Adjust for market volatility
        volatility_factor = Decimal("1")
        if market_condition.market_volatility:
            # Higher volatility = lower confidence
            volatility_factor = max(Decimal("1") - market_condition.market_volatility / Decimal("100"), Decimal("0.2"))
        
        # Adjust for liquidity
        liquidity_factor = Decimal("1")
        total_liquidity = Decimal("0")
        pair_count = 0
        
        for pair in path_pairs:
            if pair.liquidity_usd:
                total_liquidity += pair.liquidity_usd
                pair_count += 1
        
        if pair_count > 0:
            avg_liquidity = total_liquidity / Decimal(pair_count)
            liquidity_factor = min(avg_liquidity / self.min_liquidity_usd, Decimal("1"))
        else:
            liquidity_factor = Decimal("0.5")  # Default if no liquidity data
        
        # Adjust for network congestion
        congestion_factor = Decimal("1")
        if market_condition.network_congestion:
            # Higher congestion = lower confidence
            congestion_factor = max(Decimal("1") - market_condition.network_congestion / Decimal("100"), Decimal("0.2"))
        
        # Triangular arbitrage involves more complexity, reduce confidence slightly
        complexity_factor = Decimal("0.9")  # 10% reduction due to complexity
        
        # Calculate final confidence score
        confidence = base_confidence * volatility_factor * liquidity_factor * congestion_factor * complexity_factor
        
        # Ensure score is between 0 and 1
        return max(min(confidence, Decimal("1")), Decimal("0"))


async def create_triangular_detector(
    dexes: List[DEX],
    config: Dict[str, Any] = None
) -> TriangularDetector:
    """
    Factory function to create a triangular detector.
    
    Args:
        dexes: List of DEXs to monitor
        config: Configuration dictionary
        
    Returns:
        Initialized triangular detector
    """
    return TriangularDetector(dexes=dexes, config=config)