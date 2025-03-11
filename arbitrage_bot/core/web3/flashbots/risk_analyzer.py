"""
Risk Analyzer for Flashbots Integration

This module provides functionality for:
- Analyzing mempool for MEV risks
- Detecting potential MEV attacks
- Tracking risk statistics
- Providing risk mitigation recommendations
"""

import logging
import time
from typing import Dict, List, Any, Optional
from decimal import Decimal

from ....utils.async_manager import AsyncLock, with_retry
from ..web3_manager import Web3Error

logger = logging.getLogger(__name__)

class RiskAnalyzer:
    """Analyzes and manages MEV-related risks."""

    def __init__(self, web3_manager, config: Dict[str, Any]):
        """
        Initialize risk analyzer.

        Args:
            web3_manager: Web3Manager instance
            config: Configuration dictionary containing:
                - mev_protection settings
                - gas price thresholds
                - risk parameters
        """
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        self._request_lock = AsyncLock()
        
        # Initialize risk parameters
        self.max_bundle_size = config.get('mev_protection', {}).get('max_bundle_size', 5)
        self.max_blocks_ahead = config.get('mev_protection', {}).get('max_blocks_ahead', 3)
        self.min_priority_fee = Decimal(config.get('mev_protection', {}).get('min_priority_fee', '1.5'))
        self.max_priority_fee = Decimal(config.get('mev_protection', {}).get('max_priority_fee', '3'))
        
        # Initialize attack detection flags
        self.sandwich_detection = config.get('mev_protection', {}).get('sandwich_detection', True)
        self.frontrun_detection = config.get('mev_protection', {}).get('frontrun_detection', True)
        self.adaptive_gas = config.get('mev_protection', {}).get('adaptive_gas', True)

        # Initialize statistics
        self._stats = {
            'total_attacks': 0,
            'attack_types': {},
            'risk_level': 'LOW',
            'last_update': 0
        }

    def _parse_hex_or_int(self, value: Any, default: int = 0) -> int:
        """Parse a value that could be hex string or int."""
        try:
            if isinstance(value, str):
                if value.startswith('0x'):
                    return int(value, 16)
                return int(value)
            return int(value)
        except (ValueError, TypeError):
            return default

    @with_retry(retries=3, delay=1.0)
    async def analyze_mempool_risk(self) -> Dict[str, Any]:
        """
        Analyze current mempool for MEV risks.

        Returns:
            Dict containing:
                - risk_level: Current risk level (LOW, MEDIUM, HIGH)
                - gas_price: Current gas price
                - avg_gas_price: Average gas price
                - gas_volatility: Gas price volatility
                - risk_factors: List of identified risk factors
        """
        async with self._request_lock:
            try:
                # Get current gas price
                gas_price = await self.web3_manager.get_gas_price()
                gas_price = self._parse_hex_or_int(gas_price)
                
                # Get latest block and await the result
                block_result = await self.web3_manager.get_block('latest')
                if not block_result:
                    raise ValueError("Failed to get latest block")
                    
                # Parse base fee from hex if needed
                base_fee = block_result.get('baseFeePerGas', '0x0')
                base_fee = self._parse_hex_or_int(base_fee)

                # Calculate gas price statistics
                avg_gas_price = await self._calculate_average_gas_price()
                volatility = self._calculate_gas_volatility(gas_price, avg_gas_price)

                # Identify risk factors
                risk_factors = []
                if volatility > 0.2:
                    risk_factors.append('High gas price volatility')
                if gas_price > avg_gas_price * 1.5:
                    risk_factors.append('Gas price spike')

                # Determine risk level
                risk_level = self._determine_risk_level(risk_factors, volatility)

                return {
                    'risk_level': risk_level,
                    'gas_price': gas_price,
                    'avg_gas_price': avg_gas_price,
                    'gas_volatility': volatility,
                    'risk_factors': risk_factors,
                    'base_fee': base_fee
                }

            except Web3Error as e:
                logger.error(f"Web3 error in analyze_mempool_risk: {e}")
                raise

            except Exception as e:
                logger.error(f"Failed to analyze mempool risk: {e}")
                raise

    async def detect_mev_attacks(self, blocks: int = 10) -> List[Dict[str, Any]]:
        """
        Detect potential MEV attacks in recent blocks.

        Args:
            blocks: Number of recent blocks to analyze

        Returns:
            List of detected attacks, each containing:
                - type: Attack type
                - severity: Attack severity
                - block_number: Block where attack was detected
                - details: Attack details
                - confidence: Detection confidence
        """
        attacks = []
        try:
            current_block = await self.web3_manager.get_block_number()
            
            for block_number in range(current_block - blocks, current_block + 1):
                # Get block and await the result
                block_result = await self.web3_manager.get_block(block_number)
                if not block_result:
                    continue
                
                if self.sandwich_detection:
                    sandwich = await self._detect_sandwich_attack(block_result)
                    if sandwich:
                        attacks.append(sandwich)
                
                if self.frontrun_detection:
                    frontrun = await self._detect_frontrunning(block_result)
                    if frontrun:
                        attacks.append(frontrun)

            # Update statistics
            self._update_attack_statistics(attacks)
            
            return attacks

        except Exception as e:
            logger.error(f"Failed to detect MEV attacks: {e}")
            return []

    async def get_mev_attack_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about detected MEV attacks.

        Returns:
            Dict containing:
                - total_attacks: Total number of attacks detected
                - attack_types: Count of each attack type
                - risk_level: Current risk level
                - recommendation: Risk mitigation recommendation
        """
        stats = self._stats.copy()
        stats['recommendation'] = self._generate_recommendation(stats)
        return stats

    async def _calculate_average_gas_price(self) -> int:
        """Calculate average gas price over recent blocks."""
        try:
            current_block = await self.web3_manager.get_block_number()
            prices = []
            
            for block_number in range(current_block - 10, current_block + 1):
                # Get block and await the result
                block_result = await self.web3_manager.get_block(block_number)
                if block_result:
                    base_fee = block_result.get('baseFeePerGas', '0x0')
                    base_fee = self._parse_hex_or_int(base_fee)
                    prices.append(base_fee)
            
            return sum(prices) // len(prices) if prices else 0

        except Exception as e:
            logger.error(f"Failed to calculate average gas price: {e}")
            return 0

    def _calculate_gas_volatility(self, current: int, average: int) -> float:
        """Calculate gas price volatility."""
        if average == 0:
            return 0
        return abs(current - average) / average

    def _determine_risk_level(self, risk_factors: List[str], volatility: float) -> str:
        """Determine overall risk level."""
        if len(risk_factors) >= 2 or volatility > 0.3:
            return 'HIGH'
        elif len(risk_factors) == 1 or volatility > 0.2:
            return 'MEDIUM'
        return 'LOW'

    async def _detect_sandwich_attack(self, block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect potential sandwich attacks in a block."""
        try:
            txs = block.get('transactions', [])
            for i in range(len(txs) - 2):
                tx_group = txs[i:i+3]
                if await self._is_sandwich_pattern(tx_group):
                    return {
                        'type': 'sandwich',
                        'severity': 'HIGH',
                        'block_number': block['number'],
                        'details': f"Potential sandwich attack detected in block {block['number']}",
                        'confidence': 0.85
                    }
            return None

        except Exception as e:
            logger.error(f"Failed to detect sandwich attack: {e}")
            return None

    async def _detect_frontrunning(self, block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect potential frontrunning in a block."""
        try:
            txs = block.get('transactions', [])
            for i in range(len(txs) - 1):
                tx_pair = txs[i:i+2]
                if await self._is_frontrun_pattern(tx_pair):
                    return {
                        'type': 'frontrun',
                        'severity': 'MEDIUM',
                        'block_number': block['number'],
                        'details': f"Potential frontrunning detected in block {block['number']}",
                        'confidence': 0.75
                    }
            return None

        except Exception as e:
            logger.error(f"Failed to detect frontrunning: {e}")
            return None

    async def _is_sandwich_pattern(self, txs: List[Dict[str, Any]]) -> bool:
        """Check if transactions match sandwich attack pattern."""
        if len(txs) != 3:
            return False
        
        try:
            # Check for similar token pairs and increasing gas prices
            gas_prices = []
            for tx in txs:
                if isinstance(tx, dict):
                    gas_price = tx.get('gasPrice', '0x0')
                    gas_price = self._parse_hex_or_int(gas_price)
                    gas_prices.append(gas_price)
                else:
                    return False
                    
            if not all(gas_prices):
                return False
                
            return (
                gas_prices[0] > gas_prices[1] and
                gas_prices[2] > gas_prices[1] and
                await self._share_token_pair(txs[0], txs[2])
            )
        except Exception:
            return False

    async def _is_frontrun_pattern(self, txs: List[Dict[str, Any]]) -> bool:
        """Check if transactions match frontrunning pattern."""
        if len(txs) != 2:
            return False
        
        try:
            # Check for similar operations and higher gas price
            gas_prices = []
            for tx in txs:
                if isinstance(tx, dict):
                    gas_price = tx.get('gasPrice', '0x0')
                    gas_price = self._parse_hex_or_int(gas_price)
                    gas_prices.append(gas_price)
                else:
                    return False
                    
            if not all(gas_prices):
                return False
                
            return (
                gas_prices[0] > gas_prices[1] and
                await self._share_token_pair(txs[0], txs[1])
            )
        except Exception:
            return False

    async def _share_token_pair(self, tx1: Dict[str, Any], tx2: Dict[str, Any]) -> bool:
        """Check if two transactions share the same token pair."""
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

    def _update_attack_statistics(self, attacks: List[Dict[str, Any]]) -> None:
        """Update attack statistics."""
        self._stats['total_attacks'] += len(attacks)
        
        for attack in attacks:
            attack_type = attack['type']
            self._stats['attack_types'][attack_type] = (
                self._stats['attack_types'].get(attack_type, 0) + 1
            )
        
        self._stats['last_update'] = time.time()

    def _generate_recommendation(self, stats: Dict[str, Any]) -> str:
        """Generate risk mitigation recommendation based on statistics."""
        if stats['risk_level'] == 'HIGH':
            return (
                "High MEV risk detected. Recommend using private transactions, "
                "increasing priority fees, and implementing additional slippage protection."
            )
        elif stats['risk_level'] == 'MEDIUM':
            return (
                "Moderate MEV risk. Consider using Flashbots bundles and "
                "implementing basic slippage protection."
            )
        return (
            "Low MEV risk. Standard Flashbots protection should be sufficient."
        )