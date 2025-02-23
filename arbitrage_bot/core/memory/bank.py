"""Memory bank for storing and retrieving arbitrage opportunities and trade results."""

import logging
import time
import os
import json
import zlib
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple, defaultdict
import lru

from ..models.opportunity import Opportunity
from .file_manager import FileManager

logger = logging.getLogger(__name__)

def create_memory_bank(config: Optional[Dict[str, Any]] = None) -> 'MemoryBank':
    """Create and initialize a memory bank instance."""
    memory_bank = MemoryBank()
    success = memory_bank.initialize(config)
    if not success:
        raise RuntimeError("Failed to initialize memory bank")
    return memory_bank

# Cache settings
CACHE_TTL = 60  # 60 seconds
BATCH_SIZE = 50  # Process 50 items at a time
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
        self._storage_locks = {}
        for category in self._categories:
            self._storage_locks[category] = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        
        # LRU caches for frequently accessed data
        self._data_cache = lru.LRU(CACHE_SIZE)
        
        # Set up base path and ensure directories exist
        if base_path:
            self.base_path = base_path
        else:
            # Use absolute path from project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            self.base_path = os.path.join(project_root, "data", "memory")
            
        # Initialize file manager
        self.file_manager = FileManager(self.base_path)
        
        logger.debug("Memory bank instance created with base path: %s", self.base_path)

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize memory bank with configuration."""
        try:
            if self.initialized:
                logger.debug("Memory bank already initialized")
                return True
                
            logger.debug("Initializing memory bank...")
            
            # Store configuration
            self.config = config or {}
            
            # Create category directories
            for category in self._categories:
                if not self.file_manager.ensure_directory(category):
                    logger.error("Failed to create directory for category: %s", category)
                    return False
            
            # Load historical data
            self._load_historical_data()
            
            self.initialized = True
            logger.debug("Memory bank initialization complete")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize memory bank: %s", str(e), exc_info=True)
            return False

    def _load_historical_data(self) -> None:
        """Load historical data from disk."""
        try:
            # Load opportunities
            opportunities = self.file_manager.read_json(os.path.join('market_data', 'opportunities.json'))
            if opportunities:
                self.opportunities = opportunities
                logger.debug("Loaded %d historical opportunities", len(self.opportunities))

            # Load trade results
            trade_results = self.file_manager.read_json(os.path.join('transactions', 'trade_results.json'))
            if trade_results:
                self.trade_results = trade_results
                logger.debug("Loaded %d historical trade results", len(self.trade_results))

            # Load other categories
            for category in self._categories:
                if category not in ['market_data', 'transactions']:
                    category_path = os.path.join(self.base_path, category)
                    if os.path.exists(category_path):
                        for filename in os.listdir(category_path):
                            if filename.endswith('.json'):
                                key = filename[:-5]  # Remove .json extension
                                file_path = os.path.join(category, filename)
                                try:
                                    data_obj = self.file_manager.read_json(file_path)
                                    if data_obj:
                                        # Check TTL
                                        if 'ttl' in data_obj and data_obj['ttl'] is not None:
                                            if time.time() - data_obj['timestamp'] > data_obj['ttl']:
                                                self.file_manager.delete_file(file_path)
                                                continue
                                        
                                        # Store in memory
                                        with self._storage_locks[category]:
                                            self.storage[category][key] = data_obj
                                except Exception as e:
                                    logger.error("Failed to load %s: %s", file_path, str(e))
                                    continue

            logger.debug("Historical data loading complete")
            
        except Exception as e:
            logger.error("Failed to load historical data: %s", str(e))

    def store(self, key: str, data: Any, category: str, ttl: Optional[int] = None) -> None:
        """Store data in specified category."""
        if not self.initialized:
            logger.warning("Memory bank not initialized")
            return

        try:
            if category not in self.storage:
                logger.error("Invalid category: %s", category)
                return

            # Store in memory
            data_obj = {
                'data': data,
                'timestamp': time.time(),
                'ttl': ttl
            }
            async with self._storage_locks[category]:
                self.storage[category][key] = data_obj
            
            # Store to disk
            file_path = os.path.join(category, key + ".json")
            if not self.file_manager.write_json(file_path, data_obj):
                logger.error("Failed to write data to %s", file_path)
                
        except Exception as e:
            logger.error("Error storing data: %s", str(e))
            raise

    def retrieve(self, key: str, category: str) -> Optional[Any]:
        """Retrieve data from specified category."""
        if not self.initialized:
            logger.warning("Memory bank not initialized")
            return None

        try:
            # Check cache first
            cache_key = category + ":" + key
            if cache_key in self._data_cache:
                async with self._stats_lock:
                    self.stats['cache_hits'] += 1
                    return self._data_cache[cache_key]['data']

            with self._stats_lock:
                self.stats['cache_misses'] += 1

            # Check memory storage
            async with self._storage_locks[category]:
                if key in self.storage[category]:
                    data_obj = self.storage[category][key]
                    
                    # Check TTL
                    if 'ttl' in data_obj and data_obj['ttl'] is not None:
                        if time.time() - data_obj['timestamp'] > data_obj['ttl']:
                            del self.storage[category][key]
                            return None
                    
                    # Update cache
                    self._data_cache[cache_key] = data_obj
                    return data_obj['data']

            # If not in memory, try to load from disk
            file_path = os.path.join(category, key + ".json")
            data_obj = self.file_manager.read_json(file_path)
            if data_obj:
                # Check TTL
                if 'ttl' in data_obj and data_obj['ttl'] is not None:
                    if time.time() - data_obj['timestamp'] > data_obj['ttl']:
                        self.file_manager.delete_file(file_path)
                        return None
                
                # Store in memory and cache
                async with self._storage_locks[category]:
                    self.storage[category][key] = data_obj
                self._data_cache[cache_key] = data_obj
                return data_obj['data']

            return None
            
        except Exception as e:
            logger.error("Error retrieving data: %s", str(e))
            return None

    def store_opportunities(self, opportunities: List[Opportunity]) -> None:
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
            logger.debug("Added %d opportunities to memory", len(opp_dicts))
            
            # Store to disk
            file_path = os.path.join('market_data', 'opportunities.json')
            if not self.file_manager.write_json(file_path, self.opportunities):
                logger.error("Failed to write opportunities to disk")
            
        except Exception as e:
            logger.error("Error storing opportunities: %s", str(e), exc_info=True)

    def store_trade_result(
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
            file_path = os.path.join('transactions', 'trade_results.json')
            if not self.file_manager.write_json(file_path, self.trade_results):
                logger.error("Failed to write trade results to disk")
            
        except Exception as e:
            logger.error("Error storing trade result: %s", str(e))

    def get_trade_history(self, limit: Optional[int] = None, max_age: Optional[int] = None) -> List[Dict[str, Any]]:
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
            logger.error("Error getting trade history: %s", str(e))
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
            logger.error("Error getting compression stats: %s", str(e))
            return {
                'total_size': 0,
                'compressed_size': 0,
                'compression_ratio': 0,
                'compression_savings': 0
            }

    def get_recent_opportunities(self, max_age: Optional[int] = None) -> List[Dict[str, Any]]:
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
            logger.error("Error getting recent opportunities: %s", str(e))
            return []

    def get_memory_stats(self) -> MemoryStats:
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
                'items': ['opportunity_%d' % i for i in range(len(self.opportunities))]
            }
            categories['transactions'] = {
                'size': trade_size,
                'items': ['trade_%d' % i for i in range(len(self.trade_results))]
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
            logger.error("Error getting memory stats: %s", str(e))
            return MemoryStats(0, 0, 0, {}, 0, 0)
