"""
Attack Detector for Flashbots Integration

This module provides functionality for:
- Detecting potential MEV attacks
- Analyzing transaction patterns
- Monitoring suspicious activity
"""

import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal

from ....utils.async_manager import AsyncLock, with_retry

logger = logging.getLogger(__name__)

class AttackDetector:
    """Detects and analyzes potential MEV attacks."""

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
        self.w3 = web3_manager.w3
        self.config = config
        self._request_lock = AsyncLock()

        # Initialize detection parameters
        self.sandwich_threshold = config.get('mev_protection', {}).get('sandwich_threshold', 0.85)
        self.frontrun_threshold = config.get('mev_protection', {}).get('frontrun_threshold', 0.75)
        self.max_time_diff = config.get('mev_protection', {}).get('max_time_diff', 2)

    @with_retry(retries=3, delay=1.0)
    async def scan_for_attacks(self, start_block: Optional[int] = None, blocks_to_scan: int = 10) -> List[Dict[str, Any]]:
        """
        Scan recent blocks for potential MEV attacks.

        Args:
            start_block: Optional starting block number. If not provided, uses (current - blocks_to_scan)
            blocks_to_scan: Number of blocks to scan

        Returns:
            List of detected attacks, each containing:
                - type: Attack type
                - severity: Attack severity
                - block_number: Block where attack was detected
                - details: Attack details
                - confidence: Detection confidence
        """
        async with self._request_lock:
            try:
                # Get current block number
                end_block = await self.web3_manager.get_block_number()
                
                # Calculate start block if not provided
                if start_block is None:
                    start_block = end_block - blocks_to_scan

                attacks = []
                for block_num in range(start_block, end_block + 1):
                    block = await self.web3_manager.get_block(block_num, True)
                    block_attacks = await self._analyze_block(block)
                    if block_attacks:
                        attacks.extend(block_attacks)

                return attacks

            except Exception as e:
                logger.error(f"Failed to scan for attacks: {e}")
                raise

    async def _analyze_block(self, block: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze a block for potential attacks.

        Args:
            block: Block data including transactions

        Returns:
            List of detected attacks in the block
        """
        attacks = []
        try:
            txs = block.get('transactions', [])
            
            # Check for sandwich attacks
            for i in range(len(txs) - 2):
                if await self._is_sandwich_pattern(txs[i:i+3]):
                    attacks.append({
                        'type': 'sandwich',
                        'severity': 'HIGH',
                        'block_number': block['number'],
                        'details': f"Potential sandwich attack detected in block {block['number']}",
                        'confidence': self.sandwich_threshold
                    })

            # Check for frontrunning
            for i in range(len(txs) - 1):
                if await self._is_frontrun_pattern(txs[i:i+2]):
                    attacks.append({
                        'type': 'frontrun',
                        'severity': 'MEDIUM',
                        'block_number': block['number'],
                        'details': f"Potential frontrunning detected in block {block['number']}",
                        'confidence': self.frontrun_threshold
                    })

            # Analyze timing patterns
            if len(txs) > 1:
                block_num = int(block['number'], 16) if isinstance(block['number'], str) else block['number']
                prev_block = await self.web3_manager.get_block(block_num - 1)
                
                # Convert timestamps to integers
                current_timestamp = int(block['timestamp'], 16) if isinstance(block['timestamp'], str) else block['timestamp']
                prev_timestamp = int(prev_block['timestamp'], 16) if isinstance(prev_block['timestamp'], str) else prev_block['timestamp']
                
                time_diff = current_timestamp - prev_timestamp
                
                if time_diff < self.max_time_diff:
                    attacks.append({
                        'type': 'timing',
                        'severity': 'LOW',
                        'block_number': block['number'],
                        'details': f"Suspicious block timing detected: {time_diff}s",
                        'confidence': 0.6
                    })

            return attacks

        except Exception as e:
            logger.error(f"Failed to analyze block {block.get('number')}: {e}")
            return []

    async def _is_sandwich_pattern(self, txs: List[Dict[str, Any]]) -> bool:
        """
        Check if transactions match sandwich attack pattern.

        Args:
            txs: List of 3 consecutive transactions

        Returns:
            True if pattern matches sandwich attack
        """
        if len(txs) != 3:
            return False

        try:
            # Check for typical sandwich pattern:
            # 1. High gas price buy
            # 2. Target transaction
            # 3. High gas price sell
            return (
                txs[0]['gasPrice'] > txs[1]['gasPrice'] and
                txs[2]['gasPrice'] > txs[1]['gasPrice'] and
                await self._share_token_pair(txs[0], txs[2])
            )
        except Exception:
            return False

    async def _is_frontrun_pattern(self, txs: List[Dict[str, Any]]) -> bool:
        """
        Check if transactions match frontrunning pattern.

        Args:
            txs: List of 2 consecutive transactions

        Returns:
            True if pattern matches frontrunning
        """
        if len(txs) != 2:
            return False

        try:
            # Check for typical frontrunning pattern:
            # 1. High gas price copy of target tx
            # 2. Target transaction
            return (
                txs[0]['gasPrice'] > txs[1]['gasPrice'] and
                await self._share_token_pair(txs[0], txs[1])
            )
        except Exception:
            return False

    async def _share_token_pair(self, tx1: Dict[str, Any], tx2: Dict[str, Any]) -> bool:
        """
        Check if two transactions share the same token pair.

        Args:
            tx1: First transaction
            tx2: Second transaction

        Returns:
            True if transactions involve the same token pair
        """
        try:
            # This is a simplified check - in production, you'd decode the transaction
            # input data to determine the actual tokens being traded
            return (
                tx1.get('to') == tx2.get('to') and
                len(tx1.get('input', '')) > 10 and
                len(tx2.get('input', '')) > 10
            )
        except Exception:
            return False