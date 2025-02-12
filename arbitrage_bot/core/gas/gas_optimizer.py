"""Gas optimization system."""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime, timedelta
import statistics
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..dex.dex_manager import DEXManager
    from ..web3.web3_manager import Web3Manager

# Gas cost constants
GAS_COSTS = {
    'v2': {
        'base_cost': 100000,  # Base cost for v2 protocol
        'hop_cost': 50000,    # Additional cost per hop for v2
        'buffer': 1.2         # Safety buffer for v2 gas estimates
    },
    'v3': {
        'base_cost': 150000,  # Base cost for v3 protocol
        'hop_cost': 75000,    # Additional cost per hop for v3
        'buffer': 1.3         # Safety buffer for v3 gas estimates
    }
}

# Cache settings
CACHE_TTL = 60  # 60 seconds
BATCH_SIZE = 50  # Process 50 items at a time
MAX_RETRIES = 3  # Maximum number of retries for failed operations
RETRY_DELAY = 1  # Delay between retries in seconds

logger = logging.getLogger(__name__)

class GasOptimizer:
    """Optimizes gas usage for arbitrage trades."""

    def __init__(
        self,
        dex_manager: 'DEXManager',
        web3_manager: Optional['Web3Manager'] = None,
        base_gas_limit: int = 500000,  # 500k gas units
        max_gas_price: int = 100000000000,  # 100 gwei
        min_gas_price: int = 5000000000,  # 5 gwei
        gas_price_buffer: float = 1.1,  # 10% buffer
        gas_history_window: int = 200  # blocks
    ):
        """Initialize gas optimizer."""
        self.dex_manager = dex_manager
        self.web3_manager = web3_manager
        self.base_gas_limit = base_gas_limit
        self.max_gas_price = max_gas_price
        self.min_gas_price = min_gas_price
        self.gas_price_buffer = gas_price_buffer
        self.gas_history_window = gas_history_window
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Gas price history
        self.gas_prices: List[int] = []
        self.last_update = datetime.min
        
        # Gas usage statistics
        self.dex_gas_stats: Dict[str, Dict[str, Any]] = {}
        self.protocol_gas_stats = {
            'v2': {'base': GAS_COSTS['v2']['base_cost'], 'hop': GAS_COSTS['v2']['hop_cost']},
            'v3': {'base': GAS_COSTS['v3']['base_cost'], 'hop': GAS_COSTS['v3']['hop_cost']}
        }
        
        # Cache settings
        self.cache_ttl = CACHE_TTL
        self.batch_size = BATCH_SIZE
        
        # Caches with TTL
        self._web3_cache = {}  # Cache for Web3 data
        self._gas_estimate_cache = {}  # Cache for gas estimates
        self._dex_stats_cache = {}  # Cache for DEX stats
        self._path_cache = {}  # Cache for path calculations
        self._price_cache = {}  # Cache for gas prices
        
        # Cache timestamps
        self._web3_cache_times = {}
        self._gas_estimate_cache_times = {}
        self._dex_stats_cache_times = {}
        self._path_cache_times = {}
        self._price_cache_times = {}
        
        # Locks for thread safety
        self._cache_lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        self._history_lock = asyncio.Lock()
        self._path_lock = asyncio.Lock()
        self._price_lock = asyncio.Lock()
        
        # Batch processing
        self._path_batch = []
        self._last_path_batch = time.time()
        self._path_batch_lock = asyncio.Lock()
        
        # Start cache cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cache_cleanup())
        
        # Start path batch task
        self._batch_task = asyncio.create_task(self._periodic_path_batch())

    async def initialize(self) -> bool:
        """Initialize gas optimizer."""
        try:
            # Update initial gas history and clean caches concurrently
            init_tasks = [
                asyncio.create_task(self._update_gas_history()),
                asyncio.create_task(self._cleanup_caches())
            ]
            await asyncio.gather(*init_tasks)
            
            logger.info("Gas optimizer initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize gas optimizer: {e}")
            return False

    async def get_optimal_gas_price(self) -> int:
        """Get optimal gas price based on network conditions."""
        try:
            # Check cache first
            cache_key = 'optimal_price'
            price = await self._get_cached_data(
                cache_key,
                self._price_cache,
                self._price_cache_times
            )
            if price is not None:
                return price
            
            # Update gas price history
            await self._update_gas_history()
            
            if not self.gas_prices:
                return self.min_gas_price
            
            # Calculate optimal price in thread pool
            loop = asyncio.get_event_loop()
            optimal_price = await loop.run_in_executor(
                self.executor,
                self._calculate_optimal_price
            )
            
            # Update cache
            await self._update_cache(
                cache_key,
                optimal_price,
                self._price_cache,
                self._price_cache_times
            )
            
            return optimal_price
            
        except Exception as e:
            logger.error(f"Error getting optimal gas price: {e}")
            return self.min_gas_price

    def _calculate_optimal_price(self) -> int:
        """Calculate optimal gas price (CPU-bound)."""
        try:
            recent_prices = self.gas_prices[-20:]  # Last 20 blocks
            median_price = statistics.median(recent_prices)
            
            # Add buffer for safety
            optimal_price = int(median_price * self.gas_price_buffer)
            
            # Ensure within bounds
            return max(self.min_gas_price, min(self.max_gas_price, optimal_price))
            
        except Exception as e:
            logger.error(f"Error calculating optimal price: {e}")
            return self.min_gas_price

    async def estimate_gas_limits(
        self,
        paths: List[Dict[str, Any]]
    ) -> List[int]:
        """Estimate gas limits for multiple paths concurrently."""
        try:
            # Process paths in batches
            gas_limits = []
            for i in range(0, len(paths), self.batch_size):
                batch = paths[i:i + self.batch_size]
                
                # Process batch in thread pool
                loop = asyncio.get_event_loop()
                batch_tasks = [
                    loop.run_in_executor(
                        self.executor,
                        self._estimate_single_path,
                        path['dex_name'],
                        path['path'],
                        'v3' if 'quoter' in path else 'v2'
                    )
                    for path in batch
                ]
                
                # Wait for batch results
                batch_results = await asyncio.gather(*batch_tasks)
                gas_limits.extend(batch_results)
            
            return gas_limits
            
        except Exception as e:
            logger.error(f"Error estimating gas limits: {e}")
            return [self.base_gas_limit] * len(paths)

    def _estimate_single_path(
        self,
        dex_name: str,
        path: List[str],
        protocol: str = 'v2'
    ) -> int:
        """Estimate gas limit for a single path (CPU-bound)."""
        try:
            # Get base costs for protocol
            protocol_stats = self.protocol_gas_stats[protocol]
            base_cost = protocol_stats['base']
            hop_cost = protocol_stats['hop']
            
            # Calculate path cost
            path_length = len(path)
            path_cost = base_cost + (hop_cost * (path_length - 1))
            
            # Add DEX-specific adjustment
            dex_stats = self.dex_gas_stats.get(dex_name, {})
            adjustment = dex_stats.get('adjustment', 1.0)
            
            # Calculate final limit with safety buffer
            gas_limit = int(path_cost * adjustment * GAS_COSTS[protocol]['buffer'])
            
            # Ensure within bounds
            return min(gas_limit, self.base_gas_limit)
            
        except Exception as e:
            logger.error(f"Error estimating single path gas: {e}")
            return self.base_gas_limit

    async def update_gas_stats_batch(
        self,
        updates: List[Tuple[str, str, int, int]]
    ) -> None:
        """Update gas usage statistics for multiple trades concurrently."""
        try:
            # Process updates in batches
            for i in range(0, len(updates), self.batch_size):
                batch = updates[i:i + self.batch_size]
                
                # Process batch in thread pool
                loop = asyncio.get_event_loop()
                batch_tasks = [
                    loop.run_in_executor(
                        self.executor,
                        self._update_single_dex_stats,
                        dex_name,
                        protocol,
                        actual_gas,
                        path_length
                    )
                    for dex_name, protocol, actual_gas, path_length in batch
                ]
                
                await asyncio.gather(*batch_tasks)
                
            # Clean up caches after updates
            await self._cleanup_caches()
                
        except Exception as e:
            logger.error(f"Error updating gas stats batch: {e}")

    def _update_single_dex_stats(
        self,
        dex_name: str,
        protocol: str,
        actual_gas: int,
        path_length: int
    ) -> None:
        """Update gas stats for a single DEX (CPU-bound)."""
        try:
            # Initialize DEX stats if needed
            if dex_name not in self.dex_gas_stats:
                self.dex_gas_stats[dex_name] = {
                    'total_trades': 0,
                    'total_gas': 0,
                    'avg_gas': 0,
                    'adjustment': 1.0
                }
            
            stats = self.dex_gas_stats[dex_name]
            
            # Update running averages
            stats['total_trades'] += 1
            stats['total_gas'] += actual_gas
            stats['avg_gas'] = stats['total_gas'] / stats['total_trades']
            
            # Calculate expected gas
            protocol_stats = self.protocol_gas_stats[protocol]
            expected_gas = protocol_stats['base'] + (protocol_stats['hop'] * (path_length - 1))
            
            # Update adjustment factor
            if expected_gas > 0:
                current_ratio = actual_gas / expected_gas
                stats['adjustment'] = (
                    (stats['adjustment'] * (stats['total_trades'] - 1) + current_ratio) /
                    stats['total_trades']
                )
            
        except Exception as e:
            logger.error(f"Error updating single DEX stats: {e}")

    async def optimize_path_gas(
        self,
        paths: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Optimize gas usage across multiple paths concurrently."""
        try:
            # Get gas estimates and price concurrently
            gas_price_task = asyncio.create_task(self.get_optimal_gas_price())
            gas_limits_task = asyncio.create_task(self.estimate_gas_limits(paths))
            
            gas_price, gas_limits = await asyncio.gather(gas_price_task, gas_limits_task)
            
            # Update paths with gas info in thread pool
            loop = asyncio.get_event_loop()
            optimized = await loop.run_in_executor(
                self.executor,
                self._update_paths_with_gas,
                paths,
                gas_limits,
                gas_price
            )
            
            return optimized
            
        except Exception as e:
            logger.error(f"Error optimizing path gas: {e}")
            return paths

    def _update_paths_with_gas(
        self,
        paths: List[Dict[str, Any]],
        gas_limits: List[int],
        gas_price: int
    ) -> List[Dict[str, Any]]:
        """Update paths with gas information (CPU-bound)."""
        try:
            optimized = []
            for path, gas_limit in zip(paths, gas_limits):
                # Calculate gas cost
                gas_cost = gas_limit * gas_price
                
                # Update path
                path_copy = path.copy()
                path_copy.update({
                    'gas_limit': gas_limit,
                    'gas_price': gas_price,
                    'gas_cost': gas_cost
                })
                
                optimized.append(path_copy)
            
            return optimized
            
        except Exception as e:
            logger.error(f"Error updating paths with gas: {e}")
            return paths

    async def analyze_gas_usage(self) -> Dict[str, Any]:
        """Analyze gas usage patterns concurrently."""
        try:
            # Run analysis components concurrently
            analysis_tasks = {
                'gas_price': asyncio.create_task(self.get_optimal_gas_price()),
                'recommendations': asyncio.create_task(self._generate_recommendations())
            }
            
            # Wait for all analysis
            results = {}
            for key, task in analysis_tasks.items():
                try:
                    results[key] = await task
                except Exception as e:
                    logger.error(f"Error in {key} analysis: {e}")
                    results[key] = None
            
            return {
                'current_gas_price': results['gas_price'],
                'dex_stats': self.dex_gas_stats.copy(),
                'protocol_stats': self.protocol_gas_stats.copy(),
                'recommendations': results['recommendations'] or []
            }
            
        except Exception as e:
            logger.error(f"Error analyzing gas usage: {e}")
            return {
                'current_gas_price': self.min_gas_price,
                'dex_stats': {},
                'protocol_stats': {},
                'recommendations': [f"Error analyzing gas usage: {e}"]
            }

    async def _generate_recommendations(self) -> List[str]:
        """Generate gas usage recommendations concurrently."""
        try:
            # Generate recommendations in thread pool
            loop = asyncio.get_event_loop()
            recommendations = await loop.run_in_executor(
                self.executor,
                self._analyze_gas_patterns
            )
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return [f"Error generating recommendations: {e}"]

    def _analyze_gas_patterns(self) -> List[str]:
        """Analyze gas patterns for recommendations (CPU-bound)."""
        try:
            recommendations = []
            
            # Check DEX adjustments
            for dex_name, stats in self.dex_gas_stats.items():
                if stats['adjustment'] > 1.2:  # Using 20% more gas than expected
                    recommendations.append(
                        f"{dex_name} using {(stats['adjustment'] - 1) * 100:.1f}% more gas "
                        "than expected. Consider reviewing path optimization."
                    )
            
            # Check gas prices
            if self.gas_prices:
                avg_price = sum(self.gas_prices) / len(self.gas_prices)
                if avg_price > self.max_gas_price * 0.8:  # Within 20% of max
                    recommendations.append(
                        "Network gas prices approaching maximum threshold. "
                        "Consider adjusting trading thresholds."
                    )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error analyzing gas patterns: {e}")
            return [f"Error analyzing gas patterns: {e}"]

    async def _update_gas_history(self) -> None:
        """Update gas price history with caching."""
        try:
            now = datetime.now()
            if (now - self.last_update) < timedelta(seconds=15):
                return
                
            async with self._history_lock:
                # Get current gas price
                current_gas = await self._get_cached_gas_price()
                
                # Update gas price history
                if not self.gas_prices:
                    self.gas_prices = [current_gas] * self.gas_history_window
                else:
                    self.gas_prices = self.gas_prices[1:] + [current_gas]
                
                self.last_update = now
            
        except Exception as e:
            logger.error(f"Error updating gas history: {e}")

    async def _get_cached_gas_price(self) -> int:
        """Get gas price from cache or fetch if needed."""
        try:
            # Check cache first
            cache_key = 'gas_price'
            price = await self._get_cached_data(
                cache_key,
                self._web3_cache,
                self._web3_cache_times
            )
            if price is not None:
                return price
            
            # Fetch new price with retries
            for attempt in range(MAX_RETRIES):
                try:
                    price = await self._fetch_gas_price()
                    
                    # Update cache
                    await self._update_cache(
                        cache_key,
                        price,
                        self._web3_cache,
                        self._web3_cache_times
                    )
                    
                    return price
                    
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to get gas price after {MAX_RETRIES} attempts: {e}")
                    return self.min_gas_price
                    
        except Exception as e:
            logger.error(f"Error getting cached gas price: {e}")
            return self.min_gas_price

    async def _fetch_gas_price(self) -> int:
        """Fetch current gas price from Web3."""
        try:
            w3 = self.get_web3_instance()
            if not w3:
                raise ValueError("No Web3 instance available")
                
            # Run gas_price in executor to avoid blocking
            loop = asyncio.get_event_loop()
            current_gas = await loop.run_in_executor(
                self.executor,
                lambda: w3.eth.gas_price
            )
            
            return current_gas
            
        except Exception as e:
            logger.error(f"Failed to get gas price: {e}")
            return self.min_gas_price

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

    async def _periodic_cache_cleanup(self) -> None:
        """Periodically clean up caches."""
        try:
            while True:
                await self._cleanup_caches()
                await asyncio.sleep(self.cache_ttl / 2)  # Clean up every half TTL
        except Exception as e:
            logger.error(f"Error in periodic cache cleanup: {e}")

    async def _cleanup_caches(self) -> None:
        """Clean up expired cache entries."""
        try:
            current_time = time.time()
            
            async with self._cache_lock:
                # Clean up Web3 cache
                expired_web3 = [
                    key for key, last_update in self._web3_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_web3:
                    del self._web3_cache[key]
                    del self._web3_cache_times[key]
                
                # Clean up gas estimate cache
                expired_estimates = [
                    key for key, last_update in self._gas_estimate_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_estimates:
                    del self._gas_estimate_cache[key]
                    del self._gas_estimate_cache_times[key]
                
                # Clean up DEX stats cache
                expired_stats = [
                    key for key, last_update in self._dex_stats_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_stats:
                    del self._dex_stats_cache[key]
                    del self._dex_stats_cache_times[key]
                
                # Clean up path cache
                expired_paths = [
                    key for key, last_update in self._path_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_paths:
                    del self._path_cache[key]
                    del self._path_cache_times[key]
                
                # Clean up price cache
                expired_prices = [
                    key for key, last_update in self._price_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_prices:
                    del self._price_cache[key]
                    del self._price_cache_times[key]
                    
        except Exception as e:
            logger.error(f"Error cleaning up caches: {e}")

    async def _periodic_path_batch(self) -> None:
        """Periodically process path batch."""
        try:
            while True:
                if time.time() - self._last_path_batch > 5:  # Process every 5 seconds
                    await self._process_path_batch()
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in periodic path batch: {e}")

    async def _process_path_batch(self) -> None:
        """Process path batch."""
        try:
            async with self._path_batch_lock:
                if not self._path_batch:
                    return
                    
                # Process paths in batch
                paths = self._path_batch
                self._path_batch = []
                self._last_path_batch = time.time()
                
                await self.optimize_path_gas(paths)
                
        except Exception as e:
            logger.error(f"Error processing path batch: {e}")

    def get_web3_instance(self) -> Optional[Any]:
        """Get Web3 instance from available sources."""
        try:
            if self.web3_manager and hasattr(self.web3_manager, 'w3') and self.web3_manager.w3:
                return self.web3_manager.w3
        except Exception as e:
            logger.debug(f"Failed to get w3 from web3_manager: {e}")

        try:
            if self.dex_manager and hasattr(self.dex_manager, 'web3_manager'):
                web3_manager = self.dex_manager.web3_manager
                if hasattr(web3_manager, 'w3') and web3_manager.w3:
                    return web3_manager.w3
        except Exception as e:
            logger.debug(f"Failed to get w3 from dex_manager.web3_manager: {e}")

        logger.warning("No valid Web3 instance found")
        return None

    def get_dex_gas_stats(self, dex_name: str) -> Optional[Dict[str, Any]]:
        """Get gas statistics for a specific DEX."""
        return self.dex_gas_stats.get(dex_name)

    def get_protocol_gas_stats(self, protocol: str) -> Optional[Dict[str, Any]]:
        """Get gas statistics for a specific protocol."""
        return self.protocol_gas_stats.get(protocol)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            # Cancel periodic tasks
            if hasattr(self, '_cleanup_task'):
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            if hasattr(self, '_batch_task'):
                self._batch_task.cancel()
                try:
                    await self._batch_task
                except asyncio.CancelledError:
                    pass
            
            # Clear caches
            self._web3_cache.clear()
            self._gas_estimate_cache.clear()
            self._dex_stats_cache.clear()
            self._path_cache.clear()
            self._price_cache.clear()
            self._web3_cache_times.clear()
            self._gas_estimate_cache_times.clear()
            self._dex_stats_cache_times.clear()
            self._path_cache_times.clear()
            self._price_cache_times.clear()
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            logger.info("Gas optimizer cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during gas optimizer cleanup: {e}")
            raise

async def create_gas_optimizer(
    dex_manager: Optional['DEXManager'] = None,
    web3_manager: Optional['Web3Manager'] = None,
    base_gas_limit: int = 500000,
    max_gas_price: int = 100000000000,
    min_gas_price: int = 5000000000,
    gas_price_buffer: float = 1.1,
    gas_history_window: int = 200
) -> GasOptimizer:
    """Create and initialize gas optimizer instance."""
    if not dex_manager:
        logger.warning("No dex_manager provided, gas optimizer may have limited functionality")

    # If no web3_manager provided, try to get it from dex_manager
    if not web3_manager and dex_manager:
        try:
            web3_manager = dex_manager.web3_manager
            if not web3_manager or not hasattr(web3_manager, 'w3') or not web3_manager.w3:
                logger.warning("No valid web3_manager available from dex_manager")
                web3_manager = None
        except Exception as e:
            logger.error(f"Error accessing web3_manager from dex_manager: {e}")
            web3_manager = None

    optimizer = GasOptimizer(
        dex_manager=dex_manager,
        web3_manager=web3_manager,
        base_gas_limit=base_gas_limit,
        max_gas_price=max_gas_price,
        min_gas_price=min_gas_price,
        gas_price_buffer=gas_price_buffer,
        gas_history_window=gas_history_window
    )
    
    await optimizer.initialize()
    return optimizer

# Export the create function
__all__ = ['create_gas_optimizer']
