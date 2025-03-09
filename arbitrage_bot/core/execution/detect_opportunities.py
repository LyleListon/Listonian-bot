"""Detect arbitrage opportunities."""

import logging
import asyncio
from typing import Dict, List, Any, Tuple, Set, Optional, cast
from dataclasses import dataclass
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque
import time
import lru

from ..dex import DexManager
from ..analytics.analytics_system import AnalyticsSystem
from ..ml.ml_system import MLSystem
from ..models.opportunity import Opportunity, OpportunityStatus

logger = logging.getLogger(__name__)

# Cache settings
CACHE_TTL = 60  # 60 seconds
BATCH_SIZE = 50  # Process 50 items at a time
QUOTE_BATCH_SIZE = 20  # Process 20 quotes at a time
PATH_BATCH_SIZE = 10  # Process 10 paths at a time
MAX_RETRIES = 3  # Maximum number of retries for failed operations
RETRY_DELAY = 1  # Delay between retries in seconds
CACHE_SIZE = 1000  # Maximum number of items in LRU cache
PREFETCH_THRESHOLD = 0.8  # Threshold to trigger prefetch
MAX_BATCH_SIZE = 100  # Maximum number of items to process in a batch
BATCH_TIMEOUT = 5  # Maximum time to wait for batch to fill (seconds)

