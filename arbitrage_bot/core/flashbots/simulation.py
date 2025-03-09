"""
Flashbots simulation manager module.

This module provides functionality for simulating transaction bundles
and validating expected profits before submission.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from web3 import Web3
from web3.types import TxParams
from eth_typing import ChecksumAddress

from .manager import FlashbotsManager
from .bundle import BundleManager

logger = logging.getLogger(__name__)

class SimulationManager:
    """
    Manages Flashbots bundle simulation and profit validation.
    
    This class handles:
    - Bundle simulation
    - State validation
    - Profit calculation
    - Gas optimization
    """
    
    def __init__(
        self,
        flashbots_manager: FlashbotsManager,
        bundle_manager: BundleManager,
        max_simulations: int = 3,
        simulation_timeout: float = 5.0
    ) -> None:
        """
        Initialize the simulation manager.

        Args:
            flashbots_manager: FlashbotsManager instance
            bundle_manager: BundleManager instance
            max_simulations: Maximum number of simulation attempts
            simulation_timeout: Simulation timeout in seconds
        """
        self.flashbots = flashbots_manager
        self.bundle_manager = bundle_manager
        self.max_simulations = max_simulations
        self.simulation_timeout = simulation_timeout
        self._lock = asyncio.Lock()
        
        logger.info(
            f"Initialized SimulationManager with max_simulations={max_simulations}, "
            f"timeout={simulation_timeout}s"
        )
    
    async def simulate_bundle(
        self,
        bundle: Dict[str, Any],
        state_block: Optional[str] = 'latest'
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Simulate a transaction bundle and validate results.

        Args:
            bundle: Bundle parameters
            state_block: Block number for state access

        Returns:
            Tuple[bool, Dict[str, Any]]: (success, simulation results)

        Raises:
            Exception: If simulation fails
        """
        try:
            async with self._lock:
                # Prepare simulation parameters
                params = [{
                    'transactions': [
                        tx.rawTransaction.hex() for tx in bundle['transactions']
                    ],
                    'block_number': bundle['target_block'],
                    'state_block_number': state_block,
                    'simulation_kind': 'full'  # Request full simulation
                }]
                
                # Run simulation
                for attempt in range(self.max_simulations):
                    try:
                        async with asyncio.timeout(self.simulation_timeout):
                            response = await self.flashbots._make_request(
                                'eth_callBundle',
                                params
                            )
                            
                            result = response['result']
                            
                            if result['success']:
                                # Parse and validate results
                                simulation_results = await self._parse_simulation_results(
                                    result,
                                    bundle
                                )
                                
                                if simulation_results['profitable']:
                                    logger.info(
                                        f"Bundle simulation successful with profit "
                                        f"{simulation_results['profit']} ETH"
                                    )
                                    return True, simulation_results
                                else:
                                    logger.warning(
                                        f"Bundle simulation showed insufficient profit: "
                                        f"{simulation_results['profit']} ETH"
                                    )
                            else:
                                logger.warning(
                                    f"Bundle simulation failed: {result.get('error')}"
                                )
                            
                    except asyncio.TimeoutError:
                        logger.warning(
                            f"Simulation timeout on attempt {attempt + 1}"
                        )
                        continue
                        
                    except Exception as e:
                        logger.error(
                            f"Simulation error on attempt {attempt + 1}: {e}"
                        )
                        continue
                
                return False, {'error': 'All simulation attempts failed'}
                
        except Exception as e:
            logger.error(f"Failed to simulate bundle: {e}")
            raise
    
    async def _parse_simulation_results(
        self,
        result: Dict[str, Any],
        bundle: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse and validate simulation results.

        Args:
            result: Simulation result from Flashbots
            bundle: Original bundle parameters

        Returns:
            Dict[str, Any]: Parsed simulation results
        """
        try:
            # Extract key metrics
            gas_used = sum(tx['gasUsed'] for tx in result['results'])
            gas_price = bundle['gas_price']
            total_cost = Decimal(str(gas_used)) * Decimal(str(gas_price)) / Decimal('1e9')
            
            # Calculate state changes
            state_changes = await self._analyze_state_changes(result['stateDiff'])
            
            # Calculate actual profit
            profit = await self._calculate_actual_profit(
                state_changes,
                total_cost
            )
            
            # Validate profitability
            profitable = profit >= self.bundle_manager.min_profit
            
            return {
                'gas_used': gas_used,
                'total_cost': total_cost,
                'state_changes': state_changes,
                'profit': profit,
                'profitable': profitable,
                'coinbase_diff': result.get('coinbaseDiff'),
                'logs': result.get('logs', [])
            }
            
        except Exception as e:
            logger.error(f"Failed to parse simulation results: {e}")
            raise
    
    async def _analyze_state_changes(
        self,
        state_diff: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze state changes from simulation.

        Args:
            state_diff: State differences from simulation

        Returns:
            Dict[str, Any]: Analyzed state changes
        """
        try:
            changes = {
                'balance_changes': {},
                'storage_changes': {},
                'code_changes': []
            }
            
            for address, diff in state_diff.items():
                # Skip if not checksummed
                if not Web3.is_checksum_address(address):
                    continue
                
                # Analyze balance changes
                if 'balance' in diff:
                    old_balance = int(diff['balance'].get('from', '0'), 16)
                    new_balance = int(diff['balance'].get('to', '0'), 16)
                    changes['balance_changes'][address] = {
                        'old': old_balance,
                        'new': new_balance,
                        'diff': new_balance - old_balance
                    }
                
                # Analyze storage changes
                if 'storage' in diff:
                    changes['storage_changes'][address] = diff['storage']
                
                # Track code changes
                if 'code' in diff:
                    changes['code_changes'].append(address)
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to analyze state changes: {e}")
            raise
    
    async def _calculate_actual_profit(
        self,
        state_changes: Dict[str, Any],
        total_cost: Decimal
    ) -> Decimal:
        """
        Calculate actual profit from state changes.

        Args:
            state_changes: Analyzed state changes
            total_cost: Total transaction cost

        Returns:
            Decimal: Actual profit in ETH
        """
        try:
            profit = Decimal('0')
            
            # Calculate profit from balance changes
            for address, change in state_changes['balance_changes'].items():
                if address == self.flashbots.account.address:
                    # Convert to ETH
                    balance_diff = Decimal(str(change['diff'])) / Decimal('1e18')
                    profit += balance_diff
            
            # Subtract costs
            net_profit = profit - total_cost
            
            return net_profit
            
        except Exception as e:
            logger.error(f"Failed to calculate actual profit: {e}")
            raise