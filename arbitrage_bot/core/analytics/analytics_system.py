"""Real-time analytics system for arbitrage operations."""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Set
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from collections import defaultdict

from ..web3.web3_manager import Web3Manager, create_web3_manager
from ..gas.gas_optimizer import GasOptimizer, create_gas_optimizer

logger = logging.getLogger(__name__)

# Cache settings
CACHE_TTL = 60  # 60 seconds
BATCH_SIZE = 50  # Process 50 items at a time
MAX_RETRIES = 3  # Maximum number of retries for failed operations
RETRY_DELAY = 1  # Delay between retries in seconds

class AnalyticsSystem:
    """Analytics system for real-time market analysis."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize analytics system."""
        self.config = config
        self.metrics = {}
        self.last_update = time.time()
        self.initialized = False
        self.web3_manager: Optional[Web3Manager] = None
        self.gas_optimizer: Optional[GasOptimizer] = None
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Cache settings
        self.cache_ttl = CACHE_TTL
        self.batch_size = BATCH_SIZE
        
        # Caches with TTL
        self._dex_instances = {}  # Cache for DEX instances
        self._dex_cache_times = {}  # Last update times for DEX instances
        self._metrics_cache = {}  # Cache for metrics
        self._metrics_cache_times = {}  # Last update times for metrics
        self._analysis_cache = {}  # Cache for analysis results
        self._analysis_cache_times = {}  # Last update times for analysis
        self._trade_cache = {}  # Cache for trade data
        self._trade_cache_times = {}  # Last update times for trade data
        
        # Locks for thread safety
        self._metrics_lock = asyncio.Lock()
        self._dex_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()
        self._analysis_lock = asyncio.Lock()
        self._trade_lock = asyncio.Lock()
        
        # Analytics batching
        self._analysis_batch = []
        self._last_analysis_batch = time.time()
        self._analysis_batch_lock = asyncio.Lock()
        
        # Start batch processing task
        self._batch_task = asyncio.create_task(self._periodic_analysis_batch())
        
        # Start cache cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cache_cleanup())

    async def initialize(self) -> bool:
        """Initialize analytics system."""
        try:
            # Initialize components concurrently
            init_tasks = [
                asyncio.create_task(self._init_web3()),
                asyncio.create_task(self._init_gas_optimizer())
            ]
            
            # Wait for initialization with retries
            for attempt in range(MAX_RETRIES):
                try:
                    results = await asyncio.gather(*init_tasks)
                    if not all(results):
                        raise ValueError("Failed to initialize components")
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to initialize after {MAX_RETRIES} attempts: {e}")
                    return False
            
            # Get initial metrics and clean caches concurrently
            await asyncio.gather(
                self._update_metrics(),
                self._cleanup_caches()
            )
            
            self.initialized = True
            logger.info(f"Analytics system initialized with wallet: {self.metrics.get('wallet_address')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize analytics system: {e}")
            return False

    async def _init_web3(self) -> bool:
        """Initialize Web3 manager."""
        try:
            self.web3_manager = await create_web3_manager(self.config)
            if not self.web3_manager.wallet_address:
                raise ValueError("No wallet address configured")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Web3 manager: {e}")
            return False

    async def _init_gas_optimizer(self) -> bool:
        """Initialize gas optimizer."""
        try:
            self.gas_optimizer = await create_gas_optimizer(
                web3_manager=self.web3_manager,
                dex_manager=None,
                min_gas_price=5000000000,
                max_gas_price=100000000000
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize gas optimizer: {e}")
            return False

    async def _update_metrics(self) -> None:
        """Update all metrics concurrently."""
        try:
            async with self._metrics_lock:
                # Run all updates concurrently
                update_tasks = {
                    'wallet': asyncio.create_task(self._update_wallet_info()),
                    'trades': asyncio.create_task(self._get_trade_metrics()),
                    'dex': asyncio.create_task(self._get_dex_metrics())
                }
                
                # Wait for all updates with retries
                results = {}
                for key, task in update_tasks.items():
                    for attempt in range(MAX_RETRIES):
                        try:
                            results[key] = await task
                            break
                        except Exception as e:
                            if attempt < MAX_RETRIES - 1:
                                await asyncio.sleep(RETRY_DELAY)
                                continue
                            logger.error(f"Error in {key} update after {MAX_RETRIES} attempts: {e}")
                            results[key] = None
                
                # Update metrics cache
                cache_key = 'metrics'
                self._metrics_cache[cache_key] = results
                self._metrics_cache_times[cache_key] = time.time()
                
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    async def _get_trade_metrics(self) -> Dict[str, Any]:
        """Get trade metrics concurrently."""
        try:
            # Check cache first
            cache_key = 'trade_metrics'
            metrics = await self._get_cached_data(
                cache_key,
                self._trade_cache,
                self._trade_cache_times
            )
            if metrics:
                return metrics
            
            # Get memory bank data
            from ..memory import get_memory_bank
            memory_bank = await get_memory_bank()
            
            # Get trade history and opportunities concurrently
            trade_history_task = asyncio.create_task(memory_bank.get_trade_history(max_age=86400))
            opportunities_task = asyncio.create_task(memory_bank.get_recent_opportunities(max_age=300))
            
            trade_history, opportunities = await asyncio.gather(trade_history_task, opportunities_task)
            
            if not trade_history:
                return self._empty_trade_metrics()
            
            # Process trades in batches concurrently
            current_time = time.time()
            trade_batches = [
                trade_history[i:i + self.batch_size]
                for i in range(0, len(trade_history), self.batch_size)
            ]
            
            # Process each batch in thread pool
            loop = asyncio.get_event_loop()
            batch_results = await asyncio.gather(*[
                loop.run_in_executor(
                    self.executor,
                    self._process_trade_batch,
                    batch,
                    current_time
                )
                for batch in trade_batches
            ])
            
            # Combine batch results
            total_trades = len(trade_history)
            successful_trades = sum(r['successful'] for r in batch_results)
            total_profit = sum(r['profit'] for r in batch_results)
            profit_24h = sum(r['profit_24h'] for r in batch_results)
            trades_24h = sum(r['trades_24h'] for r in batch_results)
            
            metrics = {
                'total_trades': total_trades,
                'trades_24h': trades_24h,
                'success_rate': successful_trades / total_trades if total_trades > 0 else 0,
                'total_profit_usd': float(total_profit),
                'portfolio_change_24h': float(profit_24h),
                'active_opportunities': len(opportunities) if opportunities else 0
            }
            
            # Update cache
            await self._update_cache(
                cache_key,
                metrics,
                self._trade_cache,
                self._trade_cache_times
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting trade metrics: {e}")
            return self._empty_trade_metrics()

    def _process_trade_batch(
        self,
        trades: List[Dict[str, Any]],
        current_time: float
    ) -> Dict[str, Any]:
        """Process a batch of trades (CPU-bound)."""
        try:
            successful = len([t for t in trades if t.get('profit', 0) > 0])
            total_profit = sum(t.get('profit', 0) for t in trades)
            recent_trades = [t for t in trades if current_time - t.get('timestamp', 0) <= 86400]
            profit_24h = sum(t.get('profit', 0) for t in recent_trades)
            
            return {
                'successful': successful,
                'profit': total_profit,
                'profit_24h': profit_24h,
                'trades_24h': len(recent_trades)
            }
            
        except Exception as e:
            logger.error(f"Error processing trade batch: {e}")
            return {
                'successful': 0,
                'profit': 0,
                'profit_24h': 0,
                'trades_24h': 0
            }

    def _empty_trade_metrics(self) -> Dict[str, Any]:
        """Return empty trade metrics structure."""
        return {
            'total_trades': 0,
            'trades_24h': 0,
            'success_rate': 0,
            'total_profit_usd': 0.0,
            'portfolio_change_24h': 0.0,
            'active_opportunities': 0
        }

    async def _get_dex_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get DEX metrics concurrently."""
        try:
            # Process DEXes in batches
            dex_names = [
                name for name, config in self.config['dexes'].items()
                if config.get('enabled', True)
            ]
            
            metrics = {}
            for i in range(0, len(dex_names), self.batch_size):
                batch = dex_names[i:i + self.batch_size]
                batch_tasks = []
                
                for dex_name in batch:
                    dex = await self._get_dex_instance(dex_name)
                    if not dex:
                        continue
                        
                    await dex.initialize()
                    
                    # Create tasks for metrics
                    task = asyncio.create_task(self._get_single_dex_metrics(dex))
                    batch_tasks.append((dex_name, task))
                
                # Wait for batch results with retries
                for dex_name, task in batch_tasks:
                    for attempt in range(MAX_RETRIES):
                        try:
                            dex_metrics = await task
                            if dex_metrics:
                                metrics[dex_name] = dex_metrics
                            break
                        except Exception as e:
                            if attempt < MAX_RETRIES - 1:
                                await asyncio.sleep(RETRY_DELAY)
                                continue
                            logger.error(f"Failed to get metrics for {dex_name} after {MAX_RETRIES} attempts: {e}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting DEX metrics: {e}")
            return {}

    async def _get_single_dex_metrics(self, dex) -> Optional[Dict[str, Any]]:
        """Get metrics for a single DEX."""
        try:
            # Get total liquidity
            liquidity = await dex.get_total_liquidity()
            
            # Get volume for WETH pairs as a representative sample
            weth_token = self.config.get('tokens', {}).get('WETH', {})
            usdc_token = self.config.get('tokens', {}).get('USDC', {})
            
            if weth_token and usdc_token and weth_token.get('address') and usdc_token.get('address'):
                volume = await dex.get_24h_volume(
                    self.web3_manager.w3.to_checksum_address(weth_token['address']),
                    self.web3_manager.w3.to_checksum_address(usdc_token['address'])
                )
            else:
                volume = Decimal(0)
            
            return {
                'active': True,
                'liquidity': float(liquidity) if liquidity else 0,
                'volume_24h': float(volume) if volume else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting single DEX metrics: {e}")
            return None

    async def _update_wallet_info(self):
        """Update wallet balance and related metrics."""
        if not self.web3_manager:
            return
            
        try:
            # Get wallet address
            wallet_address = self.web3_manager.wallet_address
            if not wallet_address:
                return
                
            # Run get_balance in executor to avoid blocking
            loop = asyncio.get_event_loop()
            balance = await loop.run_in_executor(
                self.executor,
                lambda: self.web3_manager.w3.eth.get_balance(wallet_address)
            )
            
            return {
                'wallet_balance': balance,
                'wallet_address': wallet_address
            }
            
        except Exception as e:
            logger.error(f"Error updating wallet balance: {e}")
            return None

    async def analyze_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze arbitrage opportunity concurrently."""
        try:
            # Add to analysis batch
            async with self._analysis_batch_lock:
                self._analysis_batch.append(opportunity)
                
            # Check cache first
            cache_key = f"analysis_{opportunity.get('token_in')}_{opportunity.get('token_out')}"
            analysis = await self._get_cached_data(
                cache_key,
                self._analysis_cache,
                self._analysis_cache_times
            )
            if analysis:
                return analysis
            
            # Get memory bank data
            from ..memory import get_memory_bank
            memory_bank = await get_memory_bank()
            trade_history = await memory_bank.get_trade_history(max_age=86400)
            
            if not trade_history:
                return self._empty_opportunity_analysis()
            
            # Process trades in thread pool
            loop = asyncio.get_event_loop()
            similar_trades = await loop.run_in_executor(
                self.executor,
                self._filter_similar_trades,
                trade_history,
                opportunity
            )
            
            if not similar_trades:
                return self._empty_opportunity_analysis()
            
            # Calculate metrics concurrently
            analysis_tasks = {
                'success': asyncio.create_task(self._calculate_success_rate(similar_trades)),
                'scores': asyncio.create_task(self._calculate_opportunity_scores(
                    opportunity,
                    similar_trades
                ))
            }
            
            # Wait for all analysis with retries
            results = {}
            for key, task in analysis_tasks.items():
                for attempt in range(MAX_RETRIES):
                    try:
                        results[key] = await task
                        break
                    except Exception as e:
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        logger.error(f"Error in opportunity analysis {key} after {MAX_RETRIES} attempts: {e}")
                        results[key] = None
            
            analysis = {
                'success_probability': results['success'],
                'priority': results['scores']['priority'] if results['scores'] else 0,
                'confidence': results['scores']['confidence'] if results['scores'] else 0
            }
            
            # Update cache
            await self._update_cache(
                cache_key,
                analysis,
                self._analysis_cache,
                self._analysis_cache_times
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing opportunity: {e}")
            return self._empty_opportunity_analysis()

    def _filter_similar_trades(
        self,
        trades: List[Dict[str, Any]],
        opportunity: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter similar trades (CPU-bound)."""
        return [t for t in trades if (
            t.get('token_in') == opportunity.get('token_in') and
            t.get('token_out') == opportunity.get('token_out')
        )]

    async def _calculate_success_rate(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate success rate from trades."""
        try:
            # Calculate in thread pool
            loop = asyncio.get_event_loop()
            success_rate = await loop.run_in_executor(
                self.executor,
                lambda: len([t for t in trades if t.get('profit', 0) > 0]) / len(trades)
                if trades else 0
            )
            return success_rate
            
        except Exception as e:
            logger.error(f"Error calculating success rate: {e}")
            return 0

    async def _calculate_opportunity_scores(
        self,
        opportunity: Dict[str, Any],
        trades: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate opportunity scores concurrently."""
        try:
            # Calculate scores in thread pool
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(
                self.executor,
                self._compute_scores,
                opportunity,
                trades,
                self.metrics.get('dex_metrics', {})
            )
            return scores
            
        except Exception as e:
            logger.error(f"Error calculating opportunity scores: {e}")
            return {'priority': 0, 'confidence': 0}

    def _compute_scores(
        self,
        opportunity: Dict[str, Any],
        trades: List[Dict[str, Any]],
        dex_metrics: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
        """Compute opportunity scores (CPU-bound)."""
        try:
            # Calculate priority based on profit potential
            priority = min(opportunity.get('profit_percent', 0), 0.5)
            
            # Get DEX metrics
            buy_dex = dex_metrics.get(opportunity.get('buy_dex', ''), {})
            sell_dex = dex_metrics.get(opportunity.get('sell_dex', ''), {})
            
            # Calculate scores
            liquidity_score = min(
                (buy_dex.get('liquidity', 0) + sell_dex.get('liquidity', 0)) / 2000000,
                1.0
            )
            volume_score = min(
                (buy_dex.get('volume_24h', 0) + sell_dex.get('volume_24h', 0)) / 1000000,
                1.0
            )
            
            # Calculate profit score
            avg_profit = sum(t.get('profit', 0) for t in trades) / len(trades) if trades else 0
            profit_score = min(avg_profit / 1000, 1.0)
            
            confidence = (liquidity_score + volume_score + profit_score) / 3
            
            return {
                'priority': priority,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Error computing scores: {e}")
            return {'priority': 0, 'confidence': 0}

    def _empty_opportunity_analysis(self) -> Dict[str, float]:
        """Return empty opportunity analysis structure."""
        return {
            'success_probability': 0,
            'priority': 0,
            'confidence': 0
        }

    async def _get_dex_instance(self, dex_name: str):
        """Get or create DEX instance from cache with TTL."""
        current_time = time.time()
        
        async with self._dex_lock:
            # Check cache with TTL
            if dex_name in self._dex_instances:
                last_update = self._dex_cache_times.get(dex_name, 0)
                if current_time - last_update < self.cache_ttl:
                    return self._dex_instances[dex_name]
            
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
                    self._dex_instances[dex_name] = instance
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
                # Clean up DEX cache
                expired_dexes = [
                    name for name, last_update in self._dex_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for name in expired_dexes:
                    del self._dex_instances[name]
                    del self._dex_cache_times[name]
                
                # Clean up metrics cache
                expired_metrics = [
                    key for key, last_update in self._metrics_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_metrics:
                    del self._metrics_cache[key]
                    del self._metrics_cache_times[key]
                
                # Clean up analysis cache
                expired_analysis = [
                    key for key, last_update in self._analysis_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_analysis:
                    del self._analysis_cache[key]
                    del self._analysis_cache_times[key]
                
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

    async def _periodic_analysis_batch(self) -> None:
        """Periodically process analysis batch."""
        try:
            while True:
                if time.time() - self._last_analysis_batch > 5:  # Process every 5 seconds
                    await self._process_analysis_batch()
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in periodic analysis batch: {e}")

    async def _process_analysis_batch(self) -> None:
        """Process analysis batch."""
        try:
            async with self._analysis_batch_lock:
                if not self._analysis_batch:
                    return
                    
                # Process batch
                batch = self._analysis_batch
                self._analysis_batch = []
                self._last_analysis_batch = time.time()
                
                # Analyze opportunities concurrently
                tasks = [
                    asyncio.create_task(self.analyze_opportunity(opp))
                    for opp in batch
                ]
                
                await asyncio.gather(*tasks)
                
        except Exception as e:
            logger.error(f"Error processing analysis batch: {e}")

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

    async def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update analytics metrics."""
        try:
            async with self._metrics_lock:
                await self._update_metrics()
                self.metrics.update(metrics)
                
                # Update cache
                cache_key = 'metrics'
                self._metrics_cache[cache_key] = self.metrics.copy()
                self._metrics_cache_times[cache_key] = time.time()
                
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current analytics metrics."""
        try:
            # Check cache first
            cache_key = 'metrics'
            metrics = await self._get_cached_data(
                cache_key,
                self._metrics_cache,
                self._metrics_cache_times
            )
            if metrics:
                return metrics
            
            # Update metrics if cache miss
            await self._update_metrics()
            return self.metrics
            
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {}

    async def get_performance_metrics(self) -> list:
        """Get performance metrics for dashboard."""
        metrics = await self.get_metrics()
        return [metrics]

    async def set_dex_manager(self, dex_manager) -> None:
        """Set DEX manager for gas optimizer."""
        if self.gas_optimizer:
            self.gas_optimizer.dex_manager = dex_manager

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
            
            # Process any remaining batches
            await self._process_analysis_batch()
            
            # Clear caches
            self._dex_instances.clear()
            self._metrics_cache.clear()
            self._analysis_cache.clear()
            self._trade_cache.clear()
            self._dex_cache_times.clear()
            self._metrics_cache_times.clear()
            self._analysis_cache_times.clear()
            self._trade_cache_times.clear()
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            logger.info("Analytics system cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during analytics system cleanup: {e}")
            raise

async def create_analytics_system(config: Dict[str, Any]) -> AnalyticsSystem:
    """Create and initialize a new AnalyticsSystem instance."""
    analytics = AnalyticsSystem(config)
    await analytics.initialize()
    return analytics

# Export the create function
__all__ = ['create_analytics_system']
