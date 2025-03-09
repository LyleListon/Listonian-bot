"""Transaction monitoring and mempool analysis system."""

import logging
from typing import Optional

import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import json
from json import JSONEncoder
from pathlib import Path
from collections import defaultdict
import numpy as np

from ..web3.web3_manager import Web3Manager
from ..analytics.analytics_system import AnalyticsSystem
from ..ml.ml_system import MLSystem
from ..dex.dex_manager import DEXManager
from ..dex.utils import COMMON_TOKENS
from ...utils.database import DateTimeEncoder

logger = logging.getLogger(__name__)

class TransactionMonitor:
    """Monitors blockchain transactions and mempool."""

    def __init__(
        self,
        web3_manager: Web3Manager,
        analytics: AnalyticsSystem,
        ml_system: MLSystem,
        dex_manager: DEXManager,
        monitoring_dir: str = "monitoring_data",
        max_blocks_history: int = 1000,
        mempool_refresh_rate: float = 0.1  # seconds
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
        self.last_update = datetime.now().timestamp()
        
        # Monitoring state
        self.known_competitors: Set[str] = set()
        self.competitor_patterns: Dict[str, Dict[str, Any]] = {}
        self.recent_transactions: List[Dict[str, Any]] = []
        self.mempool_state: Dict[str, Dict[str, Any]] = {}
        self.block_reorgs: List[Dict[str, Any]] = []
        
        # Performance metrics
        self.execution_times: Dict[str, List[float]] = defaultdict(list)
        self.success_rates: Dict[str, List[bool]] = defaultdict(list)
        self.gas_usage: Dict[str, List[int]] = defaultdict(list)
        
        # Alert thresholds
        self.min_success_rate = 0.95  # 95% success rate required
        self.max_execution_time = 3.0  # seconds
        self.max_gas_increase = 1.5  # 50% gas increase threshold

    async def start_monitoring(self) -> None:
        """Start transaction monitoring."""
        try:
            # Load historical data
            await self._load_historical_data()
            
            # Start monitoring tasks
            self._tasks = [
                asyncio.create_task(self._monitor_mempool()),
                asyncio.create_task(self._monitor_blocks()),
                asyncio.create_task(self._analyze_competitors()),
                asyncio.create_task(self._detect_reorgs()),
                asyncio.create_task(self._save_monitoring_data())
            ]
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")

    async def get_metrics(self) -> Dict[str, Any]:
        """Get monitoring metrics."""
        try:
            total_txs = len(self.recent_transactions)
            successful_txs = len([tx for tx in self.recent_transactions if tx['success']])
            
            return {
                'total_transactions': total_txs,
                'successful_transactions': successful_txs,
                'success_rate': successful_txs / total_txs if total_txs > 0 else 0.0,
                'known_competitors': len(self.known_competitors),
                'block_reorgs': len(self.block_reorgs),
                'last_update': self.last_update
            }
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
            logger.info("Transaction monitor cleanup complete")
        except Exception as e:
            logger.error(f"Error during transaction monitor cleanup: {e}")

    async def _monitor_mempool(self) -> None:
        """Monitor mempool for new transactions."""
        try:
            while True:
                # Get pending transactions
                pending_filter = await self.web3_manager.w3.eth.filter('pending')
                pending_hashes = await pending_filter.get_all_entries()
                pending = []
                for tx_hash in pending_hashes:
                    try:
                        tx = await self.web3_manager.w3.eth.get_transaction(tx_hash)
                        if tx:
                            pending.append(tx)
                    except Exception as e:
                        logger.debug(f"Failed to get transaction {tx_hash.hex()}: {e}")
                
                for tx in pending:
                    # Check if transaction is relevant
                    if await self._is_relevant_transaction(tx):
                        tx_hash = tx['hash'].hex()
                        
                        # Store transaction details
                        self.mempool_state[tx_hash] = {
                            'transaction': tx,
                            'first_seen': datetime.now(),
                            'gas_price': tx['gasPrice'],
                            'predicted_success': await self._predict_transaction_success(tx)
                        }
                        
                        # Check for competitor patterns
                        await self._analyze_transaction_pattern(tx)
                
                # Clean old transactions
                current_time = datetime.now()
                expired_txs = [
                    tx_hash for tx_hash, tx_data in self.mempool_state.items()
                    if (current_time - tx_data['first_seen']) > timedelta(minutes=10)
                ]
                for tx_hash in expired_txs:
                    del self.mempool_state[tx_hash]
                
                await asyncio.sleep(self.mempool_refresh_rate)
                
        except Exception as e:
            logger.error(f"Error monitoring mempool: {e}")

    async def _monitor_blocks(self) -> None:
        """Monitor new blocks for relevant transactions."""
        try:
            while True:
                # Get latest block
                block = await self.web3_manager.w3.eth.get_block('latest', True)
                
                for tx in block['transactions']:
                    if await self._is_relevant_transaction(tx):
                        # Record transaction
                        self.recent_transactions.append({
                            'transaction': tx,
                            'block_number': block['number'],
                            'timestamp': datetime.fromtimestamp(block['timestamp']),
                            'success': await self._check_transaction_success(tx)
                        })
                        
                        # Update competitor metrics if known
                        if tx['from'] in self.known_competitors:
                            await self._update_competitor_metrics(tx)
                
                # Trim old transactions
                if len(self.recent_transactions) > self.max_blocks_history:
                    self.recent_transactions = self.recent_transactions[-self.max_blocks_history:]
                
                await asyncio.sleep(1)  # Check each block
                
        except Exception as e:
            logger.error(f"Error monitoring blocks: {e}")

    async def _analyze_competitors(self) -> None:
        """Analyze competitor behavior patterns."""
        try:
            while True:
                # Group transactions by sender
                sender_txs = defaultdict(list)
                for tx in self.recent_transactions:
                    sender_txs[tx['transaction']['from']].append(tx)
                
                # Analyze each sender's pattern
                for sender, txs in sender_txs.items():
                    if len(txs) < 10:  # Need minimum sample size
                        continue
                    
                    # Calculate metrics
                    success_rate = sum(1 for tx in txs if tx['success']) / len(txs)
                    avg_gas = np.mean([tx['transaction']['gas'] for tx in txs])
                    avg_time = np.mean([
                        (tx['timestamp'] - datetime.fromtimestamp(
                            self.web3_manager.w3.eth.get_block(
                                tx['block_number'] - 1
                            )['timestamp']
                        )).total_seconds()
                        for tx in txs
                    ])
                    
                    # Update competitor patterns
                    self.competitor_patterns[sender] = {
                        'success_rate': success_rate,
                        'avg_gas_usage': avg_gas,
                        'avg_execution_time': avg_time,
                        'transaction_count': len(txs),
                        'last_seen': max(tx['timestamp'] for tx in txs)
                    }
                    
                    # Add to known competitors if pattern suggests arbitrage bot
                    if (
                        success_rate > 0.8 and  # High success rate
                        avg_time < 2.0 and  # Fast execution
                        len(txs) > 50  # Regular activity
                    ):
                        self.known_competitors.add(sender)
                
                await asyncio.sleep(60)  # Update every minute
                
        except Exception as e:
            logger.error(f"Error analyzing competitors: {e}")

    async def _detect_reorgs(self) -> None:
        """Detect and handle block reorganizations."""
        try:
            last_block = await self.web3_manager.w3.eth.block_number
            block_hashes = {}
            
            while True:
                current_block = await self.web3_manager.w3.eth.block_number
                
                # Check new blocks
                for block_num in range(last_block + 1, current_block + 1):
                    block = await self.web3_manager.w3.eth.get_block(block_num)
                    block_hashes[block_num] = {
                        'hash': block['hash'].hex(),
                        'parent': block['parentHash'].hex(),
                        'timestamp': datetime.now()
                    }
                
                # Check for reorgs
                for block_num in range(last_block, current_block):
                    if block_num in block_hashes:
                        block = await self.web3_manager.w3.eth.get_block(block_num)
                        if block['hash'].hex() != block_hashes[block_num]['hash']:
                            # Reorg detected
                            self.block_reorgs.append({
                                'block_number': block_num,
                                'old_hash': block_hashes[block_num]['hash'],
                                'new_hash': block['hash'].hex(),
                                'timestamp': datetime.now()
                            })
                            logger.warning(f"Block reorg detected at block {block_num}")
                
                # Clean old data
                cutoff = current_block - self.max_blocks_history
                block_hashes = {
                    num: data for num, data in block_hashes.items()
                    if num > cutoff
                }
                
                last_block = current_block
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error detecting reorgs: {e}")

    async def _is_relevant_transaction(self, tx: Dict[str, Any]) -> bool:
        """Check if transaction is relevant for monitoring."""
        try:
            if not tx['to']:
                return False
                
            # Get DEX by router address
            dex = self.dex_manager.get_dex_by_address(tx['to'])
            if dex:
                try:
                    # Decode transaction input
                    decoded = dex.decode_function_input(tx['input'])
                    # Check if it's a swap function
                    return any(
                        name in decoded[0].fn_name.lower()
                        for name in ['swap', 'exactinput', 'exactoutput']
                    )
                except Exception:
                    pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking transaction relevance: {e}")
            return False

    async def _predict_transaction_success(
        self,
        tx: Dict[str, Any]
    ) -> Tuple[float, Dict[str, Any]]:
        """Predict transaction success probability."""
        try:
            # Extract transaction features
            features = {
                'gas_price': tx['gasPrice'],
                'gas_limit': tx['gas'],
                'nonce': tx['nonce'],
                'value': tx['value'],
                'input_length': len(tx['input']),
                'to_dex': tx['to'].lower() if tx['to'] else None
            }
            
            # Get current market conditions
            market_conditions = await self.ml_system.analyze_market_conditions()
            
            # Combine features
            prediction_input = {
                **features,
                'market_volatility': market_conditions['volatility'].get(
                    self.dex_manager.get_dex_by_address(tx['to']).name
                    if tx['to'] else '',
                    0
                ),
                'competition_rate': market_conditions['competition']['rate']
            }
            
            # Get prediction
            success_prob, importance = await self.ml_system.predict_trade_success(
                prediction_input
            )
            
            return success_prob, importance
            
        except Exception as e:
            logger.error(f"Error predicting transaction success: {e}")
            return 0.5, {}

    async def _check_transaction_success(self, tx: Dict[str, Any]) -> bool:
        """Check if transaction was successful."""
        try:
            receipt = await self.web3_manager.w3.eth.get_transaction_receipt(tx['hash'])
            return receipt['status'] == 1
            
        except Exception as e:
            logger.error(f"Error checking transaction success: {e}")
            return False

    async def _update_competitor_metrics(self, tx: Dict[str, Any]) -> None:
        """Update metrics for competitor transaction."""
        try:
            sender = tx['from']
            
            # Update execution time
            block = await self.web3_manager.w3.eth.get_block(tx['blockNumber'])
            prev_block = await self.web3_manager.w3.eth.get_block(tx['blockNumber'] - 1)
            execution_time = block['timestamp'] - prev_block['timestamp']
            self.execution_times[sender].append(execution_time)
            
            # Update success rate
            success = await self._check_transaction_success(tx)
            self.success_rates[sender].append(success)
            
            # Update gas usage
            self.gas_usage[sender].append(tx['gas'])
            
            # Trim old data
            max_history = 1000
            if len(self.execution_times[sender]) > max_history:
                self.execution_times[sender] = self.execution_times[sender][-max_history:]
            if len(self.success_rates[sender]) > max_history:
                self.success_rates[sender] = self.success_rates[sender][-max_history:]
            if len(self.gas_usage[sender]) > max_history:
                self.gas_usage[sender] = self.gas_usage[sender][-max_history:]
            
        except Exception as e:
            logger.error(f"Error updating competitor metrics: {e}")

    async def _save_monitoring_data(self) -> None:
        """Periodically save monitoring data."""
        try:
            while True:
                # Create monitoring report
                report = {
                    'timestamp': datetime.now().isoformat(),
                    'competitor_patterns': self.competitor_patterns,
                    'block_reorgs': self.block_reorgs[-100:],  # Last 100 reorgs
                    'performance_metrics': {
                        'execution_times': {
                            sender: np.mean(times)
                            for sender, times in self.execution_times.items()
                        },
                        'success_rates': {
                            sender: np.mean(rates)
                            for sender, rates in self.success_rates.items()
                        },
                        'gas_usage': {
                            sender: np.mean(usage)
                            for sender, usage in self.gas_usage.items()
                        }
                    }
                }
                
                # Save report
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = self.monitoring_dir / f"monitoring_{timestamp}.json"
                
                with open(file_path, 'w') as f:
                    json.dump(report, f, indent=2, cls=DateTimeEncoder)
                
                await asyncio.sleep(300)  # Save every 5 minutes
                
        except Exception as e:
            logger.error(f"Error saving monitoring data: {e}")

    async def _load_historical_data(self) -> None:
        """Load historical monitoring data."""
        try:
            # Find all monitoring files
            files = list(self.monitoring_dir.glob("monitoring_*.json"))
            
            for file_path in files:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
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
            logger.error(f"Error loading historical data: {e}")

async def create_transaction_monitor(
    web3_manager: Web3Manager,
    analytics: AnalyticsSystem,
    ml_system: MLSystem,
    dex_manager: DEXManager,
    monitoring_dir: Optional[str] = None,
    max_blocks_history: Optional[int] = None,
    mempool_refresh_rate: Optional[float] = None
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
            mempool_refresh_rate=mempool_refresh_rate or 0.1
        )
        return monitor
    except Exception as e:
        logger.error(f"Failed to create transaction monitor: {e}")
        return None
