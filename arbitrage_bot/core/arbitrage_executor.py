"""
Arbitrage Executor Module

This module ties together:
1. Path finding for optimal arbitrage routes
2. Flash loan execution through Balancer
3. MEV protection via Flashbots
4. Live profit validation and execution
"""

import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal
import asyncio
from eth_typing import ChecksumAddress

from .dex.dex_manager import DexManager
from .web3.web3_manager import create_web3_manager
from .path_finder import PathFinder, ArbitragePath
from ..integration.flashbots_integration import FlashbotsIntegration
from ..utils.async_manager import with_retry, AsyncLock

logger = logging.getLogger(__name__)

class ArbitrageExecutor:
    """Executes arbitrage opportunities with flash loans and MEV protection."""

    def __init__(
        self,
        path_finder: PathFinder,
        flashbots_integration: FlashbotsIntegration,
        min_profit_wei: int = 0
    ):
        """
        Initialize arbitrage executor.

        Args:
            path_finder: PathFinder instance
            flashbots_integration: FlashbotsIntegration instance
            min_profit_wei: Minimum profit threshold in wei
        """
        self.path_finder = path_finder
        self.flashbots_integration = flashbots_integration
        self.min_profit_wei = min_profit_wei

        # Initialize lock for thread safety
        self._execution_lock = AsyncLock()

        # Initialize statistics
        self.total_executions = 0
        self.successful_executions = 0
        self.total_profit_wei = 0
        self.max_profit_wei = 0

        logger.info(
            f"Arbitrage executor initialized with "
            f"min profit {flashbots_integration.web3_manager.w3.from_wei(min_profit_wei, 'ether')} ETH"
        )

    async def find_and_execute_arbitrage(
        self,
        token_address: ChecksumAddress,
        amount_wei: int,
        max_paths: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Find and execute the most profitable arbitrage opportunity.

        Args:
            token_address: Address of the token to start arbitrage with
            amount_wei: Amount of tokens in wei
            max_paths: Maximum number of paths to check

        Returns:
            Execution results
        """
        async with self._execution_lock:
            try:
                # Find arbitrage paths
                paths = await self.path_finder.find_arbitrage_paths(
                    start_token_address=token_address,
                    amount_in=amount_wei,
                    max_paths=max_paths
                )

                if not paths:
                    return {
                        'success': False,
                        'error': 'No profitable paths found'
                    }

                # Evaluate paths in parallel
                evaluations = await asyncio.gather(*[
                    self.path_finder.evaluate_path(path)
                    for path in paths
                ])

                # Filter viable paths and sort by expected profit
                viable_paths = []
                for path, eval_result in zip(paths, evaluations):
                    if eval_result['viable']:
                        viable_paths.append((path, eval_result['expected_net_profit']))

                if not viable_paths:
                    return {
                        'success': False,
                        'error': 'No viable paths after evaluation'
                    }

                # Sort by expected profit
                viable_paths.sort(key=lambda x: x[1], reverse=True)
                best_path = viable_paths[0][0]

                # Simulate best path
                simulation = await self.path_finder.simulate_execution(best_path)
                if not simulation['success']:
                    return {
                        'success': False,
                        'error': f"Path simulation failed: {simulation['error']}"
                    }

                # Build transactions for each step
                transactions = []
                for step in best_path.steps:
                    tx = await self.path_finder.dex_manager.build_swap_transaction(
                        step.dex,
                        step.token_in,
                        step.token_out,
                        step.amount_in,
                        int(step.amount_out * 0.99)  # 1% slippage protection
                    )
                    transactions.append(tx)

                # Execute through Flashbots
                result = await self.flashbots_integration.execute_arbitrage_bundle(
                    transactions=transactions,
                    token_addresses=[token_address],
                    flash_loan_amount=amount_wei
                )

                # Update statistics
                self.total_executions += 1
                if result['success']:
                    self.successful_executions += 1
                    self.total_profit_wei += result['net_profit']
                    self.max_profit_wei = max(self.max_profit_wei, result['net_profit'])

                return result

            except Exception as e:
                logger.error(f"Error executing arbitrage: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            'total_executions': self.total_executions,
            'successful_executions': self.successful_executions,
            'success_rate': self.successful_executions / self.total_executions if self.total_executions > 0 else 0,
            'total_profit_wei': self.total_profit_wei,
            'max_profit_wei': self.max_profit_wei,
            'path_finder_stats': self.path_finder.get_statistics()
        }

async def create_arbitrage_executor(
    path_finder: Optional[PathFinder] = None,
    flashbots_integration: Optional[FlashbotsIntegration] = None,
    config: Optional[Dict[str, Any]] = None
) -> ArbitrageExecutor:
    """
    Create and initialize an ArbitrageExecutor instance.

    Args:
        path_finder: Optional PathFinder instance
        flashbots_integration: Optional FlashbotsIntegration instance
        config: Optional configuration dictionary

    Returns:
        Initialized ArbitrageExecutor instance
    """
    # Load config if not provided
    if config is None:
        from ..utils.config_loader import load_production_config
        config = load_production_config()

    # Create PathFinder if not provided
    if path_finder is None:
        from .path_finder import create_path_finder
        web3_manager = await create_web3_manager(config)
        dex_manager = await DexManager.create(web3_manager, config)
        path_finder = await create_path_finder(dex_manager, config)

    # Create FlashbotsIntegration if not provided
    if flashbots_integration is None:
        from ..integration.flashbots_integration import setup_flashbots_rpc

        flashbots_result = await setup_flashbots_rpc(web3_manager, config)
        
        if not flashbots_result['success']:
            raise ValueError(f"Failed to set up Flashbots: {flashbots_result['error']}")
        
        flashbots_integration = flashbots_result['integration']

    # Create executor
    executor = ArbitrageExecutor(
        path_finder=path_finder,
        flashbots_integration=flashbots_integration,
        min_profit_wei=int(config.get('flashbots', {}).get('min_profit', '0'))
    )

    return executor