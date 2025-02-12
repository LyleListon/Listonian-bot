"""Memory-enabled market analyzer with caching capabilities."""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Set, Tuple
from decimal import Decimal
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import lru

from ..memory.manager import get_memory_bank
from .market_analyzer import MarketAnalyzer
from ..models.market_models import MarketTrend, MarketCondition

logger = logging.getLogger(__name__)

# Cache settings
CACHE_TTL = 30  # Cache market conditions for 30 seconds
BATCH_SIZE = 50  # Process 50 items at a time
MAX_RETRIES = 3  # Maximum number of retries for failed operations
RETRY_DELAY = 1  # Delay between retries in seconds
CACHE_SIZE = 1000  # Maximum number of items in LRU cache
PREFETCH_THRESHOLD = 0.8  # Threshold to trigger prefetch
MAX_BATCH_SIZE = 100  # Maximum number of items to process in a batch
BATCH_TIMEOUT = 5  # Maximum time to wait for batch to fill (seconds)

class MemoryEnabledMarketAnalyzer(MarketAnalyzer):
    """Market analyzer with memory caching capabilities."""
    
    def __init__(self, web3_manager, config: Dict[str, Any]):
        """Initialize memory-enabled market analyzer."""
        super().__init__(web3_manager, config)
        self.memory = get_memory_bank()
        self._cache_ttl = CACHE_TTL
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Memory batch processing
        self._memory_batch = []
        self._last_memory_batch = datetime.now().timestamp()
        self._memory_batch_lock = asyncio.Lock()
        
        # Market data batching
        self._market_data_batch = []
        self._last_market_batch = datetime.now().timestamp()
        self._market_batch_lock = asyncio.Lock()
        
        # Recent market data for deduplication
        self._recent_market_data = deque(maxlen=1000)
        
        # LRU caches for frequently accessed data
        self._market_cache = lru.LRU(CACHE_SIZE)
        self._metrics_cache = lru.LRU(CACHE_SIZE)
        self._opportunity_cache = lru.LRU(CACHE_SIZE)
        
        # Cache timestamps
        self._market_cache_times = {}
        self._metrics_cache_times = {}
        self._opportunity_cache_times = {}
        
        # Prefetch settings
        self._prefetch_size = 100  # Number of items to prefetch
        self._prefetch_threshold = PREFETCH_THRESHOLD
        
        # Start periodic tasks
        self._batch_task = asyncio.create_task(self._periodic_memory_batch())
        self._market_task = asyncio.create_task(self._periodic_market_batch())
        self._prefetch_task = asyncio.create_task(self._periodic_prefetch())
        
        logger.info("Memory-enabled market analyzer initialized")

    async def get_market_condition(self, token: str) -> Optional[Dict[str, Any]]:
        """Get current market condition for token with caching."""
        try:
            # Check local cache first
            cache_key = f"condition_{token}"
            condition = self._market_cache.get(cache_key)
            if condition is not None:
                return condition
            
            # Try to get from memory with retries
            for attempt in range(MAX_RETRIES):
                try:
                    cached = self.memory.get_market_data(cache_key)
                    if cached:
                        # Update local cache
                        self._market_cache[cache_key] = cached
                        self._market_cache_times[cache_key] = datetime.now().timestamp()
                        return cached
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to get market condition from memory: {e}")
                    break

            # If not in memory, analyze market and store concurrently
            market_task = asyncio.create_task(self.analyze_market_conditions(token))
            
            market_data = await market_task
            if market_data:
                # Process market data in thread pool
                loop = asyncio.get_event_loop()
                condition = await loop.run_in_executor(
                    self.executor,
                    self._process_market_data,
                    market_data
                )
                
                if condition:
                    condition_dict = condition.__dict__
                    
                    # Update local cache
                    self._market_cache[cache_key] = condition_dict
                    self._market_cache_times[cache_key] = datetime.now().timestamp()
                    
                    # Store in memory batch
                    async with self._memory_batch_lock:
                        self._memory_batch.append((
                            cache_key,
                            condition_dict,
                            self._cache_ttl
                        ))
                    
                    return condition_dict
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get market condition for {token}: {e}")
            return None

    def _process_market_data(self, market_data: Dict[str, Any]) -> Optional[MarketCondition]:
        """Process market data into condition (CPU-bound)."""
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
            logger.error(f"Error processing market data: {e}")
            return None

    async def get_opportunities(self):
        """Get arbitrage opportunities with memory caching."""
        try:
            # Check local cache first
            opportunities = self._opportunity_cache.get("opportunities")
            if opportunities is not None:
                return opportunities
            
            # Try to get from memory with retries
            for attempt in range(MAX_RETRIES):
                try:
                    cached = self.memory.get_market_data("opportunities")
                    if cached:
                        # Update local cache
                        self._opportunity_cache["opportunities"] = cached
                        self._opportunity_cache_times["opportunities"] = datetime.now().timestamp()
                        return cached
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to get opportunities from memory: {e}")
                    break

            # If not in memory, get fresh opportunities
            opportunities = await super().get_opportunities()
            
            if opportunities:
                # Update local cache
                self._opportunity_cache["opportunities"] = opportunities
                self._opportunity_cache_times["opportunities"] = datetime.now().timestamp()
                
                # Store in memory batch
                async with self._memory_batch_lock:
                    self._memory_batch.append((
                        "opportunities",
                        opportunities,
                        self._cache_ttl
                    ))
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Failed to get opportunities: {e}")
            return []

    async def get_performance_metrics(self):
        """Get performance metrics with memory caching."""
        try:
            # Check local cache first
            metrics = self._metrics_cache.get("performance_metrics")
            if metrics is not None:
                return metrics
            
            # Try to get from memory with retries
            for attempt in range(MAX_RETRIES):
                try:
                    cached = self.memory.get_analytics("performance_metrics")
                    if cached:
                        # Update local cache
                        self._metrics_cache["performance_metrics"] = cached
                        self._metrics_cache_times["performance_metrics"] = datetime.now().timestamp()
                        return cached
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to get metrics from memory: {e}")
                    break

            # If not in memory, get fresh metrics
            metrics = await super().get_performance_metrics()
            
            if metrics:
                # Update local cache
                self._metrics_cache["performance_metrics"] = metrics
                self._metrics_cache_times["performance_metrics"] = datetime.now().timestamp()
                
                # Store in memory batch
                async with self._memory_batch_lock:
                    self._memory_batch.append((
                        "performance_metrics",
                        metrics,
                        self._cache_ttl
                    ))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return []

    async def _get_market_data_batch(self, tokens: List[str]) -> Dict[str, Any]:
        """Get market data for multiple tokens concurrently."""
        try:
            # Check local cache first
            market_data = {}
            for token in tokens:
                cache_key = f"market_data_{token}"
                data = self._market_cache.get(cache_key)
                if data is not None:
                    market_data[token] = data
                    continue
                
                # Try memory if not in local cache
                try:
                    cached = self.memory.get_market_data(cache_key)
                    if cached:
                        market_data[token] = cached
                        # Update local cache
                        self._market_cache[cache_key] = cached
                        self._market_cache_times[cache_key] = datetime.now().timestamp()
                        continue
                except Exception as e:
                    logger.debug(f"Failed to get market data from memory for {token}: {e}")
            
            # Get missing data concurrently
            missing_tokens = [t for t in tokens if t not in market_data]
            if missing_tokens:
                # Add to market batch
                async with self._market_batch_lock:
                    self._market_data_batch.extend(missing_tokens)
                    
                    # Process batch if full or timeout reached
                    current_time = datetime.now().timestamp()
                    if (len(self._market_data_batch) >= MAX_BATCH_SIZE or 
                        current_time - self._last_market_batch >= BATCH_TIMEOUT):
                        await self._process_market_batch()
                
                # Process missing tokens concurrently
                tasks = []
                for token in missing_tokens:
                    # Skip if recently processed
                    key = f"market_data_{token}"
                    if key in self._recent_market_data:
                        continue
                        
                    # Add to recent market data
                    self._recent_market_data.append(key)
                    
                    # Create task
                    task = asyncio.create_task(self._get_token_market_data(token))
                    tasks.append((token, task))
                
                # Wait for all tasks with retries
                for token, task in tasks:
                    for attempt in range(MAX_RETRIES):
                        try:
                            data = await task
                            if data:
                                market_data[token] = data
                                
                                # Update local cache
                                cache_key = f"market_data_{token}"
                                self._market_cache[cache_key] = data
                                self._market_cache_times[cache_key] = datetime.now().timestamp()
                                
                                # Store in memory batch
                                async with self._memory_batch_lock:
                                    self._memory_batch.append((
                                        cache_key,
                                        data,
                                        self._cache_ttl
                                    ))
                            break
                        except Exception as e:
                            if attempt < MAX_RETRIES - 1:
                                await asyncio.sleep(RETRY_DELAY)
                                continue
                            logger.error(f"Failed to get market data for {token} after {MAX_RETRIES} attempts: {e}")
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to get market data batch: {e}")
            return {}

    async def _get_token_market_data(self, token: str) -> Optional[Dict[str, Any]]:
        """Get market data for a single token."""
        try:
            # Get all metrics concurrently
            volume_task = asyncio.create_task(self._get_24h_volume(token))
            liquidity_task = asyncio.create_task(self._get_liquidity(token))
            volatility_task = asyncio.create_task(self._get_volatility(token))
            trend_task = asyncio.create_task(self._get_market_trend(token))
            strength_task = asyncio.create_task(self._get_trend_strength(token))
            impact_task = asyncio.create_task(self._get_price_impact(token))
            
            volume, liquidity, volatility, trend, strength, impact = await asyncio.gather(
                volume_task, liquidity_task, volatility_task,
                trend_task, strength_task, impact_task
            )
            
            return {
                "volume_24h": str(volume),
                "liquidity": str(liquidity),
                "volatility": str(volatility),
                "trend": trend,
                "trend_strength": str(strength),
                "price_impact": str(impact),
                "timestamp": datetime.now().timestamp()
            }
            
        except Exception as e:
            logger.error(f"Failed to get token market data: {e}")
            return None

    async def _periodic_memory_batch(self) -> None:
        """Periodically process memory batch."""
        try:
            while True:
                current_time = datetime.now().timestamp()
                if current_time - self._last_memory_batch >= BATCH_TIMEOUT:
                    await self._process_memory_batch()
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in periodic memory batch: {e}")

    async def _process_memory_batch(self) -> None:
        """Process memory batch."""
        try:
            async with self._memory_batch_lock:
                if not self._memory_batch:
                    return
                    
                # Process batch
                batch = self._memory_batch[:MAX_BATCH_SIZE]
                self._memory_batch = self._memory_batch[MAX_BATCH_SIZE:]
                self._last_memory_batch = datetime.now().timestamp()
                
                # Store in memory concurrently
                tasks = []
                for key, data, ttl in batch:
                    task = asyncio.create_task(self._store_in_memory(key, data, ttl))
                    tasks.append(task)
                
                await asyncio.gather(*tasks)
                
        except Exception as e:
            logger.error(f"Error processing memory batch: {e}")

    async def _store_in_memory(self, key: str, data: Any, ttl: int) -> None:
        """Store data in memory with retries."""
        try:
            for attempt in range(MAX_RETRIES):
                try:
                    if key.startswith("performance"):
                        self.memory.store_analytics(key, data, ttl=ttl)
                    else:
                        self.memory.store_market_data(key, data, ttl=ttl)
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to store {key} in memory after {MAX_RETRIES} attempts: {e}")
                    
        except Exception as e:
            logger.error(f"Error storing {key} in memory: {e}")

    async def _periodic_market_batch(self) -> None:
        """Periodically process market batch."""
        try:
            while True:
                current_time = datetime.now().timestamp()
                if current_time - self._last_market_batch >= BATCH_TIMEOUT:
                    await self._process_market_batch()
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in periodic market batch: {e}")

    async def _process_market_batch(self) -> None:
        """Process market data batch."""
        try:
            async with self._market_batch_lock:
                if not self._market_data_batch:
                    return
                    
                # Process batch
                batch = self._market_data_batch[:MAX_BATCH_SIZE]
                self._market_data_batch = self._market_data_batch[MAX_BATCH_SIZE:]
                self._last_market_batch = datetime.now().timestamp()
                
                # Process market data concurrently
                tasks = []
                for token in batch:
                    # Skip if recently processed
                    key = f"market_data_{token}"
                    if key in self._recent_market_data:
                        continue
                        
                    # Add to recent market data
                    self._recent_market_data.append(key)
                    
                    # Create task
                    task = asyncio.create_task(self._get_token_market_data(token))
                    tasks.append((token, task))
                
                # Wait for all tasks
                for token, task in tasks:
                    try:
                        data = await task
                        if data:
                            # Update local cache
                            cache_key = f"market_data_{token}"
                            self._market_cache[cache_key] = data
                            self._market_cache_times[cache_key] = datetime.now().timestamp()
                            
                            # Store in memory batch
                            async with self._memory_batch_lock:
                                self._memory_batch.append((
                                    cache_key,
                                    data,
                                    self._cache_ttl
                                ))
                    except Exception as e:
                        logger.error(f"Failed to process market data for {token}: {e}")
                
        except Exception as e:
            logger.error(f"Error processing market batch: {e}")

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
            market_size = len(self._market_cache)
            metrics_size = len(self._metrics_cache)
            opportunity_size = len(self._opportunity_cache)
            
            # Prefetch if below threshold
            if market_size < self._prefetch_size * self._prefetch_threshold:
                await self._prefetch_market_data()
                
            if metrics_size < self._prefetch_size * self._prefetch_threshold:
                await self._prefetch_metrics()
                
            if opportunity_size < self._prefetch_size * self._prefetch_threshold:
                await self._prefetch_opportunities()
                
        except Exception as e:
            logger.error(f"Error prefetching data: {e}")

    async def _prefetch_market_data(self) -> None:
        """Prefetch market data."""
        try:
            # Get tokens
            tokens = list(self.config['tokens'].keys())
            
            # Add to market batch
            async with self._market_batch_lock:
                self._market_data_batch.extend(tokens)
                
        except Exception as e:
            logger.error(f"Error prefetching market data: {e}")

    async def _prefetch_metrics(self) -> None:
        """Prefetch metrics data."""
        try:
            # Get fresh metrics
            metrics = await super().get_performance_metrics()
            
            if metrics:
                # Update local cache
                self._metrics_cache["performance_metrics"] = metrics
                self._metrics_cache_times["performance_metrics"] = datetime.now().timestamp()
                
                # Store in memory batch
                async with self._memory_batch_lock:
                    self._memory_batch.append((
                        "performance_metrics",
                        metrics,
                        self._cache_ttl
                    ))
                
        except Exception as e:
            logger.error(f"Error prefetching metrics: {e}")

    async def _prefetch_opportunities(self) -> None:
        """Prefetch opportunities data."""
        try:
            # Get fresh opportunities
            opportunities = await super().get_opportunities()
            
            if opportunities:
                # Update local cache
                self._opportunity_cache["opportunities"] = opportunities
                self._opportunity_cache_times["opportunities"] = datetime.now().timestamp()
                
                # Store in memory batch
                async with self._memory_batch_lock:
                    self._memory_batch.append((
                        "opportunities",
                        opportunities,
                        self._cache_ttl
                    ))
                
        except Exception as e:
            logger.error(f"Error prefetching opportunities: {e}")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            # Cancel periodic tasks
            tasks = [
                self._batch_task,
                self._market_task,
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
            await self._process_memory_batch()
            await self._process_market_batch()
            
            # Clear caches
            self._market_cache.clear()
            self._metrics_cache.clear()
            self._opportunity_cache.clear()
            self._market_cache_times.clear()
            self._metrics_cache_times.clear()
            self._opportunity_cache_times.clear()
            
            # Clear batches
            self._memory_batch.clear()
            self._market_data_batch.clear()
            
            # Clear recent market data
            self._recent_market_data.clear()
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            # Call parent cleanup
            await super().cleanup()
            
            logger.info("Memory-enabled market analyzer cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during memory analyzer cleanup: {e}")
            raise

async def create_memory_market_analyzer(web3_manager, config: Dict[str, Any]) -> MemoryEnabledMarketAnalyzer:
    """Create and initialize a memory-enabled market analyzer instance."""
    analyzer = MemoryEnabledMarketAnalyzer(web3_manager=web3_manager, config=config)
    await analyzer.start_monitoring()
    return analyzer
