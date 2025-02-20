"""Transaction monitoring and mempool analysis system."""

import logging
import time
from typing import Optional
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import json
from json import JSONEncoder
from pathlib import Path
from collections import defaultdict
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from ..web3.web3_manager import Web3Manager
from ..analytics.analytics_system import AnalyticsSystem
from ..ml.ml_system import MLSystem
from ..dex import DexManager
from ..dex.utils import COMMON_TOKENS
from ...utils.database import DateTimeEncoder

logger = logging.getLogger(__name__)

# Cache settings
CACHE_TTL = 60  # 60 seconds
BATCH_SIZE = 50  # Process 50 items at a time

class TransactionMonitor:
    """Monitors blockchain transactions and mempool."""

    def __init__(
        self,
        web3_manager: Web3Manager,
        analytics: AnalyticsSystem,
        ml_system: MLSystem,
        dex_manager: DexManager,
        monitoring_dir: str = "monitoring_data",
        max_blocks_history: int = 1000,
        mempool_refresh_rate: float = 0.1,  # seconds
        batch_size: int = BATCH_SIZE
    ):
        """Initialize transaction monitor."""
        self.web3_manager = web3_manager
        self.analytics = analytics
        self.ml_system = ml_system
        self.dex_manager = dex_manager
        self.monitoring_dir = Path(monitoring_dir)
        self.monitoring_dir.mkdir(exist_ok=True)
        self.max_blocks_history = max_blocks_history
        self.mempool_refresh_rate = mempool_refresh_rate
        self.batch_size = batch_size
        self.last_update = datetime.now().timestamp()
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Monitoring state with locks
        self._state_lock = asyncio.Lock()
        self.known_competitors: Set[str] = set()
        self.competitor_patterns: Dict[str, Dict[str, Any]] = {}
        self.recent_transactions: List[Dict[str, Any]] = []
        self.mempool_state: Dict[str, Dict[str, Any]] = {}
        self.block_reorgs: List[Dict[str, Any]] = []
        
        # Performance metrics with locks
        self._metrics_lock = asyncio.Lock()
        self.execution_times: Dict[str, List[float]] = defaultdict(list)
        self.success_rates: Dict[str, List[bool]] = defaultdict(list)
        self.gas_usage: Dict[str, List[int]] = defaultdict(list)
        
        # Cache settings
        self.cache_ttl = CACHE_TTL
        
        # Caches with TTL
        self._tx_cache = {}  # Cache for transaction data
        self._block_cache = {}  # Cache for block data
        self._pattern_cache = {}  # Cache for competitor patterns
        
        # Cache timestamps
        self._tx_cache_times = {}
        self._block_cache_times = {}
        self._pattern_cache_times = {}
        
        # Additional locks for thread safety
        self._cache_lock = asyncio.Lock()
        self._file_lock = asyncio.Lock()
        
        # Alert thresholds
        self.min_success_rate = 0.95  # 95% success rate required
        self.max_execution_time = 3.0  # seconds
        self.max_gas_increase = 1.5  # 50% gas increase threshold

    async def start_monitoring(self) -> None:
        """Start transaction monitoring."""
        try:
            # Load historical data and clean caches concurrently
            init_tasks = [
                asyncio.create_task(self._load_historical_data()),
                asyncio.create_task(self._cleanup_caches())
            ]
            await asyncio.gather(*init_tasks)
            
            # Start monitoring tasks
            self._tasks = [
                asyncio.create_task(self._monitor_mempool()),
                asyncio.create_task(self._monitor_blocks()),
                asyncio.create_task(self._analyze_competitors()),
                asyncio.create_task(self._detect_reorgs()),
                asyncio.create_task(self._save_monitoring_data()),
                asyncio.create_task(self._periodic_cache_cleanup())
            ]
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")

    async def _clean_mempool(self) -> None:
        """Clean old transactions from mempool state."""
        try:
            current_time = time.time()
            async with self._state_lock:
                # Remove transactions older than cache TTL
                expired_txs = [
                    tx_hash for tx_hash, tx_data in self.mempool_state.items()
                    if current_time - tx_data['first_seen'].timestamp() > self.cache_ttl
                ]
                for tx_hash in expired_txs:
                    del self.mempool_state[tx_hash]
        except Exception as e:
            logger.error(f"Error cleaning mempool: {e}")

    async def _trim_transactions(self) -> None:
        """Trim old transactions from recent transactions list."""
        try:
            async with self._state_lock:
                # Keep only transactions from last max_blocks_history blocks
                if not self.recent_transactions:
                    return
                    
                latest_block = max(tx['block_number'] for tx in self.recent_transactions)
                self.recent_transactions = [
                    tx for tx in self.recent_transactions
                    if latest_block - tx['block_number'] < self.max_blocks_history
                ]
        except Exception as e:
            logger.error(f"Error trimming transactions: {e}")

    async def _monitor_mempool(self) -> None:
        """Monitor mempool for new transactions in batches."""
        try:
            while True:
                # Get pending transactions
                pending_filter = await self.web3_manager.w3.eth.filter('pending')
                pending_hashes = await pending_filter.get_all_entries()
                
                # Process transactions in batches concurrently
                for i in range(0, len(pending_hashes), self.batch_size):
                    batch = pending_hashes[i:i + self.batch_size]
                    
                    # Process batch in thread pool
                    loop = asyncio.get_event_loop()
                    batch_tasks = [
                        loop.run_in_executor(
                            self.executor,
                            self._process_mempool_batch,
                            batch[j:j + 10]  # Sub-batch of 10 transactions
                        )
                        for j in range(0, len(batch), 10)
                    ]
                    
                    # Wait for all sub-batches
                    await asyncio.gather(*batch_tasks)
                
                # Clean old transactions
                await self._clean_mempool()
                
                await asyncio.sleep(self.mempool_refresh_rate)
                
        except Exception as e:
            logger.error(f"Error monitoring mempool: {e}")

    def _process_mempool_batch(self, tx_hashes: List[str]) -> None:
        """Process a batch of mempool transactions (CPU-bound)."""
        try:
            for tx_hash in tx_hashes:
                try:
                    tx = self.web3_manager.w3.eth.get_transaction(tx_hash)
                    if not tx:
                        continue
                        
                    # Check transaction cache
                    tx_hash_hex = tx['hash'].hex()
                    if tx_hash_hex in self._tx_cache:
                        continue
                    
                    # Process transaction
                    if self._is_relevant_transaction_sync(tx):
                        self._tx_cache[tx_hash_hex] = {
                            'transaction': tx,
                            'first_seen': datetime.now(),
                            'gas_price': tx['gasPrice']
                        }
                        self._tx_cache_times[tx_hash_hex] = time.time()
                        
                except Exception as e:
                    logger.debug(f"Failed to process transaction {tx_hash.hex()}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing mempool batch: {e}")

    def _is_relevant_transaction_sync(self, tx: Dict[str, Any]) -> bool:
        """Check if transaction is relevant (CPU-bound)."""
        try:
            # Check for common DEX methods
            method_id = tx.get('input', '')[:10]
            return (
                method_id in self.dex_manager.known_methods or
                tx['to'] in self.dex_manager.known_contracts
            )
        except Exception:
            return False

    async def _is_relevant_transaction(self, tx: Dict[str, Any]) -> bool:
        """Check if transaction is relevant."""
        try:
            # Check for common DEX methods
            method_id = tx.get('input', '')[:10]
            return (
                method_id in self.dex_manager.known_methods or
                tx['to'] in self.dex_manager.known_contracts
            )
        except Exception:
            return False

    async def _monitor_blocks(self) -> None:
        """Monitor new blocks for relevant transactions."""
        try:
            while True:
                # Get latest block with caching
                block = await self._get_cached_block('latest')
                if not block:
                    await asyncio.sleep(1)
                    continue
                
                # Process transactions in batches concurrently
                txs = [tx for tx in block['transactions'] if await self._is_relevant_transaction(tx)]
                
                for i in range(0, len(txs), self.batch_size):
                    batch = txs[i:i + self.batch_size]
                    
                    # Process batch in thread pool
                    loop = asyncio.get_event_loop()
                    batch_tasks = [
                        loop.run_in_executor(
                            self.executor,
                            self._process_block_batch,
                            batch[j:j + 10],  # Sub-batch of 10 transactions
                            block
                        )
                        for j in range(0, len(batch), 10)
                    ]
                    
                    # Wait for all sub-batches
                    await asyncio.gather(*batch_tasks)
                
                # Trim old transactions
                await self._trim_transactions()
                
                await asyncio.sleep(1)  # Check each block
                
        except Exception as e:
            logger.error(f"Error monitoring blocks: {e}")

    async def _get_cached_block(self, block_identifier: str) -> Optional[Dict[str, Any]]:
        """Get block from cache or fetch if needed."""
        try:
            current_time = time.time()
            cache_key = str(block_identifier)
            
            async with self._cache_lock:
                # Check cache with TTL
                if cache_key in self._block_cache:
                    last_update = self._block_cache_times.get(cache_key, 0)
                    if current_time - last_update < self.cache_ttl:
                        return self._block_cache[cache_key]
                
                # Fetch new block
                block = await self.web3_manager.w3.eth.get_block(block_identifier, True)
                
                # Update cache
                self._block_cache[cache_key] = block
                self._block_cache_times[cache_key] = current_time
                
                return block
                
        except Exception as e:
            logger.error(f"Error getting cached block: {e}")
            return None

    def _process_block_batch(
        self,
        txs: List[Dict[str, Any]],
        block: Dict[str, Any]
    ) -> None:
        """Process a batch of block transactions (CPU-bound)."""
        try:
            for tx in txs:
                try:
                    # Check transaction success
                    success = self._check_transaction_success_sync(tx)
                    
                    # Record transaction
                    transaction_data = {
                        'transaction': tx,
                        'block_number': block['number'],
                        'timestamp': datetime.fromtimestamp(block['timestamp']),
                        'success': success
                    }
                    
                    # Update state synchronously
                    self._update_transaction_state(transaction_data, tx)
                        
                except Exception as e:
                    logger.error(f"Error processing block transaction: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing block batch: {e}")

    def _update_competitor_metrics_sync(self, tx: Dict[str, Any]) -> None:
        """Update competitor metrics (CPU-bound)."""
        try:
            # Get transaction receipt
            receipt = self.web3_manager.w3.eth.get_transaction_receipt(tx['hash'])
            if not receipt:
                return
                
            # Update metrics
            with self._metrics_lock:
                # Update success rate
                self.success_rates[tx['from']].append(receipt['status'] == 1)
                if len(self.success_rates[tx['from']]) > 100:  # Keep last 100
                    self.success_rates[tx['from']] = self.success_rates[tx['from']][-100:]
                
                # Update gas usage
                self.gas_usage[tx['from']].append(receipt['gasUsed'])
                if len(self.gas_usage[tx['from']]) > 100:  # Keep last 100
                    self.gas_usage[tx['from']] = self.gas_usage[tx['from']][-100:]
                
                # Update execution time if we have block timestamps
                try:
                    block = self.web3_manager.w3.eth.get_block(receipt['blockNumber'])
                    prev_block = self.web3_manager.w3.eth.get_block(receipt['blockNumber'] - 1)
                    execution_time = block['timestamp'] - prev_block['timestamp']
                    
                    self.execution_times[tx['from']].append(execution_time)
                    if len(self.execution_times[tx['from']]) > 100:  # Keep last 100
                        self.execution_times[tx['from']] = self.execution_times[tx['from']][-100:]
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Error updating competitor metrics: {e}")

    def _update_transaction_state(self, transaction_data: Dict[str, Any], tx: Dict[str, Any]) -> None:
        """Update transaction state (CPU-bound)."""
        try:
            # Update recent transactions
            with self._state_lock:
                self.recent_transactions.append(transaction_data)
            
            # Update competitor metrics if known
            if tx['from'] in self.known_competitors:
                self._update_competitor_metrics_sync(tx)
                
        except Exception as e:
            logger.error(f"Error updating transaction state: {e}")

    def _check_transaction_success_sync(self, tx: Dict[str, Any]) -> bool:
        """Check transaction success (CPU-bound)."""
        try:
            receipt = self.web3_manager.w3.eth.get_transaction_receipt(tx['hash'])
            return receipt['status'] == 1
        except Exception:
            return False

    async def _analyze_competitors(self) -> None:
        """Analyze competitor behavior patterns concurrently."""
        try:
            while True:
                # Group transactions by sender
                sender_txs = defaultdict(list)
                async with self._state_lock:
                    for tx in self.recent_transactions:
                        sender_txs[tx['transaction']['from']].append(tx)
                
                # Process senders in batches
                senders = [
                    sender for sender, txs in sender_txs.items()
                    if len(txs) >= 10  # Need minimum sample size
                ]
                
                for i in range(0, len(senders), self.batch_size):
                    batch = senders[i:i + self.batch_size]
                    
                    # Process batch in thread pool
                    loop = asyncio.get_event_loop()
                    batch_tasks = [
                        loop.run_in_executor(
                            self.executor,
                            self._analyze_competitor_batch,
                            [sender_txs[sender] for sender in batch[j:j + 10]]
                        )
                        for j in range(0, len(batch), 10)
                    ]
                    
                    # Wait for all sub-batches
                    results = await asyncio.gather(*batch_tasks)
                    
                    # Update competitor patterns
                    async with self._state_lock:
                        for sender, pattern in results:
                            if pattern:
                                self.competitor_patterns[sender] = pattern
                                
                                # Add to known competitors if pattern suggests arbitrage bot
                                if (
                                    pattern['success_rate'] > 0.8 and
                                    pattern['avg_execution_time'] < 2.0 and
                                    pattern['transaction_count'] > 50
                                ):
                                    self.known_competitors.add(sender)
                
                await asyncio.sleep(60)  # Update every minute
                
        except Exception as e:
            logger.error(f"Error analyzing competitors: {e}")

    def _analyze_competitor_batch(
        self,
        sender_txs_list: List[List[Dict[str, Any]]]
    ) -> List[Tuple[str, Optional[Dict[str, Any]]]]:
        """Analyze a batch of competitors (CPU-bound)."""
        results = []
        for txs in sender_txs_list:
            if not txs:
                continue
                
            sender = txs[0]['transaction']['from']
            try:
                # Calculate metrics
                success_rate = sum(1 for tx in txs if tx['success']) / len(txs)
                avg_gas = np.mean([tx['transaction']['gas'] for tx in txs])
                
                # Calculate execution times
                execution_times = []
                for tx in txs:
                    try:
                        block = self.web3_manager.w3.eth.get_block(tx['block_number'])
                        prev_block = self.web3_manager.w3.eth.get_block(tx['block_number'] - 1)
                        execution_time = block['timestamp'] - prev_block['timestamp']
                        execution_times.append(execution_time)
                    except Exception:
                        continue
                
                avg_time = np.mean(execution_times) if execution_times else float('inf')
                
                pattern = {
                    'success_rate': success_rate,
                    'avg_gas_usage': avg_gas,
                    'avg_execution_time': avg_time,
                    'transaction_count': len(txs),
                    'last_seen': max(tx['timestamp'] for tx in txs)
                }
                
                results.append((sender, pattern))
                
            except Exception as e:
                logger.error(f"Error analyzing competitor {sender}: {e}")
                results.append((sender, None))
                
        return results

    async def _load_historical_data(self) -> None:
        """Load historical monitoring data concurrently."""
        try:
            # Find all monitoring files
            files = list(self.monitoring_dir.glob("monitoring_*.json"))
            
            # Process files in batches
            for i in range(0, len(files), self.batch_size):
                batch = files[i:i + self.batch_size]
                
                # Load batch in thread pool
                loop = asyncio.get_event_loop()
                batch_tasks = [
                    loop.run_in_executor(
                        self.executor,
                        self._read_json_file,
                        file_path
                    )
                    for file_path in batch
                ]
                
                # Wait for batch results
                results = await asyncio.gather(*batch_tasks)
                
                # Update state with results
                await self._update_state_from_historical(results)
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")

    async def _update_state_from_historical(
        self,
        results: List[Optional[Dict[str, Any]]]
    ) -> None:
        """Update state from historical data results."""
        try:
            async with self._state_lock:
                for data in results:
                    if data:
                        # Update competitor patterns
                        self.competitor_patterns.update(data.get('competitor_patterns', {}))
                        
                        # Update known competitors
                        for sender, pattern in data.get('competitor_patterns', {}).items():
                            if (
                                pattern.get('success_rate', 0) > 0.8 and
                                pattern.get('avg_execution_time', float('inf')) < 2.0 and
                                pattern.get('transaction_count', 0) > 50
                            ):
                                self.known_competitors.add(sender)
                        
                        # Update block reorgs
                        self.block_reorgs.extend(data.get('block_reorgs', []))
                
                # Trim old data
                self.block_reorgs = self.block_reorgs[-1000:]  # Keep last 1000 reorgs
                
        except Exception as e:
            logger.error(f"Error updating state from historical data: {e}")

    def _read_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Read JSON file (CPU-bound)."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    async def _cleanup_caches(self) -> None:
        """Clean up expired cache entries."""
        try:
            current_time = time.time()
            
            async with self._cache_lock:
                # Clean up transaction cache
                expired_txs = [
                    key for key, last_update in self._tx_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_txs:
                    del self._tx_cache[key]
                    del self._tx_cache_times[key]
                
                # Clean up block cache
                expired_blocks = [
                    key for key, last_update in self._block_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_blocks:
                    del self._block_cache[key]
                    del self._block_cache_times[key]
                
                # Clean up pattern cache
                expired_patterns = [
                    key for key, last_update in self._pattern_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_patterns:
                    del self._pattern_cache[key]
                    del self._pattern_cache_times[key]
                    
        except Exception as e:
            logger.error(f"Error cleaning up caches: {e}")

    async def _periodic_cache_cleanup(self) -> None:
        """Periodically clean up caches."""
        try:
            while True:
                await self._cleanup_caches()
                await asyncio.sleep(self.cache_ttl / 2)  # Clean up every half TTL
        except Exception as e:
            logger.error(f"Error in periodic cache cleanup: {e}")

    async def get_metrics(self) -> Dict[str, Any]:
        """Get monitoring metrics."""
        try:
            # Calculate metrics in thread pool
            loop = asyncio.get_event_loop()
            metrics = await loop.run_in_executor(
                self.executor,
                self._calculate_metrics
            )
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {
                'total_transactions': 0,
                'successful_transactions': 0,
                'success_rate': 0.0,
                'known_competitors': 0,
                'block_reorgs': 0,
                'last_update': datetime.now().timestamp()
            }

    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate metrics (CPU-bound)."""
        try:
            # Create a copy of the data we need to avoid holding the lock
            total_txs = len(self.recent_transactions)
            successful_txs = len([tx for tx in self.recent_transactions if tx['success']])
            known_competitors = len(self.known_competitors)
            block_reorgs = len(self.block_reorgs)
            last_update = self.last_update
            
            return {
                'total_transactions': total_txs,
                'successful_transactions': successful_txs,
                'success_rate': successful_txs / total_txs if total_txs > 0 else 0.0,
                'known_competitors': known_competitors,
                'block_reorgs': block_reorgs,
                'last_update': last_update
            }
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {
                'total_transactions': 0,
                'successful_transactions': 0,
                'success_rate': 0.0,
                'known_competitors': 0,
                'block_reorgs': 0,
                'last_update': datetime.now().timestamp()
            }

    async def _detect_reorgs(self) -> None:
        """Detect and record blockchain reorganizations."""
        try:
            while True:
                # Get latest block
                latest_block = await self.web3_manager.w3.eth.get_block('latest')
                if not latest_block:
                    await asyncio.sleep(1)
                    continue
                
                # Check previous blocks for reorgs
                for i in range(1, 6):  # Check last 5 blocks
                    block_number = latest_block['number'] - i
                    
                    # Get block by number
                    block = await self.web3_manager.w3.eth.get_block(block_number)
                    if not block:
                        continue
                    
                    # Get cached block
                    cache_key = str(block_number)
                    cached_block = self._block_cache.get(cache_key)
                    
                    # Compare block hashes
                    if cached_block and block['hash'] != cached_block['hash']:
                        # Record reorg
                        reorg = {
                            'block_number': block_number,
                            'old_hash': cached_block['hash'].hex(),
                            'new_hash': block['hash'].hex(),
                            'timestamp': datetime.now().timestamp(),
                            'depth': i
                        }
                        
                        async with self._state_lock:
                            self.block_reorgs.append(reorg)
                            # Keep only last 1000 reorgs
                            if len(self.block_reorgs) > 1000:
                                self.block_reorgs = self.block_reorgs[-1000:]
                    
                    # Update cache
                    self._block_cache[cache_key] = block
                    self._block_cache_times[cache_key] = time.time()
                
                await asyncio.sleep(1)  # Check every second
                
        except Exception as e:
            logger.error(f"Error detecting reorgs: {e}")

    async def _save_monitoring_data(self) -> None:
        """Periodically save monitoring data to disk."""
        try:
            while True:
                try:
                    # Prepare monitoring data
                    data = {
                        'timestamp': datetime.now().timestamp(),
                        'competitor_patterns': self.competitor_patterns,
                        'known_competitors': list(self.known_competitors),
                        'block_reorgs': self.block_reorgs[-100:],  # Save last 100 reorgs
                        'metrics': await self.get_metrics()
                    }
                    
                    # Generate filename with timestamp
                    filename = f"monitoring_{int(time.time())}.json"
                    file_path = self.monitoring_dir / filename
                    
                    # Save to file
                    async with self._file_lock:
                        with open(file_path, 'w') as f:
                            json.dump(data, f, cls=DateTimeEncoder, indent=2)
                    
                    # Clean up old files
                    files = sorted(self.monitoring_dir.glob("monitoring_*.json"))
                    if len(files) > 100:  # Keep last 100 files
                        for file in files[:-100]:
                            file.unlink()
                            
                except Exception as e:
                    logger.error(f"Error saving monitoring data: {e}")
                
                await asyncio.sleep(300)  # Save every 5 minutes
                
        except Exception as e:
            logger.error(f"Error in monitoring data save loop: {e}")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            # Cancel any ongoing tasks
            if hasattr(self, '_tasks'):
                for task in self._tasks:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                        
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            logger.info("Transaction monitor cleanup complete")
        except Exception as e:
            logger.error(f"Error during transaction monitor cleanup: {e}")

async def create_transaction_monitor(
    web3_manager: Web3Manager,
    analytics: AnalyticsSystem,
    ml_system: MLSystem,
    dex_manager: DexManager,
    monitoring_dir: Optional[str] = None,
    max_blocks_history: Optional[int] = None,
    mempool_refresh_rate: Optional[float] = None,
    batch_size: Optional[int] = None
) -> Optional[TransactionMonitor]:
    """Create and initialize a transaction monitor instance."""
    try:
        # Ensure DEX manager is initialized
        if not dex_manager.initialized:
            success = await dex_manager.initialize()
            if not success:
                logger.error("Failed to initialize DEX manager")
                return None

        monitor = TransactionMonitor(
            web3_manager=web3_manager,
            analytics=analytics,
            ml_system=ml_system,
            dex_manager=dex_manager,
            monitoring_dir=monitoring_dir or "monitoring_data",
            max_blocks_history=max_blocks_history or 1000,
            mempool_refresh_rate=mempool_refresh_rate or 0.1,
            batch_size=batch_size or BATCH_SIZE
        )
        return monitor
    except Exception as e:
        logger.error(f"Failed to create transaction monitor: {e}")
        return None

# Export the create function
__all__ = ['create_transaction_monitor']
