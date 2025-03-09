"""
Unified Flash Loan Manager Module

This module provides functionality for:
- Flash loan execution
- Flash loan validation
- Profit calculation
- Multi-path support
"""

import logging
import asyncio
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from eth_typing import ChecksumAddress
from web3 import Web3

from ..utils.async_manager import with_retry, AsyncLock
from .web3.interfaces import Web3Client, Transaction
from .dex.dex_manager import DexManager
from .web3.balance_validator import BalanceValidator
from .web3.flashbots.flashbots_provider import FlashbotsProvider
from .path_finder import ArbitragePath

logger = logging.getLogger(__name__)

class UnifiedFlashLoanManager:
    """Manages flash loan operations with multi-path support."""

    def __init__(
        self,
        web3_manager: Web3Client,
        dex_manager: DexManager,
        balance_validator: BalanceValidator,
        flashbots_provider: FlashbotsProvider,
        balancer_vault: ChecksumAddress,
        min_profit: int = 0,
        max_parallel_pools: int = 10,
        min_liquidity_ratio: float = 1.5  # Require 150% of flash loan amount in liquidity
    ):
        """
        Initialize flash loan manager.

        Args:
            web3_manager: Web3 client instance
            dex_manager: DEX manager instance
            balance_validator: Balance validator instance
            flashbots_provider: Flashbots provider instance
            balancer_vault: Balancer vault address
            min_profit: Minimum profit required (in wei)
            max_parallel_pools: Maximum number of pools to scan in parallel
            min_liquidity_ratio: Minimum ratio of pool liquidity to flash loan amount
        """
        self.web3_manager = web3_manager
        self.dex_manager = dex_manager
        self.balance_validator = balance_validator
        self.flashbots_provider = flashbots_provider
        self.balancer_vault = balancer_vault
        self.min_profit = min_profit
        self.max_parallel_pools = max_parallel_pools
        self.min_liquidity_ratio = min_liquidity_ratio

        # Initialize locks
        self._validation_lock = AsyncLock()
        self._execution_lock = AsyncLock()

        # Initialize cache
        self._liquidity_cache: Dict[str, Tuple[int, int]] = {}  # (amount, timestamp)
        self._cache_ttl = 30  # 30 seconds

        logger.info(
            f"Flash loan manager initialized with min profit: {min_profit}"
        )

    async def _get_pool_liquidity(
        self,
        pool_addresses: Set[ChecksumAddress]
    ) -> Dict[ChecksumAddress, int]:
        """Get liquidity for multiple pools in parallel."""
        async def check_single_pool(pool: ChecksumAddress) -> Tuple[ChecksumAddress, int]:
            try:
                # Check cache first
                cache_entry = self._liquidity_cache.get(pool)
                if cache_entry:
                    amount, timestamp = cache_entry
                    if timestamp + self._cache_ttl > int(self.web3_manager.w3.eth.get_block('latest')['timestamp']):
                        return pool, amount

                liquidity = await self.dex_manager.get_pool_liquidity(pool)

                # Update cache
                self._liquidity_cache[pool] = (
                    liquidity,
                    int(self.web3_manager.w3.eth.get_block('latest')['timestamp'])
                )

                return pool, liquidity
            except Exception as e:
                logger.error(f"Failed to get liquidity for pool {pool}: {e}")
                return pool, 0

        # Process pools in batches
        results = {}
        for i in range(0, len(pool_addresses), self.max_parallel_pools):
            batch = list(pool_addresses)[i:i + self.max_parallel_pools]
            batch_results = await asyncio.gather(*[
                check_single_pool(pool)
                for pool in batch
            ])
            results.update(dict(batch_results))

        return results

    @with_retry(retries=3, delay=1.0)
    async def validate_flash_loan(
        self,
        token_address: ChecksumAddress,
        amount: int,
        expected_profit: int,
        path: Optional[ArbitragePath] = None
    ) -> bool:
        """
        Validate flash loan parameters.

        Args:
            token_address: Token address
            amount: Flash loan amount
            expected_profit: Expected profit
            path: Optional arbitrage path for validation

        Returns:
            True if valid, False otherwise
        """
        try:
            async with self._validation_lock:
                # Check token balance
                balance = await self.balance_validator.get_token_balance(
                    token_address=token_address
                )

                if balance < amount:
                    logger.warning(
                        f"Insufficient balance: {balance} < {amount}"
                    )
                    return False

                # Check minimum profit
                if expected_profit < self.min_profit:
                    logger.warning(
                        f"Profit too low: {expected_profit} < {self.min_profit}"
                    )
                    return False

                # Get pool addresses from path if provided
                pool_addresses = set()
                if path:
                    pool_addresses = {step.pool_address for step in path.steps if step.pool_address}

                # Check liquidity in all pools
                pool_liquidity = await self._get_pool_liquidity(pool_addresses)

                required_liquidity = amount * self.min_liquidity_ratio
                for pool, liquidity in pool_liquidity.items():
                    if liquidity < required_liquidity:
                        logger.warning(
                            f"Insufficient liquidity in pool {pool}: "
                            f"{liquidity} < {required_liquidity}"
                        )
                        return False

                # Validate price impact if path provided
                if path:
                    total_price_impact = 0
                    for step in path.steps:
                        impact = await self.dex_manager.calculate_price_impact(
                            step.dex,
                            step.pool_address,
                            step.amount_in
                        )
                        total_price_impact += impact

                    if total_price_impact > 0.05:  # 5% max price impact
                        logger.warning(
                            f"Price impact too high: {total_price_impact * 100}%"
                        )
                        return False

                return True

        except Exception as e:
            logger.error(f"Error validating flash loan: {e}")
            return False

    @with_retry(retries=3, delay=1.0)
    async def execute_flash_loan(
        self,
        token_address: ChecksumAddress,
        amount: int,
        target_contract: ChecksumAddress,
        callback_data: bytes,
        path: Optional[ArbitragePath] = None
    ) -> Dict[str, Any]:
        """
        Execute flash loan with optional path-specific optimization.

        Args:
            token_address: Token address
            amount: Flash loan amount
            target_contract: Target contract address
            callback_data: Callback data
            path: Optional arbitrage path for optimization

        Returns:
            Result dictionary with success status and transaction hash
        """
        try:
            async with self._execution_lock:
                # Validate parameters
                if not await self.validate_flash_loan(
                    token_address=token_address,
                    amount=amount,
                    expected_profit=self.min_profit,
                    path=path
                ):
                    return {
                        'success': False,
                        'error': 'Flash loan validation failed'
                    }

                # Create flash loan transaction
                flash_loan_tx = {
                    'to': self.balancer_vault,
                    'value': 0,
                    'data': self.web3_manager.w3.eth.abi.encode_abi(
                        [
                            'function flashLoan('
                            'address recipient,'
                            'address token,'
                            'uint256 amount,'
                            'bytes calldata data'
                            ')'
                        ],
                        [
                            target_contract,
                            token_address,
                            amount,
                            callback_data
                        ]
                    )
                }

                # Create transaction bundle
                transactions = [Transaction(flash_loan_tx)]

                # Add path-specific transactions if provided
                if path:
                    for step in path.steps:
                        swap_tx = await self.dex_manager.build_swap_transaction(
                            step.dex,
                            step.token_in,
                            step.token_out,
                            step.amount_in,
                            step.amount_out * 0.99  # 1% slippage tolerance
                        )
                        transactions.append(Transaction(swap_tx))

                # Simulate bundle
                simulation = await self.flashbots_provider.simulate_bundle(
                    transactions=transactions
                )

                if not simulation['success']:
                    return {
                        'success': False,
                        'error': simulation.get('error', 'Simulation failed')
                    }

                # Send bundle through Flashbots
                bundle_hash = await self.flashbots_provider.send_bundle(
                    transactions=transactions
                )

                return {
                    'success': True,
                    'bundle_hash': bundle_hash,
                    'gas_used': simulation['gasUsed'],
                    'profit': simulation['profitability']
                }

        except Exception as e:
            logger.error(f"Error executing flash loan: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def close(self):
        """Clean up resources."""
        self._liquidity_cache.clear()

async def create_unified_flash_loan_manager(
    web3_manager: Web3Client,
    dex_manager: DexManager,
    balance_validator: BalanceValidator,
    flashbots_provider: FlashbotsProvider,
    config: Dict[str, Any]
) -> UnifiedFlashLoanManager:
    """
    Create a new flash loan manager.

    Args:
        web3_manager: Web3 client instance
        dex_manager: DEX manager instance
        balance_validator: Balance validator instance
        flashbots_provider: Flashbots provider instance
        config: Configuration dictionary

    Returns:
        UnifiedFlashLoanManager instance
    """
    # Convert min_profit from ETH to wei
    min_profit_eth = Decimal(config['flash_loan']['min_profit'])
    min_profit_wei = web3_manager.w3.to_wei(min_profit_eth, 'ether')

    return UnifiedFlashLoanManager(
        web3_manager=web3_manager,
        dex_manager=dex_manager,
        balance_validator=balance_validator,
        flashbots_provider=flashbots_provider,
        balancer_vault=config['flash_loan']['balancer_vault'],
        min_profit=min_profit_wei,
        max_parallel_pools=config['flash_loan'].get('max_parallel_pools', 10),
        min_liquidity_ratio=config['flash_loan'].get('min_liquidity_ratio', 1.5)
    )