class OpportunityDetector:
    """Detects arbitrage opportunities across DEXes."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        web3_manager: Any,
        dex_manager: DexManager,
        analytics: AnalyticsSystem,
        ml_system: MLSystem
    ):
        """Initialize detector."""
        self.config = config
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.dex_manager = dex_manager
        self.analytics = analytics
        self.ml_system = ml_system
        
        # Get trading config with defaults
        self.config = config or {}
        trading_config = self.config.get("arbitrage", {})  # Use arbitrage section from config
        self.min_profit = Decimal(str(trading_config.get("min_profit_usd", "0.05")))
        self.max_slippage = Decimal(str(trading_config.get("slippage_tolerance", "0.001")))
        self.max_trade_size = Decimal(str(trading_config.get("max_trade_size_usd", "1000.0")))
        
        # Ensure required config sections exist
        if "tokens" not in self.config:
            self.config["tokens"] = {}
        if "pairs" not in self.config:
            self.config["pairs"] = []
        
        # Cache settings
        self.cache_ttl = CACHE_TTL
        self.batch_size = BATCH_SIZE
        self.quote_batch_size = QUOTE_BATCH_SIZE
        self.path_batch_size = PATH_BATCH_SIZE
        
        # LRU caches for frequently accessed data
        self._dex_cache = lru.LRU(CACHE_SIZE)
        self._quote_cache = lru.LRU(CACHE_SIZE)
        self._path_cache = lru.LRU(CACHE_SIZE)
        self._gas_cache = lru.LRU(CACHE_SIZE)
        self._token_cache = lru.LRU(CACHE_SIZE)
        
        # Cache timestamps
        self._dex_cache_times = {}
        self._quote_cache_times = {}
        self._path_cache_times = {}
        self._gas_cache_times = {}
        self._token_cache_times = {}
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Locks for thread safety
        self._cache_lock = asyncio.Lock()
        self._gas_lock = asyncio.Lock()
        self._quote_lock = asyncio.Lock()
        self._path_lock = asyncio.Lock()
        self._batch_lock = asyncio.Lock()
        
        # Gas price tracking
        self.gas_price = 0
        self.last_gas_update = 0
        self.gas_update_interval = 1  # 1 second
        
        # Opportunity batching
        self._opportunity_batch = []
        self._last_batch = time.time()
        
        # Quote batching
        self._quote_batch = []
        self._last_quote_batch = time.time()
        
        # Path batching
        self._path_batch = []
        self._last_path_batch = time.time()
        
        # Recent opportunities for deduplication
        self._recent_opportunities = deque(maxlen=1000)
        
        # Prefetch settings
        self._prefetch_size = 100  # Number of items to prefetch
        self._prefetch_threshold = PREFETCH_THRESHOLD
        
        # Start periodic tasks
        self._cleanup_task = None
        self._batch_task = None
        self._prefetch_task = None
        
        self.initialized = False
        logger.info("OpportunityDetector instance created")

    async def initialize(self) -> bool:
        """Initialize detector."""
        try:
            if self.initialized:
                logger.debug("OpportunityDetector already initialized")
                return True
                
            logger.info("Initializing OpportunityDetector...")
            
            # Initialize components concurrently with retries
            for attempt in range(MAX_RETRIES):
                try:
                    init_tasks = [
                        asyncio.create_task(self.dex_manager.initialize()),
                        asyncio.create_task(self.analytics.initialize()),
                        asyncio.create_task(self.ml_system.initialize())
                    ]
                    
                    results = await asyncio.gather(*init_tasks)
                    if not all(results):
                        raise ValueError("Failed to initialize one or more components")
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to initialize after {MAX_RETRIES} attempts: {e}")
                    return False
            
            # Get initial gas price in thread pool
            loop = asyncio.get_event_loop()
            try:
                self.gas_price = await loop.run_in_executor(
                    self.executor,
                    lambda: self.w3.eth.gas_price
                )
                logger.debug(f"Initial gas price: {self.w3.from_wei(self.gas_price, 'gwei')} gwei")
            except Exception as e:
                logger.warning(f"Failed to get initial gas price: {e}, using fallback")
                self.gas_price = self.w3.to_wei(100, 'gwei')
            
            # Start periodic tasks
            self._cleanup_task = asyncio.create_task(self._periodic_cache_cleanup())
            self._batch_task = asyncio.create_task(self._periodic_batch())
            self._prefetch_task = asyncio.create_task(self._periodic_prefetch())
            
            self.initialized = True
            logger.info("OpportunityDetector initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpportunityDetector: {e}", exc_info=True)
            return False

    async def ensure_initialized(self) -> None:
        """Ensure detector is initialized."""
        if not self.initialized:
            logger.debug("OpportunityDetector not initialized, initializing now...")
            if not await self.initialize():
                raise RuntimeError("Failed to initialize OpportunityDetector")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if not self.initialized:
            logger.debug("OpportunityDetector already cleaned up")
            return
            
        try:
            logger.info("Cleaning up OpportunityDetector resources...")
            
            # Cancel periodic tasks
            tasks = [
                self._cleanup_task,
                self._batch_task,
                self._prefetch_task
            ]
            
            for task in tasks:
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Process any remaining batches
            await self._process_opportunity_batch()
            await self._process_quote_batch()
            await self._process_path_batch()
            
            # Clean up components concurrently
            cleanup_tasks = []
            
            if self.dex_manager:
                cleanup_tasks.append(asyncio.create_task(self.dex_manager.cleanup()))
            if self.analytics:
                cleanup_tasks.append(asyncio.create_task(self.analytics.cleanup()))
            if self.ml_system:
                cleanup_tasks.append(asyncio.create_task(self.ml_system.cleanup()))
            
            # Wait for all cleanups
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Reset state
            self.initialized = False
            self.gas_price = 0
            self.last_gas_update = 0
            
            # Clear caches
            self._dex_cache.clear()
            self._quote_cache.clear()
            self._path_cache.clear()
            self._gas_cache.clear()
            self._token_cache.clear()
            self._dex_cache_times.clear()
            self._quote_cache_times.clear()
            self._path_cache_times.clear()
            self._gas_cache_times.clear()
            self._token_cache_times.clear()
            
            # Clear batches
            self._opportunity_batch.clear()
            self._quote_batch.clear()
            self._path_batch.clear()
            
            # Clear recent opportunities
            self._recent_opportunities.clear()
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            logger.info("OpportunityDetector cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during OpportunityDetector cleanup: {e}", exc_info=True)
            raise

    async def detect_opportunities(self) -> List[Opportunity]:
        """Detect arbitrage opportunities across configured DEXes."""
        try:
            await self.ensure_initialized()
            opportunities = []
            
            if not self.initialized:
                logger.error("OpportunityDetector not properly initialized")
                await self.cleanup()
                return []
            
            # Update gas price if needed
            await self._update_gas_price()
            
            # Get pairs sorted by priority
            pairs = []
            try:
                pairs = sorted(
                    self.config.get("pairs", []),
                    key=lambda x: (x.get("priority", 0), x.get("historical_profit", 0)),
                    reverse=True
                )
            except Exception as e:
                logger.error(f"Error getting pairs from config: {e}")
                pairs = []

            # Detect opportunities concurrently
            direct_task = asyncio.create_task(self._detect_direct_arbitrage(pairs))
            triangular_task = asyncio.create_task(self._detect_triangular_arbitrage(pairs))
            
            direct_opportunities, triangular_opportunities = await asyncio.gather(
                direct_task, triangular_task
            )
            
            opportunities.extend(direct_opportunities)
            opportunities.extend(triangular_opportunities)

            # Sort by priority and filter by minimum profit in thread pool
            loop = asyncio.get_event_loop()
            opportunities = await loop.run_in_executor(
                self.executor,
                self._filter_and_sort_opportunities,
                opportunities
            )
            
            # Add to batch
            async with self._batch_lock:
                self._opportunity_batch.extend(opportunities)
                
                # Process batch if full or timeout reached
                current_time = time.time()
                if (len(self._opportunity_batch) >= MAX_BATCH_SIZE or 
                    current_time - self._last_batch >= BATCH_TIMEOUT):
                    await self._process_opportunity_batch()
            
            if opportunities:
                logger.info(f"Found {len(opportunities)} opportunities")
            return opportunities

        except Exception as e:
            logger.error(f"Error detecting opportunities: {e}", exc_info=True)
            return []

    async def _process_opportunity_batch(self) -> None:
        """Process opportunity batch."""
        try:
            async with self._batch_lock:
                if not self._opportunity_batch:
                    return
                    
                # Get batch
                batch = self._opportunity_batch[:MAX_BATCH_SIZE]
                self._opportunity_batch = self._opportunity_batch[MAX_BATCH_SIZE:]
                self._last_batch = time.time()
            
            # Process opportunities concurrently
            tasks = []
            for opportunity in batch:
                # Skip if recently seen
                key = f"{opportunity.buy_dex}:{opportunity.sell_dex}:{opportunity.token_pair}"
                if key in self._recent_opportunities:
                    continue
                    
                # Add to recent opportunities
                self._recent_opportunities.append(key)
                
                # Create task
                task = asyncio.create_task(self._process_single_opportunity(opportunity))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error processing opportunity batch: {e}")

    async def _process_single_opportunity(self, opportunity: Opportunity) -> None:
        """Process a single opportunity."""
        try:
            # Get ML prediction
            prediction = await self.ml_system.predict_trade_success({
                'profit_percent': opportunity.profit_percent,
                'buy_amount': opportunity.buy_amount,
                'gas_cost': opportunity.estimated_gas,
                'price_impact': opportunity.market_conditions['price_impact']
            })
            
            if prediction[0] > 0.8:  # Success probability threshold
                # Update analytics
                await self.analytics.analyze_opportunity(opportunity)
                
                # Store opportunity
                from ..memory import get_memory_bank
                memory_bank = await get_memory_bank()
                await memory_bank.store_opportunities([opportunity])
                
        except Exception as e:
            logger.error(f"Error processing opportunity: {e}")

    def _filter_and_sort_opportunities(
        self,
        opportunities: List[Opportunity]
    ) -> List[Opportunity]:
        """Filter and sort opportunities (CPU-bound)."""
        try:
            # Filter by minimum profit
            opportunities = [
                opp for opp in opportunities
                if opp.net_profit > float(self.min_profit)
            ]
            
            # Sort by priority
            opportunities.sort(key=lambda x: x.priority, reverse=True)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error filtering and sorting opportunities: {e}")
            return []

    async def _get_dex_quotes(
        self,
        token0_addr: str,
        token1_addr: str,
        amount: int
    ) -> Dict[str, Dict[str, Any]]:
        """Get quotes from all DEXes concurrently."""
        try:
            # Check cache first
            cache_key = f"{token0_addr}:{token1_addr}:{amount}"
            quotes = await self._get_cached_data(
                cache_key,
                self._quote_cache,
                self._quote_cache_times
            )
            if quotes:
                return quotes
            
            # Add to quote batch
            async with self._quote_lock:
                self._quote_batch.append((token0_addr, token1_addr, amount))
                
                # Process batch if full or timeout reached
                current_time = time.time()
                if (len(self._quote_batch) >= QUOTE_BATCH_SIZE or 
                    current_time - self._last_quote_batch >= BATCH_TIMEOUT):
                    await self._process_quote_batch()
            
            # Create quote tasks for each DEX
            quote_tasks = []
            for dex_name, dex in self.dex_manager.dexes.items():
                task = asyncio.create_task(self._get_single_quote(
                    dex_name, dex, token0_addr, token1_addr, amount
                ))
                quote_tasks.append((dex_name, task))
            
            # Wait for all quotes with retries
            quotes = {}
            for dex_name, task in quote_tasks:
                for attempt in range(MAX_RETRIES):
                    try:
                        quote = await task
                        if quote:
                            quotes[dex_name] = quote
                        break
                    except Exception as e:
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        logger.debug(f"Error getting quote from {dex_name} after {MAX_RETRIES} attempts: {e}")
            
            # Update cache
            await self._update_cache(
                cache_key,
                quotes,
                self._quote_cache,
                self._quote_cache_times
            )
            
            return quotes
            
        except Exception as e:
            logger.error(f"Error getting DEX quotes: {e}")
            return {}

    async def _process_quote_batch(self) -> None:
        """Process quote batch."""
        try:
            async with self._quote_lock:
                if not self._quote_batch:
                    return
                    
                # Get batch
                batch = self._quote_batch[:QUOTE_BATCH_SIZE]
                self._quote_batch = self._quote_batch[QUOTE_BATCH_SIZE:]
                self._last_quote_batch = time.time()
            
            # Process quotes concurrently
            tasks = []
            for token0_addr, token1_addr, amount in batch:
                task = asyncio.create_task(self._get_dex_quotes(
                    token0_addr, token1_addr, amount
                ))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error processing quote batch: {e}")

    async def _get_single_quote(
        self,
        dex_name: str,
        dex: Any,
        token0_addr: str,
        token1_addr: str,
        amount: int
    ) -> Optional[Dict[str, Any]]:
        """Get quote from a single DEX with caching."""
        try:
            cache_key = f"{dex_name}:{token0_addr}:{token1_addr}:{amount}"
            
            # Check cache first
            quote = self._quote_cache.get(cache_key)
            if quote is not None:
                return quote
            
            # Get quote with retries
            for attempt in range(MAX_RETRIES):
                try:
                    quote = await dex.get_quote_with_impact(amount, [token0_addr, token1_addr])
                    if quote:
                        # Update cache
                        self._quote_cache[cache_key] = quote
                        self._quote_cache_times[cache_key] = time.time()
                        return quote
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.debug(f"Error getting quote from {dex_name} after {MAX_RETRIES} attempts: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting quote from {dex_name}: {e}")
            return None

    async def _detect_direct_arbitrage(self, pairs: List[Dict]) -> List[Opportunity]:
        """Detect direct arbitrage between two DEXes concurrently."""
        try:
            # Process pairs in batches
            opportunities = []
            for i in range(0, len(pairs), self.batch_size):
                batch = pairs[i:i + self.batch_size]
                
                # Process batch in thread pool
                loop = asyncio.get_event_loop()
                batch_tasks = [
                    loop.run_in_executor(
                        self.executor,
                        self._analyze_direct_pair,
                        pair
                    )
                    for pair in batch
                ]
                
                # Wait for batch results with retries
                for task in batch_tasks:
                    for attempt in range(MAX_RETRIES):
                        try:
                            result = await task
                            if isinstance(result, list):
                                opportunities.extend(result)
                            break
                        except Exception as e:
                            if attempt < MAX_RETRIES - 1:
                                await asyncio.sleep(RETRY_DELAY)
                                continue
                            logger.error(f"Error in pair analysis after {MAX_RETRIES} attempts: {e}")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error in direct arbitrage detection: {e}")
            return []

    async def _analyze_direct_pair(self, pair: Dict) -> List[Opportunity]:
        """Analyze a single pair for direct arbitrage opportunities."""
        opportunities = []
        try:
            # Safely get token addresses
            token0 = pair.get("token0")
            token1 = pair.get("token1")
            if not token0 or not token1:
                logger.error(f"Invalid pair configuration: {pair}")
                return []
                
            tokens = self.config.get("tokens", {})
            token0_info = tokens.get(token0, {})
            token1_info = tokens.get(token1, {})
            
            token0_addr = token0_info.get("address")
            token1_addr = token1_info.get("address")
            
            if not token0_addr or not token1_addr:
                logger.error(f"Missing token addresses for pair {token0}/{token1}")
                return []
            
            # Get quotes from all DEXes concurrently
            quotes = await self._get_dex_quotes(
                token0_addr,
                token1_addr,
                int(float(self.max_trade_size))
            )
            
            # Check for arbitrage opportunities
            for buy_dex, buy_quote in quotes.items():
                for sell_dex, sell_quote in quotes.items():
                    if buy_dex == sell_dex:
                        continue
                        
                    # Calculate profit
                    buy_price = Decimal(str(buy_quote['amount_out'])) / self.max_trade_size
                    sell_price = Decimal(str(sell_quote['amount_in'])) / self.max_trade_size
                    profit_percent = (sell_price - buy_price) / buy_price
                    
                    # Calculate optimal amount
                    optimal_amount = min(
                        self.max_trade_size,
                        Decimal(str(buy_quote['liquidity_depth'])),
                        Decimal(str(sell_quote['liquidity_depth']))
                    )
                    
                    # Get gas cost and ML prediction concurrently
                    gas_task = asyncio.create_task(self._estimate_gas_cost(buy_dex, sell_dex))
                    ml_task = asyncio.create_task(self.ml_system.predict_trade_success({
                        'profit_percent': float(profit_percent),
                        'buy_amount': float(optimal_amount),
                        'gas_cost': 0,  # Will update after gas estimation
                        'buy_impact': buy_quote['price_impact'],
                        'sell_impact': sell_quote['price_impact']
                    }))
                    
                    gas_cost, (success_prob, importance) = await asyncio.gather(gas_task, ml_task)
                    net_profit = profit_percent * optimal_amount - Decimal(str(gas_cost))
                    
                    if net_profit > self.min_profit and success_prob > 0.8:
                        opportunities.append(
                            Opportunity(
                                buy_dex=buy_dex,
                                sell_dex=sell_dex,
                                token_pair=f"{pair['token0']}/{pair['token1']}",
                                profit_percent=float(profit_percent),
                                buy_amount=float(optimal_amount),
                                sell_amount=float(optimal_amount * (1 - self.max_slippage)),
                                estimated_gas=float(gas_cost),
                                net_profit=float(net_profit),
                                priority=self._calculate_priority_score(
                                    profit_percent=float(profit_percent),
                                    net_profit=float(net_profit),
                                    gas_cost=float(gas_cost),
                                    success_prob=success_prob,
                                    impact_score=1 - max(
                                        buy_quote['price_impact'],
                                        sell_quote['price_impact']
                                    )
                                ),
                                route_type="direct",
                                confidence_score=success_prob,
                                market_conditions={
                                    'liquidity': float(min(
                                        buy_quote['liquidity_depth'],
                                        sell_quote['liquidity_depth']
                                    )),
                                    'price_impact': max(
                                        buy_quote['price_impact'],
                                        sell_quote['price_impact']
                                    ),
                                    'max_trade_size': float(optimal_amount)
                                }
                            )
                        )
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error analyzing direct pair: {e}")
            return []

    async def _detect_triangular_arbitrage(self, pairs: List[Dict]) -> List[Opportunity]:
        """Detect triangular arbitrage opportunities concurrently."""
        try:
            # Get all valid tokens from pairs
            tokens = set()
            config_tokens = self.config.get("tokens", {})
            for pair in pairs:
                token0 = pair.get("token0")
                token1 = pair.get("token1")
                if token0 and token1 and token0 in config_tokens and token1 in config_tokens:
                    tokens.add(token0)
                    tokens.add(token1)
            
            # Process paths in batches
            opportunities = []
            paths = []
            for token_a in tokens:
                for token_b in tokens:
                    if token_a == token_b:
                        continue
                        
                    for token_c in tokens:
                        if token_c in (token_a, token_b):
                            continue
                            
                        paths.append((token_a, token_b, token_c))
            
            # Add paths to batch
            async with self._path_lock:
                self._path_batch.extend(paths)
                
                # Process batch if full or timeout reached
                current_time = time.time()
                if (len(self._path_batch) >= PATH_BATCH_SIZE or 
                    current_time - self._last_path_batch >= BATCH_TIMEOUT):
                    await self._process_path_batch()
            
            for i in range(0, len(paths), self.path_batch_size):
                batch = paths[i:i + self.path_batch_size]
                
                # Process batch in thread pool
                loop = asyncio.get_event_loop()
                batch_tasks = [
                    loop.run_in_executor(
                        self.executor,
                        self._analyze_triangular_path,
                        path[0], path[1], path[2]
                    )
                    for path in batch
                ]
                
                # Wait for batch results with retries
                for task in batch_tasks:
                    for attempt in range(MAX_RETRIES):
                        try:
                            result = await task
                            if isinstance(result, list):
                                opportunities.extend(result)
                            break
                        except Exception as e:
                            if attempt < MAX_RETRIES - 1:
                                await asyncio.sleep(RETRY_DELAY)
                                continue
                            logger.error(f"Error in path analysis after {MAX_RETRIES} attempts: {e}")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error in triangular arbitrage detection: {e}")
            return []

    async def _process_path_batch(self) -> None:
        """Process path batch."""
        try:
            async with self._path_lock:
                if not self._path_batch:
                    return
                    
                # Get batch
                batch = self._path_batch[:PATH_BATCH_SIZE]
                self._path_batch = self._path_batch[PATH_BATCH_SIZE:]
                self._last_path_batch = time.time()
            
            # Process paths concurrently
            tasks = []
            for token_a, token_b, token_c in batch:
                task = asyncio.create_task(self._analyze_triangular_path(
                    token_a, token_b, token_c
                ))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error processing path batch: {e}")

    async def _analyze_triangular_path(
        self,
        token_a: str,
        token_b: str,
        token_c: str
    ) -> List[Opportunity]:
        """Analyze a single triangular path for arbitrage opportunities."""
        opportunities = []
        try:
            # Safely get token addresses
            tokens = self.config.get("tokens", {})
            token_a_info = tokens.get(token_a, {})
            token_b_info = tokens.get(token_b, {})
            token_c_info = tokens.get(token_c, {})
            
            token_a_addr = token_a_info.get("address")
            token_b_addr = token_b_info.get("address")
            token_c_addr = token_c_info.get("address")
            
            if not all([token_a_addr, token_b_addr, token_c_addr]):
                logger.error(f"Missing token addresses for path {token_a}-{token_b}-{token_c}")
                return []

            # Get best DEXes for each leg concurrently
            dex_tasks = [
                asyncio.create_task(self.dex_manager.get_best_dex(f"{token_a}/{token_b}")),
                asyncio.create_task(self.dex_manager.get_best_dex(f"{token_b}/{token_c}")),
                asyncio.create_task(self.dex_manager.get_best_dex(f"{token_c}/{token_a}"))
            ]
            
            dex1, dex2, dex3 = await asyncio.gather(*dex_tasks)
            
            if not all([dex1, dex2, dex3]):
                logger.debug(f"Could not find DEXes for path {token_a}-{token_b}-{token_c}")
                return []
            
            # Get quotes concurrently
            quote_tasks = [
                asyncio.create_task(self._get_single_quote(
                    dex1,
                    self.dex_manager.get_dex(dex1),
                    token_a_addr,
                    token_b_addr,
                    int(float(self.max_trade_size))
                )),
                asyncio.create_task(self._get_single_quote(
                    dex2,
                    self.dex_manager.get_dex(dex
