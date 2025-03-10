"""
Path Finder Module

This module provides functionality for:
- Finding arbitrage paths
- Analyzing path profitability
- Optimizing path execution
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from eth_typing import ChecksumAddress
from web3 import Web3

from ...utils.async_manager import with_retry, AsyncLock
from .dex_manager import DexManager

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

    def __init__(
        self,
        path_id: str,
        input_token: ChecksumAddress,
        output_token: ChecksumAddress,
        amount_in: int,
        expected_output: int,
        profit: int,
        steps: List[PathStep],
        profit_margin: float,
        gas_estimate: int
    ):
        """Initialize arbitrage path."""
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
        self.net_profit = profit - (gas_estimate * Web3.to_wei(50, 'gwei'))  # Assume 50 gwei

class PathFinder:
    """Finds and analyzes arbitrage paths."""

    def __init__(
        self,
        dex_manager: DexManager,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize path finder."""
        self.dex_manager = dex_manager
        self.config = config or {}

        # Extract configuration
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

        logger.info(
            f"Path finder initialized with max paths: {self.max_paths_to_check}, "
            f"max length: {self.max_path_length}"
        )

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

        # Split into batches
        results = {}
        for i in range(0, len(token_pairs), self.max_parallel_requests):
            batch = token_pairs[i:i + self.max_parallel_requests]
            batch_results = await asyncio.gather(*[
                get_single_price(dex, token_in, token_out)
                for dex, token_in, token_out in batch
            ])
            results.update(dict(batch_results))

        return results

    @with_retry(retries=3, delay=1.0)
    async def find_arbitrage_paths(
        self,
        start_token_address: ChecksumAddress,
        amount_in: int,
        max_paths: Optional[int] = None,
        min_profit_threshold: Optional[float] = None
    ) -> List[ArbitragePath]:
        """Find arbitrage paths starting and ending with the specified token."""
        max_paths = max_paths or self.max_paths_to_check
        min_profit_threshold = min_profit_threshold or self.min_profit_threshold

        logger.info(f"Finding arbitrage paths for {start_token_address}")

        # Get supported tokens and DEXs
        tokens = await self.dex_manager.get_supported_tokens()
        dex_names = list(self.dex_manager.dexes.keys())

        paths: List[ArbitragePath] = []
        path_id = 0

        # Generate paths up to max_path_length
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
                # Add start token to complete cycle
                full_path = [start_token_address] + token_path + [start_token_address]

                # Generate DEX combinations
                dex_combinations = []
                for _ in range(path_length):
                    dex_combinations.append(dex_names)

                # Try each DEX combination
                for dex_path in self._generate_dex_combinations(dex_combinations):
                    # Build steps to check
                    steps_to_check = []
                    for i in range(len(full_path) - 1):
                        steps_to_check.append((
                            dex_path[i],
                            full_path[i],
                            full_path[i + 1]
                        ))

                    # Get all prices in parallel
                    prices = await self._get_prices_parallel(steps_to_check, amount_in)

                    # Build path if all prices available
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

                        # Estimate gas cost
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

    @with_retry(retries=3, delay=1.0)
    async def evaluate_path(
        self,
        path: ArbitragePath
    ) -> Dict[str, Any]:
        """Evaluate an arbitrage path for profitability."""
        try:
            # Verify liquidity
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

        except Exception as e:
            logger.error(f"Failed to evaluate path: {e}")
            return {
                'viable': False,
                'error': str(e)
            }

    def _generate_dex_combinations(self, dex_lists: List[List[str]]) -> List[List[str]]:
        """Generate all possible DEX combinations."""
        if not dex_lists:
            return [[]]

        result = []
        for dex in dex_lists[0]:
            for sub_combination in self._generate_dex_combinations(dex_lists[1:]):
                result.append([dex] + sub_combination)
        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get current path finder statistics."""
        return {
            'total_paths_analyzed': self.total_paths_analyzed,
            'profitable_paths_found': self.profitable_paths_found,
            'max_profit_seen': self.max_profit_seen,
            'average_path_length': self.average_path_length
        }

    async def close(self):
        """Clean up resources."""
        pass

async def create_path_finder(
    dex_manager: DexManager,
    config: Optional[Dict[str, Any]] = None
) -> PathFinder:
    """Create a new path finder."""
    return PathFinder(
        dex_manager=dex_manager,
        config=config
    )
