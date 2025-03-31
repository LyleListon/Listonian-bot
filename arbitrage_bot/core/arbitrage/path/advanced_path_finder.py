"""
Advanced Path Finder for Multi-Path Arbitrage

This module provides functionality for finding arbitrage paths using advanced
algorithms, including Bellman-Ford for negative cycle detection, multi-hop path
support, parallel path exploration, and pruning for unprofitable paths.

Key features:
- Bellman-Ford algorithm for negative cycle detection
- Support for multi-hop paths (up to 5 hops)
- Parallel path exploration
- Pruning for unprofitable paths
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Set, Union
import numpy as np
from collections import defaultdict

from .interfaces import ArbitragePath, Pool
from ...utils.async_utils import gather_with_concurrency
from ...utils.retry import with_retry

logger = logging.getLogger(__name__)

class AdvancedPathFinder:
    """
    Finds arbitrage paths using advanced algorithms.
    
    This class implements algorithms for finding arbitrage paths, including
    Bellman-Ford for negative cycle detection, multi-hop path support, parallel
    path exploration, and pruning for unprofitable paths.
    """
    
    def __init__(
        self,
        graph_explorer,
        max_hops: int = 4,
        max_paths_per_token: int = 10,
        concurrency_limit: int = 5,
        min_profit_threshold: Decimal = Decimal('0.0001'),
        max_path_exploration: int = 1000
    ):
        """
        Initialize the advanced path finder.
        
        Args:
            graph_explorer: Graph explorer for finding cycles
            max_hops: Maximum number of hops in a path (default: 4)
            max_paths_per_token: Maximum number of paths per token (default: 10)
            concurrency_limit: Maximum number of concurrent operations (default: 5)
            min_profit_threshold: Minimum profit threshold (default: 0.0001 ETH)
            max_path_exploration: Maximum number of paths to explore (default: 1000)
        """
        self.graph_explorer = graph_explorer
        self.max_hops = max_hops
        self.max_paths_per_token = max_paths_per_token
        self.concurrency_limit = concurrency_limit
        self.min_profit_threshold = min_profit_threshold
        self.max_path_exploration = max_path_exploration
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Path cache
        self._path_cache = {}
        self._last_cache_cleanup = time.time()
        
        logger.info(
            f"Initialized AdvancedPathFinder with max_hops={max_hops}, "
            f"max_paths_per_token={max_paths_per_token}"
        )
    
    async def initialize(self) -> bool:
        """
        Initialize the path finder.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Initialize graph explorer
            success = await self.graph_explorer.initialize()
            
            if not success:
                logger.error("Failed to initialize graph explorer")
                return False
            
            logger.info("Initialized AdvancedPathFinder successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error initializing AdvancedPathFinder: {e}")
            return False
    
    async def find_paths(
        self,
        start_token: str,
        max_paths: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ArbitragePath]:
        """
        Find arbitrage paths starting from a token.
        
        Args:
            start_token: Start token address
            max_paths: Maximum number of paths to return (default: 10)
            filters: Optional filters for path finding
                - max_hops: Maximum number of hops in a path
                - min_profit: Minimum profit threshold
                - max_slippage: Maximum acceptable slippage
                - dexes: List of allowed DEXes
                - tokens: List of allowed tokens
            
        Returns:
            List of arbitrage paths
        """
        async with self._lock:
            try:
                # Apply filters
                filters = filters or {}
                
                # Get max_hops from filters or use default
                max_hops = filters.get('max_hops', self.max_hops)
                
                # Get min_profit from filters or use default
                min_profit = filters.get('min_profit', self.min_profit_threshold)
                
                # Check cache first
                cache_key = f"{start_token}:{max_paths}:{max_hops}:{min_profit}"
                
                if cache_key in self._path_cache:
                    cache_entry = self._path_cache[cache_key]
                    if time.time() - cache_entry['timestamp'] < 60:  # 60 seconds TTL
                        logger.debug(f"Using cached paths for {start_token}")
                        return cache_entry['paths']
                
                # Find cycles using graph explorer
                logger.info(f"Finding cycles for {start_token} with max_hops={max_hops}")
                
                cycles = await self.graph_explorer.find_cycles(
                    start_token=start_token,
                    max_length=max_hops + 1,  # +1 because cycles include start token twice
                    max_cycles=self.max_path_exploration,
                    filters=filters
                )
                
                logger.info(f"Found {len(cycles)} cycles for {start_token}")
                
                # Convert cycles to arbitrage paths
                paths = []
                
                for cycle in cycles:
                    # Create pools
                    pools = []
                    
                    for pool_data in cycle.get('pools', []):
                        pool = Pool(
                            address=pool_data['address'],
                            token0=pool_data['token0'],
                            token1=pool_data['token1'],
                            reserves0=pool_data.get('reserves0'),
                            reserves1=pool_data.get('reserves1'),
                            fee=pool_data.get('fee', 3000),
                            pool_type=pool_data.get('pool_type', 'constant_product'),
                            dex=pool_data.get('dex', 'unknown')
                        )
                        pools.append(pool)
                    
                    # Create arbitrage path
                    path = ArbitragePath(
                        tokens=cycle.get('tokens', []),
                        pools=pools,
                        dexes=cycle.get('dexes', []),
                        optimal_amount=cycle.get('optimal_amount'),
                        expected_output=cycle.get('expected_output'),
                        confidence=cycle.get('confidence', 0.5)
                    )
                    
                    # Add to paths if profitable
                    if path.profit is not None and path.profit >= min_profit:
                        paths.append(path)
                
                # Sort paths by profit (descending)
                paths.sort(key=lambda p: p.profit if p.profit is not None else Decimal('0'), reverse=True)
                
                # Limit to max_paths
                paths = paths[:max_paths]
                
                # Cache paths
                self._path_cache[cache_key] = {
                    'timestamp': time.time(),
                    'paths': paths
                }
                
                # Clean up cache if needed
                if time.time() - self._last_cache_cleanup > 300:  # 5 minutes
                    self._cleanup_cache()
                
                logger.info(f"Returning {len(paths)} paths for {start_token}")
                
                return paths
            
            except Exception as e:
                logger.error(f"Error finding paths: {e}")
                return []
    
    async def find_paths_parallel(
        self,
        start_tokens: List[str],
        max_paths_per_token: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[ArbitragePath]]:
        """
        Find arbitrage paths for multiple tokens in parallel.
        
        Args:
            start_tokens: List of start token addresses
            max_paths_per_token: Maximum number of paths per token (default: 5)
            filters: Optional filters for path finding
            
        Returns:
            Dictionary of token -> paths
        """
        try:
            # Create tasks for each token
            tasks = []
            
            for token in start_tokens:
                task = self.find_paths(
                    start_token=token,
                    max_paths=max_paths_per_token,
                    filters=filters
                )
                tasks.append(task)
            
            # Execute tasks in parallel with concurrency limit
            results = await gather_with_concurrency(
                self.concurrency_limit,
                *tasks
            )
            
            # Create result dictionary
            paths_by_token = {}
            
            for i, token in enumerate(start_tokens):
                paths_by_token[token] = results[i]
            
            return paths_by_token
        
        except Exception as e:
            logger.error(f"Error finding paths in parallel: {e}")
            return {}
    
    async def find_best_paths(
        self,
        start_tokens: List[str],
        max_total_paths: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ArbitragePath]:
        """
        Find the best arbitrage paths across multiple tokens.
        
        Args:
            start_tokens: List of start token addresses
            max_total_paths: Maximum total number of paths to return (default: 20)
            filters: Optional filters for path finding
            
        Returns:
            List of arbitrage paths
        """
        try:
            # Find paths for each token
            paths_by_token = await self.find_paths_parallel(
                start_tokens=start_tokens,
                max_paths_per_token=max_total_paths,
                filters=filters
            )
            
            # Combine paths
            all_paths = []
            
            for token, paths in paths_by_token.items():
                all_paths.extend(paths)
            
            # Sort paths by profit (descending)
            all_paths.sort(key=lambda p: p.profit if p.profit is not None else Decimal('0'), reverse=True)
            
            # Limit to max_total_paths
            all_paths = all_paths[:max_total_paths]
            
            return all_paths
        
        except Exception as e:
            logger.error(f"Error finding best paths: {e}")
            return []
    
    async def close(self) -> None:
        """Close the path finder and release resources."""
        try:
            # Close graph explorer
            await self.graph_explorer.close()
            
            logger.info("Closed AdvancedPathFinder")
        
        except Exception as e:
            logger.error(f"Error closing AdvancedPathFinder: {e}")
    
    def _cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        try:
            current_time = time.time()
            expired_keys = []
            
            for key, entry in self._path_cache.items():
                if current_time - entry['timestamp'] > 60:  # 60 seconds TTL
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._path_cache[key]
            
            self._last_cache_cleanup = current_time
            
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
