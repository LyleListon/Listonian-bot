"""Memory bank for storing and retrieving arbitrage opportunities and trade results."""

import logging
import asyncio
import time
import os
import json
import zlib
from typing import Dict, List, Any, Optional
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple, defaultdict
import lru

from ..models.opportunity import Opportunity

logger = logging.getLogger(__name__)

async def create_memory_bank(config: Optional[Dict[str, Any]] = None) -> 'MemoryBank':
    """Create and initialize a memory bank instance."""
    memory_bank = MemoryBank()
    success = await memory_bank.initialize(config)
    if not success:
        raise RuntimeError("Failed to initialize memory bank")
    return memory_bank

# Cache settings
CACHE_TTL = 60  # 60 seconds
BATCH_SIZE = 50  # Process 50 items at a time
MAX_RETRIES = 3  # Maximum number of retries for failed operations
RETRY_DELAY = 1  # Delay between retries in seconds
COMPRESSION_THRESHOLD = 1024  # Minimum size in bytes for compression
CACHE_SIZE = 1000  # Maximum number of items in LRU cache

MemoryStats = namedtuple('MemoryStats', [
    'cache_size',
    'total_size_bytes',
    'total_entries',
    'categories',
    'cache_hits',
    'cache_misses'
])

class MemoryBank:
    """Stores and manages arbitrage opportunities and trade results."""

    def __init__(self, base_path: Optional[str] = None):
        """Initialize memory bank."""
        self.opportunities = []  # List of opportunities
        self.trade_results = []  # List of trade results
        self.config = {}
        self.initialized = False
        self._categories = [
            "market_data",
            "transactions",
            "analytics",
            "docs",
            "temp",
            "storage",
            "cache"
        ]
        self.storage = {category: {} for category in self._categories}
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Locks for thread safety
        self._storage_locks = {category: asyncio.Lock() for category in self._categories}
        self._stats_lock = asyncio.Lock()
        self._file_lock = asyncio.Lock()
        
        # LRU caches for frequently accessed data
        self._data_cache = lru.LRU(CACHE_SIZE)
        
        # Set up base path and ensure directories exist
        if base_path:
            self.base_path = base_path
        else:
            # Use absolute path from project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            self.base_path = os.path.join(project_root, "data", "memory")
        os.makedirs(self.base_path, exist_ok=True)
        
        logger.debug(f"Memory bank instance created with base path: {self.base_path}")

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize memory bank with configuration."""
        try:
            if self.initialized:
                logger.debug("Memory bank already initialized")
                return True
                
            logger.info("Initializing memory bank...")
            
            # Store configuration
            self.config = config or {}
            
            # Create category directories
            for category in self._categories:
                category_path = os.path.join(self.base_path, category)
                os.makedirs(category_path, exist_ok=True)
                logger.debug(f"Created directory: {category_path}")
            
            self.initialized = True
            logger.info("Memory bank initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize memory bank: {e}", exc_info=True)
            return False

    async def store(self, key: str, data: Any, category: str, ttl: Optional[int] = None) -> None:
        """Store data in specified category."""
        if not self.initialized:
            logger.warning("Memory bank not initialized")
            return

        try:
            if category not in self.storage:
                logger.error(f"Invalid category: {category}")
                return

            # Store in memory
            data_obj = {
                'data': data,
                'timestamp': time.time()
            }
            async with self._storage_locks[category]:
                self.storage[category][key] = data_obj
            
            # Store to disk
            logger.debug(f"Writing {category}/{key} to disk")
            try:
                file_path = os.path.join(self.base_path, category, f"{key}.json")
                logger.debug(f"Writing to file: {file_path}")
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Prepare data
                json_data = json.dumps(data_obj, indent=2).encode('utf-8')
                
                # Write file
                async with self._file_lock:
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        lambda: open(file_path, 'wb').write(json_data)
                    )
                logger.debug(f"Successfully wrote data to {file_path}")
            except Exception as e:
                logger.error(f"Failed to write file {file_path}: {e}")
                raise
            
        except Exception as e:
            logger.error(f"Error storing data: {e}")
            raise

    async def store_opportunities(self, opportunities: List[Opportunity]) -> None:
        """Store arbitrage opportunities."""
        if not self.initialized:
            logger.warning("Memory bank not initialized")
            return
            
        try:
            current_time = time.time()
            logger.debug("Preparing opportunities for storage")
            
            # Add timestamp to opportunities
            opp_dicts = []
            for opp in opportunities:
                if isinstance(opp, dict):
                    opp_dict = {**opp, 'timestamp': current_time}
                else:
                    opp_dict = {**asdict(opp), 'timestamp': current_time}
                opp_dicts.append(opp_dict)
            
            # Add new opportunities
            self.opportunities.extend(opp_dicts)
            logger.debug(f"Added {len(opp_dicts)} opportunities to memory")
            
            # Store to disk
            logger.debug("Writing opportunities to disk")
            try:
                file_path = os.path.join(self.base_path, 'market_data', 'opportunities.json')
                logger.debug(f"Writing to file: {file_path}")
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Prepare data
                json_data = json.dumps(self.opportunities, indent=2).encode('utf-8')
                
                # Write file
                async with self._file_lock:
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        lambda: open(file_path, 'wb').write(json_data)
                    )
                logger.debug(f"Successfully wrote {len(self.opportunities)} opportunities to {file_path}")
            except Exception as e:
                logger.error(f"Failed to write opportunities to disk: {e}")
                raise
            
        except Exception as e:
            logger.error(f"Error storing opportunities: {e}", exc_info=True)

    async def store_trade_result(
        self,
        opportunity: Dict[str, Any],
        success: bool,
        net_profit: Optional[float] = None,
        gas_cost: Optional[float] = None,
        tx_hash: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Store trade execution result."""
        if not self.initialized:
            logger.warning("Memory bank not initialized")
            return
            
        try:
            result = {
                'opportunity': opportunity,
                'success': success,
                'timestamp': time.time(),
                'net_profit': net_profit,
                'gas_cost': gas_cost,
                'tx_hash': tx_hash,
                'error': error
            }
            
            self.trade_results.append(result)
            
            # Store to disk
            logger.debug("Writing trade results to disk")
            try:
                file_path = os.path.join(self.base_path, 'transactions', 'trade_results.json')
                logger.debug(f"Writing to file: {file_path}")
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Prepare data
                json_data = json.dumps(self.trade_results, indent=2).encode('utf-8')
                
                # Write file
                async with self._file_lock:
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        lambda: open(file_path, 'wb').write(json_data)
                    )
                logger.debug(f"Successfully wrote {len(self.trade_results)} trade results to {file_path}")
            except Exception as e:
                logger.error(f"Failed to write trade results to disk: {e}")
                raise
            
        except Exception as e:
            logger.error(f"Error storing trade result: {e}")

    async def get_trade_history(self, limit: Optional[int] = None, max_age: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get trade execution history."""
        if not self.initialized:
            logger.warning("Memory bank not initialized")
            return []
            
        try:
            current_time = time.time()
            filtered_trades = self.trade_results

            # Filter by age if specified
            if max_age is not None:
                filtered_trades = [
                    trade for trade in filtered_trades
                    if current_time - trade['timestamp'] <= max_age
                ]

            # Apply limit if specified
            if limit is not None:
                filtered_trades = filtered_trades[-limit:]

            return filtered_trades
            
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []

    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        try:
            total_size = 0
            compressed_size = 0
            compression_ratio = 0
            
            # Calculate sizes for all stored data
            for category in self.storage:
                for key, value in self.storage[category].items():
                    if isinstance(value, dict) and 'data' in value:
                        data_str = json.dumps(value['data'])
                        uncompressed_size = len(data_str.encode('utf-8'))
                        compressed_size += len(zlib.compress(data_str.encode('utf-8')))
                        total_size += uncompressed_size
            
            if total_size > 0:
                compression_ratio = (total_size - compressed_size) / total_size
            
            return {
                'total_size': total_size,
                'compressed_size': compressed_size,
                'compression_ratio': compression_ratio,
                'compression_savings': total_size - compressed_size
            }
        except Exception as e:
            logger.error(f"Error getting compression stats: {e}")
            return {
                'total_size': 0,
                'compressed_size': 0,
                'compression_ratio': 0,
                'compression_savings': 0
            }

    async def get_recent_opportunities(self, max_age: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent arbitrage opportunities."""
        try:
            current_time = time.time()
            filtered_opps = self.opportunities

            # Filter by age if specified
            if max_age is not None:
                filtered_opps = [
                    opp for opp in filtered_opps
                    if current_time - opp['timestamp'] <= max_age
                ]

            return filtered_opps
        except Exception as e:
            logger.error(f"Error getting recent opportunities: {e}")
            return []

    async def get_memory_stats(self) -> MemoryStats:
        """Get memory usage statistics."""
        try:
            total_size = 0
            categories = {}
            item_count = 0
            
            # Add opportunities and trade results to stats
            opp_size = sum(len(str(opp)) for opp in self.opportunities)
            trade_size = sum(len(str(trade)) for trade in self.trade_results)
            total_size = opp_size + trade_size
            item_count = len(self.opportunities) + len(self.trade_results)
            
            categories['market_data'] = {
                'size': opp_size,
                'items': [f'opportunity_{i}' for i in range(len(self.opportunities))]
            }
            categories['transactions'] = {
                'size': trade_size,
                'items': [f'trade_{i}' for i in range(len(self.trade_results))]
            }
            
            # Add storage categories
            for category, data in self.storage.items():
                if category not in ['market_data', 'transactions']:
                    category_size = 0
                    category_items = []
                    
                    for key, value in data.items():
                        if isinstance(value, dict) and 'data' in value:
                            size = len(str(value['data']))
                        else:
                            size = len(str(value))
                        category_size += size
                        total_size += size
                        item_count += 1
                        category_items.append(key)
                    
                    categories[category] = {
                        'size': category_size,
                        'items': category_items
                    }
            
            return MemoryStats(
                cache_size=len(self._data_cache),
                total_size_bytes=total_size,
                total_entries=item_count,
                categories=categories,
                cache_hits=self.stats['cache_hits'],
                cache_misses=self.stats['cache_misses']
            )
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return MemoryStats(0, 0, 0, {}, 0, 0)
