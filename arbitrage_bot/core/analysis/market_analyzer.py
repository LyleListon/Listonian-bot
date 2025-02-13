"""Market analysis utilities."""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from collections import defaultdict, deque
import lru

from ..web3.web3_manager import Web3Manager
from ..models.market_models import MarketTrend, MarketCondition, PricePoint
from ..models.opportunity import Opportunity
from ...utils.config_loader import load_config

logger = logging.getLogger(__name__)

# Cache settings
CACHE_TTL = 60  # 60 seconds
BATCH_SIZE = 50  # Process 50 items at a time
PRICE_BATCH_SIZE = 20  # Process 20 price requests at a time
CONDITION_BATCH_SIZE = 10  # Process 10 market conditions at a time
MAX_RETRIES = 3  # Maximum number of retries for failed operations
RETRY_DELAY = 1  # Delay between retries in seconds
CACHE_SIZE = 1000  # Maximum number of items in LRU cache
PREFETCH_THRESHOLD = 0.8  # Threshold to trigger prefetch
MAX_BATCH_SIZE = 100  # Maximum number of items to process in a batch
BATCH_TIMEOUT = 5  # Maximum time to wait for batch to fill (seconds)

class MarketAnalyzer:
    """Analyzes market conditions and opportunities."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize market analyzer."""
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        self.market_conditions = {}
        self._monitoring = False
        self._monitoring_task = None
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Cache settings
        self.cache_ttl = CACHE_TTL
        self.batch_size = BATCH_SIZE
        self.price_batch_size = PRICE_BATCH_SIZE
        self.condition_batch_size = CONDITION_BATCH_SIZE
        
        # LRU caches for frequently accessed data
        self._dex_cache = lru.LRU(CACHE_SIZE)
        self._price_cache = lru.LRU(CACHE_SIZE)
        self._metrics_cache = lru.LRU(CACHE_SIZE)
        self._opportunity_cache = lru.LRU(CACHE_SIZE)
        self._market_data_cache = lru.LRU(CACHE_SIZE)
        self._trade_cache = lru.LRU(CACHE_SIZE)
        
        # Cache timestamps
        self._dex_cache_times = {}
        self._price_cache_times = {}
        self._metrics_cache_times = {}
        self._opportunity_cache_times = {}
        self._market_data_cache_times = {}
        self._trade_cache_times = {}
        
        # Locks for thread safety
        self._dex_lock = asyncio.Lock()
        self._price_lock = asyncio.Lock()
        self._condition_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()
        self._market_lock = asyncio.Lock()
        self._trade_lock = asyncio.Lock()
        self._batch_lock = asyncio.Lock()
        
        # Price request batching
        self._price_requests = []
        self._price_request_times = {}
        self._last_price_batch = time.time()
        
        # Market data batching
        self._market_data_batch = []
        self._last_market_batch = time.time()
        
        # Recent market data for deduplication
        self._recent_market_data = deque(maxlen=1000)
        
        # Prefetch settings
        self._prefetch_size = 100  # Number of items to prefetch
        self._prefetch_threshold = PREFETCH_THRESHOLD
        
        # Start periodic tasks
        self._cleanup_task = None
        self._batch_task = None
        self._prefetch_task = None
        
        logger.info("Market analyzer initialized")

    async def get_opportunities(self) -> List[Dict[str, Any]]:
        """Get current arbitrage opportunities."""
        try:
            opportunities = []
            
            # Get all token pairs
            tokens = list(self.config['tokens'].keys())
            dexes = list(self.config['dexes'].keys())
            
            # Check each token pair across DEXes
            for token1 in tokens:
                for token2 in tokens:
                    if token1 == token2:
                        continue
                        
                    # Get prices across DEXes
                    prices = {}
                    for dex_name in dexes:
                        price = await self._get_price(token1, token2, dex_name)
                        if price:
                            prices[dex_name] = price
                    
                    if len(prices) < 2:
                        continue
                    
                    # Find price differences
                    for dex1 in prices:
                        for dex2 in prices:
                            if dex1 == dex2:
                                continue
                                
                            price1 = prices[dex1]
                            price2 = prices[dex2]
                            
                            # Calculate profit percentage
                            profit_pct = abs(price1 - price2) / min(price1, price2)
                            
                            # Skip if profit too small
                            if profit_pct < 0.01:  # 1% minimum profit
                                continue
                            
                            # Get market conditions
                            condition1 = await self.get_market_condition(token1)
                            condition2 = await self.get_market_condition(token2)
                            
                            if not condition1 or not condition2:
                                continue
                            
                            # Create opportunity
                            opportunity = {
                                'token_path': [token1, token2],
                                'dex_from': dex1,
                                'dex_to': dex2,
                                'price_from': price1,
                                'price_to': price2,
                                'profit_pct': float(profit_pct),
                                'amount_in': float(condition1['liquidity']),
                                'amount_out': float(condition1['liquidity'] * price2),
                                'profit_usd': float(condition1['liquidity'] * price2 * profit_pct),
                                'confidence': min(condition1['confidence'], condition2['confidence'])
                            }
                            
                            opportunities.append(opportunity)
            
            return sorted(opportunities, key=lambda x: x['profit_usd'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting opportunities: {e}")
            return []

    async def initialize(self) -> bool:
        """Initialize market analyzer."""
        try:
            # Start periodic tasks
            self._cleanup_task = asyncio.create_task(self._periodic_cache_cleanup())
            self._batch_task = asyncio.create_task(self._periodic_batch())
            self._prefetch_task = asyncio.create_task(self._periodic_prefetch())
            
            # Initialize BaseSwap with retries
            for attempt in range(MAX_RETRIES):
                try:
                    baseswap = await self._get_dex_instance('baseswap')
                    if not baseswap:
                        raise ValueError("Failed to get BaseSwap instance")
                        
                    await baseswap.initialize()
                    break
                    
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to initialize BaseSwap after {MAX_RETRIES} attempts: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize market analyzer: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            # Stop monitoring
            await self.stop_monitoring()
            
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
            await self._process_price_batch()
            await self._process_market_batch()
            
            # Clear caches
            self._dex_cache.clear()
            self._price_cache.clear()
            self._metrics_cache.clear()
            self._opportunity_cache.clear()
            self._market_data_cache.clear()
            self._trade_cache.clear()
            self._dex_cache_times.clear()
            self._price_cache_times.clear()
            self._metrics_cache_times.clear()
            self._opportunity_cache_times.clear()
            self._market_data_cache_times.clear()
            self._trade_cache_times.clear()
            
            # Clear batches
            self._price_requests.clear()
            self._market_data_batch.clear()
            
            # Clear recent market data
            self._recent_market_data.clear()
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            logger.info("Market analyzer cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during market analyzer cleanup: {e}")
            raise

    async def _periodic_batch(self) -> None:
        """Periodically process batches."""
        try:
            while True:
                # Process price batch if timeout reached
                current_time = time.time()
                if current_time - self._last_price_batch >= BATCH_TIMEOUT:
                    await self._process_price_batch()
                
                # Process market batch if timeout reached
                if current_time - self._last_market_batch >= BATCH_TIMEOUT:
                    await self._process_market_batch()
                
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in periodic batch: {e}")

    async def _process_price_batch(self) -> None:
        """Process price request batch."""
        try:
            async with self._price_lock:
                if not self._price_requests:
                    return
                    
                # Get batch
                batch = self._price_requests[:PRICE_BATCH_SIZE]
                self._price_requests = self._price_requests[PRICE_BATCH_SIZE:]
                self._last_price_batch = time.time()
            
            # Process price requests concurrently
            tasks = []
            for token1, token2, dex_name in batch:
                task = asyncio.create_task(self._get_price(
                    token1, token2, dex_name
                ))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error processing price batch: {e}")

    async def _process_market_batch(self) -> None:
        """Process market data batch."""
        try:
            async with self._market_lock:
                if not self._market_data_batch:
                    return
                    
                # Get batch
                batch = self._market_data_batch[:MAX_BATCH_SIZE]
                self._market_data_batch = self._market_data_batch[MAX_BATCH_SIZE:]
                self._last_market_batch = time.time()
            
            # Process market data concurrently
            tasks = []
            for token in batch:
                # Skip if recently processed
                key = f"market_data:{token}"
                if key in self._recent_market_data:
                    continue
                    
                # Add to recent market data
                self._recent_market_data.append(key)
                
                # Create task
                task = asyncio.create_task(self._process_market_data(token))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error processing market batch: {e}")

    async def _process_market_data(self, token: str) -> None:
        """Process market data for a single token."""
        try:
            # Get market data with retries
            for attempt in range(MAX_RETRIES):
                try:
                    market_data = await self._get_market_data(token)
                    if market_data:
                        # Update market conditions
                        async with self._condition_lock:
                            self.market_conditions[token] = self._create_market_condition(
                                market_data
                            )
                        break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to process market data for {token} after {MAX_RETRIES} attempts: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing market data for {token}: {e}")

    async def _periodic_prefetch(self) -> None:
        """Periodically prefetch data."""
        try:
            while True:
                await self._prefetch_data()
                await asyncio.sleep(5)  # Prefetch every 5 seconds
        except Exception as e:
            logger.error(f"Error in periodic prefetch: {e}")

    async def _prefetch_data(self) -> None:
        """Prefetch commonly accessed data."""
        try:
            # Check cache sizes
            async with self._cache_lock:
                price_size = len(self._price_cache)
                market_size = len(self._market_data_cache)
                
                # Prefetch if below threshold
                if price_size < self._prefetch_size * self._prefetch_threshold:
                    await self._prefetch_prices()
                    
                if market_size < self._prefetch_size * self._prefetch_threshold:
                    await self._prefetch_market_data()
                    
        except Exception as e:
            logger.error(f"Error prefetching data: {e}")

    async def _prefetch_prices(self) -> None:
        """Prefetch price data."""
        try:
            # Get token pairs
            token_pairs = []
            for token1 in self.config['tokens']:
                for token2 in self.config['tokens']:
                    if token1 != token2:
                        token_pairs.append((token1, token2))
            
            # Add to price batch
            async with self._price_lock:
                for token1, token2 in token_pairs:
                    self._price_requests.append((token1, token2, 'baseswap'))
                    
        except Exception as e:
            logger.error(f"Error prefetching prices: {e}")

    async def _prefetch_market_data(self) -> None:
        """Prefetch market data."""
        try:
            # Get tokens
            tokens = list(self.config['tokens'].keys())
            
            # Add to market batch
            async with self._market_lock:
                self._market_data_batch.extend(tokens)
                
        except Exception as e:
            logger.error(f"Error prefetching market data: {e}")

    async def _get_price(
        self,
        token1: str,
        token2: str,
        dex_name: str
    ) -> Optional[float]:
        """Get price with caching."""
        try:
            # Check cache first
            cache_key = f"price:{token1}:{token2}:{dex_name}"
            price = self._price_cache.get(cache_key)
            if price is not None:
                return price
            
            # Get price with retries
            for attempt in range(MAX_RETRIES):
                try:
                    # Get token addresses
                    token1_addr = self.config['tokens'][token1]['address']
                    token2_addr = self.config['tokens'][token2]['address']
                    
                    # Get DEX instance
                    dex = await self._get_dex_instance(dex_name)
                    if not dex:
                        return None
                    
                    # Get reserves in thread pool
                    loop = asyncio.get_event_loop()
                    reserves = await loop.run_in_executor(
                        self.executor,
                        dex.get_reserves_sync,
                        token1_addr,
                        token2_addr
                    )
                    
                    if not reserves:
                        return None
                    
                    # Calculate price
                    price = float(reserves['reserve1']) / float(reserves['reserve0'])
                    
                    # Update cache
                    self._price_cache[cache_key] = price
                    self._price_cache_times[cache_key] = time.time()
                    
                    return price
                    
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.debug(f"Failed to get price after {MAX_RETRIES} attempts: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting price: {e}")
            return None

    async def _get_cached_data(
        self,
        key: str,
        cache: Dict[str, Any],
        cache_times: Dict[str, float]
    ) -> Optional[Any]:
        """Get data from cache if not expired."""
        try:
            current_time = time.time()
            
            async with self._cache_lock:
                if key in cache:
                    last_update = cache_times.get(key, 0)
                    if current_time - last_update < self.cache_ttl:
                        return cache[key]
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached data: {e}")
            return None

    async def get_market_condition(self, token: str) -> Optional[Dict[str, Any]]:
        """Get market condition for a token."""
        try:
            # Check cache first
            cache_key = f"market_condition:{token}"
            condition = await self._get_cached_data(
                cache_key,
                self._market_data_cache,
                self._market_data_cache_times
            )
            if condition:
                return condition

            # Get market data
            market_data = await self._get_market_data(token)
            if not market_data:
                return None

            # Create market condition
            condition = self._create_market_condition(market_data)
            if not condition:
                return None

            # Update cache
            await self._update_cache(
                cache_key,
                condition,
                self._market_data_cache,
                self._market_data_cache_times
            )

            return condition

        except Exception as e:
            logger.error(f"Error getting market condition for {token}: {e}")
            return None

    async def _get_market_data(self, token: str) -> Optional[Dict[str, Any]]:
        """Get market data with caching."""
        try:
            # Check cache first
            cache_key = f"market_data:{token}"
            market_data = self._market_data_cache.get(cache_key)
            if market_data is not None:
                return market_data
            
            # Get market data with retries
            for attempt in range(MAX_RETRIES):
                try:
                    # Get token addresses
                    weth_address = self.config['tokens']['WETH']['address']
                    token_address = self.config['tokens'].get(token, {}).get('address')
                    if not token_address:
                        return None
                    
                    # Get BaseSwap instance
                    baseswap = await self._get_dex_instance('baseswap')
                    if not baseswap:
                        return None
                    
                    # Get market data concurrently
                    reserves_task = asyncio.create_task(baseswap.get_reserves(
                        weth_address, token_address
                    ))
                    volume_task = asyncio.create_task(baseswap.get_24h_volume(
                        weth_address, token_address
                    ))
                    trades_task = asyncio.create_task(baseswap.get_trades(token_address))
                    
                    reserves, volume, trades = await asyncio.gather(
                        reserves_task, volume_task, trades_task
                    )
                    
                    if not reserves:
                        return None
                    
                    # Calculate metrics in thread pool
                    loop = asyncio.get_event_loop()
                    metrics = await loop.run_in_executor(
                        self.executor,
                        self._calculate_market_metrics,
                        reserves,
                        volume,
                        trades
                    )
                    
                    if metrics:
                        # Update cache
                        self._market_data_cache[cache_key] = metrics
                        self._market_data_cache_times[cache_key] = time.time()
                    
                    return metrics
                    
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to get market data after {MAX_RETRIES} attempts: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return None

    def _calculate_market_metrics(
        self,
        reserves: Dict[str, Any],
        volume_24h: Optional[float],
        trades: Optional[List[Dict[str, Any]]]
    ) -> Optional[Dict[str, Any]]:
        """Calculate market metrics (CPU-bound)."""
        try:
            price = float(reserves['reserve1']) / float(reserves['reserve0'])
            liquidity = float(reserves['reserve0'])
            
            # Calculate trend metrics
            trend = "sideways"
            trend_strength = 0.0
            volatility = 0.0
            
            if trades:
                recent_trades = sorted(trades, key=lambda x: x['timestamp'])[-10:]
                prices = [t['price'] for t in recent_trades]
                
                if len(prices) >= 2:
                    trend = "up" if prices[-1] > prices[0] else "down" if prices[-1] < prices[0] else "sideways"
                    trend_strength = abs((prices[-1] - prices[0]) / prices[0])
                    volatility = sum(abs(prices[i] - prices[i-1])/prices[i-1] for i in range(1, len(prices))) / (len(prices)-1)
            
            # Calculate confidence score
            volume_score = min(float(volume_24h or 0) / 1000000, 1.0)
            liquidity_score = min(liquidity / 500000, 1.0)
            volatility_score = max(1.0 - volatility, 0.0)
            confidence = (volume_score + liquidity_score + volatility_score) / 3
            
            return {
                "trend": trend,
                "trend_strength": trend_strength,
                "trend_duration": 0.0,
                "volatility": volatility,
                "volume_24h": float(volume_24h or 0),
                "liquidity": float(liquidity),
                "volatility_24h": volatility,
                "price_impact": 1000 / liquidity if liquidity > 0 else 0,
                "confidence": confidence,
                "price": price
            }
            
        except Exception as e:
            logger.error(f"Error calculating market metrics: {e}")
            return None

    def _create_market_condition(self, market_data: Dict[str, Any]) -> MarketCondition:
        """Create market condition from market data."""
        try:
            trend = MarketTrend(
                direction=market_data.get("trend", "sideways"),
                strength=float(market_data.get("trend_strength", 0.0)),
                duration=float(market_data.get("trend_duration", 0.0)),
                volatility=float(market_data.get("volatility", 0.0)),
                confidence=float(market_data.get("confidence", 0.0))
            )
            
            return MarketCondition(
                price=Decimal(str(market_data.get("price", 0))),
                trend=trend,
                volume_24h=Decimal(str(market_data.get("volume_24h", 0))),
                liquidity=Decimal(str(market_data.get("liquidity", 0))),
                volatility_24h=float(market_data.get("volatility_24h", 0)),
                price_impact=float(market_data.get("price_impact", 0)),
                last_updated=float(datetime.now().timestamp())
            )
            
        except Exception as e:
            logger.error(f"Error creating market condition: {e}")
            return None

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
        """Main monitoring loop with concurrent updates."""
        try:
            while self._monitoring:
                try:
                    # Process tokens in batches
                    tokens = list(self.config['tokens'].keys())
                    for i in range(0, len(tokens), self.condition_batch_size):
                        batch = tokens[i:i + self.condition_batch_size]
                        
                        # Process batch in thread pool
                        loop = asyncio.get_event_loop()
                        batch_tasks = [
                            loop.run_in_executor(
                                self.executor,
                                self._update_token_condition_sync,
                                token
                            )
                            for token in batch
                        ]
                        
                        # Wait for batch results with retries
                        for task in batch_tasks:
                            for attempt in range(MAX_RETRIES):
                                try:
                                    condition = await task
                                    if condition:
                                        async with self._condition_lock:
                                            self.market_conditions[token] = condition
                                    break
                                except Exception as e:
                                    if attempt < MAX_RETRIES - 1:
                                        await asyncio.sleep(RETRY_DELAY)
                                        continue
                                    logger.error(f"Failed to update condition after {MAX_RETRIES} attempts: {e}")
                    
                    # Clean up caches periodically
                    await self._cleanup_caches()
                    
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

    def _update_token_condition_sync(self, token: str) -> Optional[MarketCondition]:
        """Update market condition for a single token (CPU-bound)."""
        try:
            # Get market data
            market_data = self._get_market_data_sync(token)
            if not market_data:
                return None
            
            # Create market condition
            return self._create_market_condition(market_data)
            
        except Exception as e:
            logger.error(f"Error updating market condition for {token}: {e}")
            return None

    def _get_market_data_sync(self, token: str) -> Optional[Dict[str, Any]]:
        """Get market data synchronously (CPU-bound)."""
        try:
            # Get token addresses
            weth_address = self.config['tokens']['WETH']['address']
            token_address = self.config['tokens'].get(token, {}).get('address')
            if not token_address:
                return None
            
            # Get BaseSwap instance
            baseswap = self._dex_cache.get('baseswap')
            if not baseswap:
                return None
            
            # Get market data
            reserves = baseswap.get_reserves_sync(weth_address, token_address)
            volume = baseswap.get_24h_volume_sync(weth_address, token_address)
            trades = baseswap.get_trades_sync(token_address)
            
            if not reserves:
                return None
            
            # Calculate metrics
            return self._calculate_market_metrics(reserves, volume, trades)
            
        except Exception as e:
            logger.error(f"Error getting market data for {token}: {e}")
            return None

    async def _periodic_cache_cleanup(self) -> None:
        """Periodically clean up caches."""
        try:
            while True:
                await self._cleanup_caches()
                await asyncio.sleep(self.cache_ttl / 2)  # Clean up every half TTL
        except Exception as e:
            logger.error(f"Error in periodic cache cleanup: {e}")

    async def _update_cache(
        self,
        key: str,
        data: Any,
        cache: Dict[str, Any],
        cache_times: Dict[str, float]
    ) -> None:
        """Update cache with new data."""
        try:
            async with self._cache_lock:
                cache[key] = data
                cache_times[key] = time.time()
        except Exception as e:
            logger.error(f"Error updating cache: {e}")

    async def _cleanup_caches(self) -> None:
        """Clean up expired cache entries."""
        try:
            current_time = time.time()
            
            async with self._cache_lock:
                # Clean up DEX cache
                expired_dexes = [
                    name for name, last_update in self._dex_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for name in expired_dexes:
                    del self._dex_cache[name]
                    del self._dex_cache_times[name]
                
                # Clean up price cache
                expired_prices = [
                    key for key, last_update in self._price_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_prices:
                    del self._price_cache[key]
                    del self._price_cache_times[key]
                
                # Clean up metrics cache
                expired_metrics = [
                    key for key, last_update in self._metrics_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_metrics:
                    del self._metrics_cache[key]
                    del self._metrics_cache_times[key]
                
                # Clean up opportunity cache
                expired_opps = [
                    key for key, last_update in self._opportunity_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_opps:
                    del self._opportunity_cache[key]
                    del self._opportunity_cache_times[key]
                
                # Clean up market data cache
                expired_market = [
                    key for key, last_update in self._market_data_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_market:
                    del self._market_data_cache[key]
                    del self._market_data_cache_times[key]
                
                # Clean up trade cache
                expired_trades = [
                    key for key, last_update in self._trade_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_trades:
                    del self._trade_cache[key]
                    del self._trade_cache_times[key]
                    
        except Exception as e:
            logger.error(f"Error cleaning up caches: {e}")

    async def _get_dex_instance(self, dex_name: str):
        """Get or create DEX instance from cache with TTL."""
        current_time = time.time()
        
        async with self._dex_lock:
            # Check cache with TTL
            if dex_name in self._dex_cache:
                last_update = self._dex_cache_times.get(dex_name, 0)
                if current_time - last_update < self.cache_ttl:
                    return self._dex_cache[dex_name]
            
            # Create new instance with retries
            for attempt in range(MAX_RETRIES):
                try:
                    # Create new instance
                    dex_class = self._get_dex_class(dex_name)
                    if not dex_class:
                        return None
                        
                    dex_config = self.config['dexes'][dex_name.lower()]
                    instance = dex_class(self.web3_manager, dex_config)
                    
                    # Update cache
                    self._dex_cache[dex_name] = instance
                    self._dex_cache_times[dex_name] = current_time
                    
                    return instance
                    
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to create DEX instance after {MAX_RETRIES} attempts: {e}")
                    return None

    def _get_dex_class(self, dex_name: str):
        """Get DEX class based on name."""
        try:
            if dex_name.lower() == 'baseswap':
                from ..dex.baseswap import Baseswap
                return Baseswap
            elif dex_name.lower() == 'swapbased':
                from ..dex.swapbased import SwapBased
                return SwapBased
            elif dex_name.lower() == 'pancakeswap':
                from ..dex.pancakeswap import Pancakeswap
                return Pancakeswap
            return None
        except Exception as e:
            logger.error(f"Failed to get DEX class for {dex_name}: {e}")
            return None

async def create_market_analyzer(web3_manager: Web3Manager, config: Dict[str, Any]) -> MarketAnalyzer:
    """Create and initialize market analyzer."""
    analyzer = MarketAnalyzer(web3_manager, config)
    success = await analyzer.initialize()
    if not success:
        raise RuntimeError("Failed to initialize market analyzer")
    return analyzer
