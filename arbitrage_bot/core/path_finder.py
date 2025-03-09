"""
Path Finder Module

This module contains the PathFinder class for finding optimal arbitrage paths across multiple DEXs.
Supports multi-path arbitrage with parallel price fetching and gas optimization.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from decimal import Decimal
from dataclasses import dataclass
from eth_typing import ChecksumAddress
from web3 import Web3

from ..utils.async_manager import AsyncLock

logger = logging.getLogger(__name__)

@dataclass
class PathStep:
    """Represents a single step in an arbitrage path."""
    dex: str
    token_in: ChecksumAddress
    token_out: ChecksumAddress
    amount_in: int
    amount_out: int
    fee: int
    pool_address: Optional[ChecksumAddress] = None

class ArbitragePath:
    """Represents a potential arbitrage path across multiple DEXs."""

    def __init__(self,
                 path_id: str,
                 input_token: ChecksumAddress,
                 output_token: ChecksumAddress,
                 amount_in: int,
                 expected_output: int,
                 profit: int,
                 steps: List[PathStep],
                 profit_margin: float,
                 gas_estimate: int):
        """
        Initialize an arbitrage path.

        Args:
            path_id: Unique identifier for this path
            input_token: Address of the input token
            output_token: Address of the output token
            amount_in: Amount of input token in wei
            expected_output: Expected amount of output token in wei
            profit: Expected profit in wei
            steps: List of steps in the arbitrage route
            profit_margin: Profit margin as a decimal (e.g., 0.02 for 2%)
            gas_estimate: Estimated gas cost for executing this path
        """
        self.id = path_id
        self.input_token = input_token
        self.output_token = output_token
        self.amount_in = amount_in
        self.expected_output = expected_output
        self.profit = profit
        self.steps = steps
        self.profit_margin = profit_margin
        self.gas_estimate = gas_estimate

        # Calculate metrics
        self.total_fee = sum(step.fee for step in steps)
        self.path_length = len(steps)
        self.net_profit = profit - (gas_estimate * Web3.to_wei(50, 'gwei'))  # Assume 50 gwei gas price

    def to_dict(self) -> Dict[str, Any]:
        """Convert the arbitrage path to a dictionary."""
        return {
            "id": self.id,
            "input_token": self.input_token,
            "output_token": self.output_token,
            "amount_in": self.amount_in,
            "expected_output": self.expected_output,
            "profit": self.profit,
            "net_profit": self.net_profit,
            "steps": [
                {
                    "dex": step.dex,
                    "token_in": step.token_in,
                    "token_out": step.token_out,
                    "amount_in": step.amount_in,
                    "amount_out": step.amount_out,
                    "fee": step.fee,
                    "pool_address": step.pool_address
                }
                for step in self.steps
            ],
            "profit_margin": self.profit_margin,
            "gas_estimate": self.gas_estimate,
            "total_fee": self.total_fee,
            "path_length": self.path_length
        }

class PathFinder:
    """Finds optimal arbitrage paths across multiple DEXs."""

    def __init__(self, dex_manager, config=None, web3_manager=None):
        """
        Initialize the PathFinder.

        Args:
            dex_manager: DexManager instance for DEX interactions
            config: Configuration dictionary
            web3_manager: Web3Manager instance for blockchain interactions
        """
        self.dex_manager = dex_manager
        self.web3_manager = web3_manager
        self.config = config or {}

        # Extract configuration settings
        self.max_paths_to_check = self.config.get('max_paths_to_check', 100)
        self.min_profit_threshold = self.config.get('min_profit_threshold', 0.001)
        self.max_path_length = self.config.get('max_path_length', 4)
        self.max_parallel_requests = self.config.get('max_parallel_requests', 10)
        self.min_liquidity_usd = self.config.get('min_liquidity_usd', 10000)

        # Initialize locks
        self._price_lock = AsyncLock()

        # Initialize statistics
        self.total_paths_analyzed = 0
        self.profitable_paths_found = 0
        self.max_profit_seen = 0.0
        self.average_path_length = 0.0
        self._total_length_sum = 0

        logger.info("Initialized PathFinder with max path length %d", self.max_path_length)

    async def _get_prices_parallel(
        self,
        token_pairs: List[Tuple[str, str, str]],  # [(dex, token_in, token_out)]
        amount: int
    ) -> Dict[Tuple[str, str, str], int]:
        """Get prices for multiple token pairs in parallel."""
        async def get_single_price(dex: str, token_in: str, token_out: str) -> Tuple[Tuple[str, str, str], int]:
            try:
                price = await self.dex_manager.get_price(dex, token_in, token_out, amount)
                return ((dex, token_in, token_out), price)
            except Exception as e:
                logger.debug(f"Failed to get price for {token_in}/{token_out} on {dex}: {e}")
                return ((dex, token_in, token_out), 0)

        # Split into batches to avoid too many concurrent requests
        results = {}
        for i in range(0, len(token_pairs), self.max_parallel_requests):
            batch = token_pairs[i:i + self.max_parallel_requests]
            batch_results = await asyncio.gather(*[
                get_single_price(dex, token_in, token_out)
                for dex, token_in, token_out in batch
            ])
            results.update(dict(batch_results))

        return results

    async def find_arbitrage_paths(
        self,
        start_token_address: ChecksumAddress,
        amount_in: int,
        max_paths: Optional[int] = None,
        min_profit_threshold: Optional[float] = None
    ) -> List[ArbitragePath]:
        """
        Find arbitrage paths starting and ending with the specified token.

        Args:
            start_token_address: Address of the starting token
            amount_in: Amount of input token in wei
            max_paths: Maximum number of paths to return
            min_profit_threshold: Minimum profit threshold in token units

        Returns:
            List of arbitrage paths sorted by profitability
        """
        max_paths = max_paths or self.max_paths_to_check
        min_profit_threshold = min_profit_threshold or self.min_profit_threshold

        logger.info("Finding arbitrage paths for %s with amount %s",
                   start_token_address, amount_in)

        # Get list of supported tokens and DEXs
        tokens = await self.dex_manager.get_supported_tokens()
        dex_names = list(self.dex_manager.dexes.keys())

        # Find potential paths
        paths: List[ArbitragePath] = []
        path_id = 0

        # Generate all possible paths up to max_path_length
        for path_length in range(2, self.max_path_length + 1):
            # Generate token combinations
            token_paths = []
            current_tokens = [start_token_address]

            for _ in range(path_length - 1):
                next_tokens = []
                for current in current_tokens:
                    for token in tokens:
                        if token != current:
                            next_tokens.append(token)
                current_tokens = next_tokens
                token_paths.append(current_tokens)

            # For each token path, try all DEX combinations
            for token_path in token_paths:
                # Add start token to complete the cycle
                full_path = [start_token_address] + token_path + [start_token_address]

                # Generate DEX combinations
                dex_combinations = []
                for _ in range(path_length):
                    dex_combinations.append(dex_names)

                # Try each DEX combination
                for dex_path in self._generate_dex_combinations(dex_combinations):
                    # Build list of steps to check
                    steps_to_check = []
                    for i in range(len(full_path) - 1):
                        steps_to_check.append((
                            dex_path[i],
                            full_path[i],
                            full_path[i + 1]
                        ))

                    # Get all prices in parallel
                    prices = await self._get_prices_parallel(steps_to_check, amount_in)

                    # Build path if all prices are available
                    if all(prices.values()):
                        path_steps = []
                        current_amount = amount_in

                        for i, (dex, token_in, token_out) in enumerate(steps_to_check):
                            amount_out = prices[(dex, token_in, token_out)]
                            pool = await self.dex_manager.get_pool(dex, token_in, token_out)
                            fee = await self.dex_manager.get_fee(dex, pool)

                            step = PathStep(
                                dex=dex,
                                token_in=token_in,
                                token_out=token_out,
                                amount_in=current_amount,
                                amount_out=amount_out,
                                fee=fee,
                                pool_address=pool
                            )
                            path_steps.append(step)
                            current_amount = amount_out

                        # Calculate profit
                        profit = current_amount - amount_in
                        profit_margin = (current_amount / amount_in) - 1

                        # Estimate gas cost based on path length
                        gas_estimate = 150000 + (100000 * len(path_steps))

                        # If profitable, add to paths
                        if profit > 0 and profit_margin >= min_profit_threshold:
                            path_id += 1
                            path = ArbitragePath(
                                path_id=f"path_{path_id}",
                                input_token=start_token_address,
                                output_token=start_token_address,
                                amount_in=amount_in,
                                expected_output=current_amount,
                                profit=profit,
                                steps=path_steps,
                                profit_margin=profit_margin,
                                gas_estimate=gas_estimate
                            )
                            paths.append(path)

        # Update statistics
        self.total_paths_analyzed += 1
        if paths:
            self.profitable_paths_found += 1
            max_profit = max(path.profit for path in paths)
            self.max_profit_seen = max(self.max_profit_seen, max_profit)
            total_length = sum(path.path_length for path in paths)
            self._total_length_sum += total_length
            self.average_path_length = self._total_length_sum / self.total_paths_analyzed

        # Sort by net profit and return top paths
        paths.sort(key=lambda x: x.net_profit, reverse=True)
        return paths[:max_paths]

    def _generate_dex_combinations(self, dex_lists: List[List[str]]) -> List[List[str]]:
        """Generate all possible DEX combinations."""
        if not dex_lists:
            return [[]]

        result = []
        for dex in dex_lists[0]:
            for sub_combination in self._generate_dex_combinations(dex_lists[1:]):
                result.append([dex] + sub_combination)
        return result

    async def evaluate_path(self, path: ArbitragePath) -> Dict[str, Any]:
        """
        Evaluate an arbitrage path for profitability.

        Args:
            path: Arbitrage path

        Returns:
            Evaluation results
        """
        # Verify liquidity in all pools
        for step in path.steps:
            liquidity = await self.dex_manager.get_pool_liquidity(
                step.dex,
                step.pool_address
            )
            if liquidity < step.amount_in:
                return {
                    'viable': False,
                    'reason': f'Insufficient liquidity in {step.dex} pool',
                    'required': step.amount_in,
                    'available': liquidity
                }

        # Calculate price impact
        total_price_impact = 0
        for step in path.steps:
            impact = await self.dex_manager.calculate_price_impact(
                step.dex,
                step.pool_address,
                step.amount_in
            )
            total_price_impact += impact

        # Estimate execution probability
        execution_probability = max(0, 1 - (total_price_impact / len(path.steps)))

        return {
            'viable': True,
            'price_impact': total_price_impact,
            'execution_probability': execution_probability,
            'expected_net_profit': path.net_profit * execution_probability
        }

    async def simulate_execution(self, path: ArbitragePath) -> Dict[str, Any]:
        """
        Simulate execution of an arbitrage path.

        Args:
            path: Arbitrage path

        Returns:
            Simulation results
        """
        try:
            # Build transaction sequence
            transactions = []
            for step in path.steps:
                tx = await self.dex_manager.build_swap_transaction(
                    step.dex,
                    step.token_in,
                    step.token_out,
                    step.amount_in,
                    step.amount_out * 0.99  # 1% slippage tolerance
                )
                transactions.append(tx)

            # Simulate flash loan and swaps
            simulation = await self.web3_manager.simulate_transactions(transactions)

            return {
                'success': simulation['success'],
                'gas_used': simulation['gas_used'],
                'error': simulation.get('error', ''),
                'state_changes': simulation.get('state_changes', [])
            }

        except Exception as e:
            logger.error(f"Error simulating path execution: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current path finder statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            'total_paths_analyzed': self.total_paths_analyzed,
            'profitable_paths_found': self.profitable_paths_found,
            'max_profit_seen': self.max_profit_seen,
            'average_path_length': self.average_path_length
        }

async def create_path_finder(
    dex_manager=None,
    web3_manager=None,
    config=None
) -> PathFinder:
    """
    Create and initialize a PathFinder instance.

    Args:
        dex_manager: DexManager instance
        web3_manager: Web3Manager instance
        config: Configuration dictionary

    Returns:
        Initialized PathFinder instance
    """
    from .dex.dex_manager import DexManager

    if dex_manager is None:
        if web3_manager is None:
            from .web3.web3_manager import create_web3_manager
            web3_manager = await create_web3_manager(config)

        # Load config if not provided
        if config is None:
            from ..utils.config_loader import load_config
            config = load_config()

        # Create DexManager
        dex_manager = await DexManager.create(web3_manager, config)

    # Extract path finder specific config
    path_config = config.get('path_finder', {}) if config else {}

    # Create PathFinder instance
    path_finder = PathFinder(dex_manager, config, web3_manager)

    return path_finder
