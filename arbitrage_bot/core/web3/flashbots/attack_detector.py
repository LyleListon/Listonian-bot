"""
MEV Attack Detector for Flashbots Integration

This module provides functionality for:
- Detecting various types of MEV attacks
- Analyzing transaction patterns
- Tracking attack statistics
- Providing attack prevention recommendations
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal

from ....utils.async_manager import AsyncLock, with_retry

logger = logging.getLogger(__name__)

class AttackDetector:
    """Detects and analyzes MEV attacks."""

    def __init__(self, web3_manager, config: Dict[str, Any]):
        """
        Initialize attack detector.

        Args:
            web3_manager: Web3Manager instance
            config: Configuration dictionary containing:
                - mev_protection settings
                - detection thresholds
                - monitoring parameters
        """
        self.web3_manager = web3_manager
        self.config = config
        self._request_lock = AsyncLock()

        # Initialize detection parameters
        mev_config = config.get('mev_protection', {})
        self.sandwich_detection = mev_config.get('sandwich_detection', True)
        self.frontrun_detection = mev_config.get('frontrun_detection', True)
        self.backrun_detection = mev_config.get('backrun_detection', True)
        self.time_bandit_detection = mev_config.get('time_bandit_detection', True)

        # Initialize thresholds
        self.profit_threshold = Decimal(mev_config.get('profit_threshold', '0.1'))
        self.gas_threshold = Decimal(mev_config.get('gas_threshold', '1.5'))
        self.confidence_threshold = Decimal(mev_config.get('confidence_threshold', '0.7'))

        # Initialize statistics
        self._stats = {
            'total_attacks': 0,
            'attack_types': {},
            'high_risk_blocks': set(),
            'last_update': 0
        }

    @with_retry(retries=3, delay=1.0)
    async def scan_for_attacks(
        self,
        start_block: int,
        end_block: Optional[int] = None,
        attack_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scan blocks for MEV attacks.

        Args:
            start_block: Starting block number
            end_block: Optional ending block number
            attack_types: Optional list of attack types to scan for

        Returns:
            List of detected attacks
        """
        async with self._request_lock:
            try:
                if end_block is None:
                    end_block = await self.web3_manager.w3.eth.block_number

                if attack_types is None:
                    attack_types = ['sandwich', 'frontrun', 'backrun', 'time_bandit']

                attacks = []
                for block_num in range(start_block, end_block + 1):
                    block = await self.web3_manager.w3.eth.get_block(block_num, True)
                    block_attacks = await self._analyze_block(block, attack_types)
                    attacks.extend(block_attacks)

                # Update statistics
                self._update_attack_statistics(attacks)

                return attacks

            except Exception as e:
                logger.error(f"Failed to scan for attacks: {e}")
                raise

    async def get_attack_statistics(
        self,
        time_window: int = 3600  # 1 hour
    ) -> Dict[str, Any]:
        """
        Get attack statistics for a time window.

        Args:
            time_window: Time window in seconds

        Returns:
            Dict containing attack statistics
        """
        try:
            current_time = time.time()
            if current_time - self._stats['last_update'] > time_window:
                await self._refresh_statistics(time_window)

            return {
                'total_attacks': self._stats['total_attacks'],
                'attack_types': self._stats['attack_types'].copy(),
                'high_risk_blocks': len(self._stats['high_risk_blocks']),
                'time_window': time_window,
                'last_update': self._stats['last_update']
            }

        except Exception as e:
            logger.error(f"Failed to get attack statistics: {e}")
            raise

    async def _analyze_block(
        self,
        block: Dict[str, Any],
        attack_types: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze a block for MEV attacks."""
        attacks = []
        try:
            transactions = block.get('transactions', [])
            
            # Group transactions by token pairs
            token_groups = await self._group_transactions_by_tokens(transactions)
            
            for token_pair, txs in token_groups.items():
                if 'sandwich' in attack_types and self.sandwich_detection:
                    sandwich = await self._detect_sandwich_attack(txs, block)
                    if sandwich:
                        attacks.append(sandwich)
                
                if 'frontrun' in attack_types and self.frontrun_detection:
                    frontrun = await self._detect_frontrunning(txs, block)
                    if frontrun:
                        attacks.append(frontrun)
                
                if 'backrun' in attack_types and self.backrun_detection:
                    backrun = await self._detect_backrunning(txs, block)
                    if backrun:
                        attacks.append(backrun)
            
            if 'time_bandit' in attack_types and self.time_bandit_detection:
                time_bandit = await self._detect_time_bandit(block)
                if time_bandit:
                    attacks.append(time_bandit)

            return attacks

        except Exception as e:
            logger.error(f"Failed to analyze block {block.get('number')}: {e}")
            return []

    async def _group_transactions_by_tokens(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
        """Group transactions by token pairs."""
        groups = {}
        try:
            for tx in transactions:
                token_pair = await self._extract_token_pair(tx)
                if token_pair:
                    if token_pair not in groups:
                        groups[token_pair] = []
                    groups[token_pair].append(tx)
            return groups

        except Exception as e:
            logger.error(f"Failed to group transactions: {e}")
            return {}

    async def _detect_sandwich_attack(
        self,
        transactions: List[Dict[str, Any]],
        block: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Detect sandwich attacks in transactions."""
        try:
            for i in range(len(transactions) - 2):
                front_tx = transactions[i]
                victim_tx = transactions[i + 1]
                back_tx = transactions[i + 2]

                if await self._is_sandwich_pattern(front_tx, victim_tx, back_tx):
                    confidence = await self._calculate_sandwich_confidence(
                        front_tx,
                        victim_tx,
                        back_tx
                    )

                    if confidence >= self.confidence_threshold:
                        return {
                            'type': 'sandwich',
                            'block_number': block['number'],
                            'transactions': [
                                front_tx.get('hash').hex(),
                                victim_tx.get('hash').hex(),
                                back_tx.get('hash').hex()
                            ],
                            'severity': 'HIGH',
                            'confidence': float(confidence),
                            'timestamp': block['timestamp']
                        }
            return None

        except Exception as e:
            logger.error(f"Failed to detect sandwich attack: {e}")
            return None

    async def _detect_frontrunning(
        self,
        transactions: List[Dict[str, Any]],
        block: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Detect frontrunning attacks in transactions."""
        try:
            for i in range(len(transactions) - 1):
                front_tx = transactions[i]
                target_tx = transactions[i + 1]

                if await self._is_frontrun_pattern(front_tx, target_tx):
                    confidence = await self._calculate_frontrun_confidence(
                        front_tx,
                        target_tx
                    )

                    if confidence >= self.confidence_threshold:
                        return {
                            'type': 'frontrun',
                            'block_number': block['number'],
                            'transactions': [
                                front_tx.get('hash').hex(),
                                target_tx.get('hash').hex()
                            ],
                            'severity': 'MEDIUM',
                            'confidence': float(confidence),
                            'timestamp': block['timestamp']
                        }
            return None

        except Exception as e:
            logger.error(f"Failed to detect frontrunning: {e}")
            return None

    async def _detect_backrunning(
        self,
        transactions: List[Dict[str, Any]],
        block: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Detect backrunning attacks in transactions."""
        try:
            for i in range(len(transactions) - 1):
                target_tx = transactions[i]
                back_tx = transactions[i + 1]

                if await self._is_backrun_pattern(target_tx, back_tx):
                    confidence = await self._calculate_backrun_confidence(
                        target_tx,
                        back_tx
                    )

                    if confidence >= self.confidence_threshold:
                        return {
                            'type': 'backrun',
                            'block_number': block['number'],
                            'transactions': [
                                target_tx.get('hash').hex(),
                                back_tx.get('hash').hex()
                            ],
                            'severity': 'MEDIUM',
                            'confidence': float(confidence),
                            'timestamp': block['timestamp']
                        }
            return None

        except Exception as e:
            logger.error(f"Failed to detect backrunning: {e}")
            return None

    async def _detect_time_bandit(
        self,
        block: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Detect time bandit attacks."""
        try:
            # Time bandit attacks typically involve block reorganizations
            # This is a simplified detection that looks for suspicious block timing
            if 'timestamp' not in block or 'number' not in block:
                return None

            prev_block = await self.web3_manager.w3.eth.get_block(block['number'] - 1)
            time_diff = block['timestamp'] - prev_block['timestamp']

            if time_diff > 14:  # Suspicious block timing
                return {
                    'type': 'time_bandit',
                    'block_number': block['number'],
                    'severity': 'HIGH',
                    'confidence': 0.8,
                    'details': f"Suspicious block timing: {time_diff}s gap",
                    'timestamp': block['timestamp']
                }
            return None

        except Exception as e:
            logger.error(f"Failed to detect time bandit attack: {e}")
            return None

    async def _extract_token_pair(
        self,
        transaction: Dict[str, Any]
    ) -> Optional[Tuple[str, str]]:
        """Extract token pair from transaction data."""
        try:
            # This is a simplified implementation
            # In production, you would decode the transaction input data
            input_data = transaction.get('input', '')
            if len(input_data) < 138:  # Minimum length for a swap
                return None

            # Extract method signature and parameters
            method_sig = input_data[:10]
            if method_sig in ['0x38ed1739', '0x8803dbee']:  # Common swap methods
                # Extract token addresses from input data
                token0 = '0x' + input_data[34:74]
                token1 = '0x' + input_data[98:138]
                return (token0.lower(), token1.lower())

            return None

        except Exception as e:
            logger.error(f"Failed to extract token pair: {e}")
            return None

    async def _is_sandwich_pattern(
        self,
        front_tx: Dict[str, Any],
        victim_tx: Dict[str, Any],
        back_tx: Dict[str, Any]
    ) -> bool:
        """Check if transactions match sandwich attack pattern."""
        try:
            return (
                front_tx['gasPrice'] > victim_tx['gasPrice'] and
                back_tx['gasPrice'] > victim_tx['gasPrice'] and
                front_tx.get('from') == back_tx.get('from') and
                front_tx.get('from') != victim_tx.get('from')
            )
        except Exception:
            return False

    async def _is_frontrun_pattern(
        self,
        front_tx: Dict[str, Any],
        target_tx: Dict[str, Any]
    ) -> bool:
        """Check if transactions match frontrunning pattern."""
        try:
            return (
                front_tx['gasPrice'] > target_tx['gasPrice'] and
                front_tx.get('from') != target_tx.get('from')
            )
        except Exception:
            return False

    async def _is_backrun_pattern(
        self,
        target_tx: Dict[str, Any],
        back_tx: Dict[str, Any]
    ) -> bool:
        """Check if transactions match backrunning pattern."""
        try:
            return (
                back_tx['gasPrice'] >= target_tx['gasPrice'] and
                back_tx.get('from') != target_tx.get('from')
            )
        except Exception:
            return False

    def _update_attack_statistics(self, attacks: List[Dict[str, Any]]) -> None:
        """Update attack statistics."""
        try:
            self._stats['total_attacks'] += len(attacks)
            
            for attack in attacks:
                attack_type = attack['type']
                self._stats['attack_types'][attack_type] = (
                    self._stats['attack_types'].get(attack_type, 0) + 1
                )
                
                if attack['severity'] == 'HIGH':
                    self._stats['high_risk_blocks'].add(attack['block_number'])
            
            self._stats['last_update'] = time.time()

        except Exception as e:
            logger.error(f"Failed to update attack statistics: {e}")

    async def _refresh_statistics(self, time_window: int) -> None:
        """Refresh attack statistics for time window."""
        try:
            current_block = await self.web3_manager.w3.eth.block_number
            blocks_in_window = time_window // 12  # Assuming 12-second block time
            start_block = max(0, current_block - blocks_in_window)

            # Reset statistics
            self._stats = {
                'total_attacks': 0,
                'attack_types': {},
                'high_risk_blocks': set(),
                'last_update': time.time()
            }

            # Scan blocks in window
            await self.scan_for_attacks(start_block, current_block)

        except Exception as e:
            logger.error(f"Failed to refresh statistics: {e}")