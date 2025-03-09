"""
Path Finder Module

This module provides functionality for:
- Finding arbitrage paths
- Analyzing path profitability
- Optimizing path execution
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from eth_typing import ChecksumAddress

from ...utils.async_manager import with_retry
from ..web3.interfaces import Web3Client
from .dex_manager import DexManager

logger = logging.getLogger(__name__)

class PathFinder:
    """Finds and analyzes arbitrage paths."""

    def __init__(
        self,
        web3_manager: Web3Client,
        dex_manager: DexManager,
        max_paths: int = 3,
        max_hops: int = 3
    ):
        """
        Initialize path finder.

        Args:
            web3_manager: Web3 client instance
            dex_manager: DEX manager instance
            max_paths: Maximum number of paths to return
            max_hops: Maximum number of hops per path
        """
        self.web3_manager = web3_manager
        self.dex_manager = dex_manager
        self.max_paths = max_paths
        self.max_hops = max_hops

        logger.info(
            f"Path finder initialized with max paths: {max_paths}, "
            f"max hops: {max_hops}"
        )

    @with_retry(retries=3, delay=1.0)
    async def find_paths(
        self,
        start_token: ChecksumAddress,
        max_hops: Optional[int] = None,
        token_addresses: Optional[List[ChecksumAddress]] = None
    ) -> List[List[Tuple[str, ChecksumAddress]]]:
        """
        Find arbitrage paths.

        Args:
            start_token: Starting token address
            max_hops: Optional maximum number of hops (overrides instance value)
            token_addresses: Optional list of token addresses to include

        Returns:
            List of paths, where each path is a list of (dex_name, pool_address) tuples
        """
        paths = []
        visited = set()
        max_hops_to_use = max_hops if max_hops is not None else self.max_hops

        async def dfs(
            current_token: ChecksumAddress,
            current_path: List[Tuple[str, ChecksumAddress]],
            depth: int
        ):
            """Depth-first search for paths."""
            if depth >= max_hops_to_use:
                # Check if path returns to start token
                if current_token == start_token:
                    paths.append(current_path[:])
                return

            # Get pools for current token
            for dex_name, dex in self.dex_manager.dexes.items():
                # Discover pools if needed
                if not dex.pools:
                    await self.dex_manager.discover_pools(
                        dex_name=dex_name,
                        token_addresses=token_addresses
                    )

                for pool in dex.pools:
                    if pool not in visited:
                        visited.add(pool)

                        try:
                            # Get pool contract
                            pool_abi = await self.web3_manager.eth.contract(
                                address=pool
                            ).functions.abi()

                            # Get tokens
                            token0 = await pool_abi.token0().call()
                            token1 = await pool_abi.token1().call()

                            # Find next token
                            next_token = token1 if token0 == current_token else token0

                            # Continue path
                            current_path.append((dex_name, pool))
                            await dfs(next_token, current_path, depth + 1)
                            current_path.pop()

                        except Exception as e:
                            logger.debug(f"Failed to process pool {pool}: {e}")

                        visited.remove(pool)

        # Start search from start token
        await dfs(start_token, [], 0)

        # Sort paths by length (shorter is better)
        paths.sort(key=len)

        # Return top paths
        return paths[:self.max_paths]

    @with_retry(retries=3, delay=1.0)
    async def analyze_path(
        self,
        path: List[Tuple[str, ChecksumAddress]],
        amount_in: int
    ) -> Dict[str, Any]:
        """
        Analyze path profitability.

        Args:
            path: Path to analyze
            amount_in: Input amount in wei

        Returns:
            Analysis results
        """
        try:
            amount_out = amount_in
            gas_cost = 0

            # Simulate swaps
            for dex_name, pool in path:
                try:
                    # Get pool contract
                    pool_abi = await self.web3_manager.eth.contract(
                        address=pool
                    ).functions.abi()

                    # Estimate gas
                    gas = await pool_abi.swap.estimateGas(
                        amount_out,
                        self.web3_manager.wallet_address
                    )
                    gas_cost += gas

                    # Get output amount
                    amount_out = await pool_abi.getAmountOut(
                        amount_out
                    ).call()

                except Exception as e:
                    logger.debug(f"Failed to simulate swap for pool {pool}: {e}")
                    return {
                        'profitable': False,
                        'error': str(e)
                    }

            # Calculate profit
            profit = amount_out - amount_in
            gas_price = await self.web3_manager.eth.gas_price
            total_gas_cost = gas_cost * gas_price
            net_profit = profit - total_gas_cost

            return {
                'profitable': net_profit > 0,
                'profit': net_profit,
                'gas_cost': gas_cost,
                'gas_price': gas_price,
                'amount_in': amount_in,
                'amount_out': amount_out
            }

        except Exception as e:
            logger.error(f"Failed to analyze path: {e}")
            return {
                'profitable': False,
                'error': str(e)
            }

    async def close(self):
        """Clean up resources."""
        pass

async def create_path_finder(
    web3_manager: Web3Client,
    dex_manager: DexManager,
    config: Dict[str, Any]
) -> PathFinder:
    """
    Create a new path finder.

    Args:
        web3_manager: Web3 client instance
        dex_manager: DEX manager instance
        config: Configuration dictionary

    Returns:
        PathFinder instance
    """
    return PathFinder(
        web3_manager=web3_manager,
        dex_manager=dex_manager,
        max_paths=config.get('max_paths', 3),
        max_hops=config.get('max_hops', 3)
    )
