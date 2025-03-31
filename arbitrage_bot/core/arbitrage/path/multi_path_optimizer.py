"""
Multi-Path Arbitrage Optimizer

This module provides functionality for optimizing multi-path arbitrage opportunities
by efficiently allocating capital across multiple paths to maximize profit.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
import numpy as np
from eth_typing import ChecksumAddress

from ..models import ArbitrageOpportunity, ArbitragePath
from ...flashbots.bundle import BundleManager
from ...flashbots.simulation import SimulationManager

logger = logging.getLogger(__name__)

class MultiPathOptimizer:
    """
    Optimizes capital allocation across multiple arbitrage paths.
    
    This class implements algorithms for:
    - Optimal capital allocation across paths
    - Path prioritization based on profitability
    - Gas optimization for multi-path execution
    - Slippage minimization
    """
    
    def __init__(
        self,
        bundle_manager: Optional[BundleManager] = None,
        simulation_manager: Optional[SimulationManager] = None,
        max_paths: int = 5,
        min_allocation_percent: Decimal = Decimal('0.05'),
        slippage_tolerance: Decimal = Decimal('0.005')
    ):
        """
        Initialize the multi-path optimizer.
        
        Args:
            bundle_manager: Optional BundleManager for bundle creation
            simulation_manager: Optional SimulationManager for simulation
            max_paths: Maximum number of paths to include in a multi-path opportunity
            min_allocation_percent: Minimum allocation percentage for any path
            slippage_tolerance: Slippage tolerance for price impact calculation
        """
        self.bundle_manager = bundle_manager
        self.simulation_manager = simulation_manager
        self.max_paths = max_paths
        self.min_allocation_percent = min_allocation_percent
        self.slippage_tolerance = slippage_tolerance
        self._lock = asyncio.Lock()
        
        logger.info(
            f"Initialized MultiPathOptimizer with max_paths={max_paths}, "
            f"min_allocation={min_allocation_percent:.1%}, "
            f"slippage_tolerance={slippage_tolerance:.2%}"
        )
    
    async def optimize_paths(
        self,
        paths: List[ArbitragePath],
        total_capital: Decimal,
        token_address: ChecksumAddress
    ) -> Tuple[List[Decimal], Decimal]:
        """
        Optimize capital allocation across multiple paths.
        
        Args:
            paths: List of arbitrage paths to optimize
            total_capital: Total capital available for allocation
            token_address: Address of the token to allocate
            
        Returns:
            Tuple[List[Decimal], Decimal]: (allocations, expected_profit)
        """
        async with self._lock:
            try:
                # Limit number of paths
                if len(paths) > self.max_paths:
                    logger.info(f"Limiting from {len(paths)} to {self.max_paths} paths")
                    paths = self._select_best_paths(paths, self.max_paths)
                
                # Calculate optimal allocations
                allocations = await self._calculate_optimal_allocations(
                    paths, total_capital, token_address
                )
                
                # Calculate expected profit
                expected_profit = await self._calculate_expected_profit(
                    paths, allocations, token_address
                )
                
                logger.info(
                    f"Optimized {len(paths)} paths with {total_capital} capital. "
                    f"Expected profit: {expected_profit}"
                )
                
                return allocations, expected_profit
                
            except Exception as e:
                logger.error(f"Error optimizing paths: {e}")
                # Return equal allocation as fallback
                equal_allocation = total_capital / Decimal(len(paths))
                allocations = [equal_allocation] * len(paths)
                return allocations, Decimal('0')
    
    def _select_best_paths(
        self,
        paths: List[ArbitragePath],
        max_paths: int
    ) -> List[ArbitragePath]:
        """
        Select the best paths based on profitability and diversity.
        
        Args:
            paths: List of all available paths
            max_paths: Maximum number of paths to select
            
        Returns:
            List[ArbitragePath]: Selected paths
        """
        try:
            # Sort paths by expected profit
            sorted_paths = sorted(
                paths,
                key=lambda p: p.expected_profit,
                reverse=True
            )
            
            # Take top paths
            return sorted_paths[:max_paths]
            
        except Exception as e:
            logger.error(f"Error selecting best paths: {e}")
            return paths[:max_paths] if len(paths) > max_paths else paths
    
    async def _calculate_optimal_allocations(
        self,
        paths: List[ArbitragePath],
        total_capital: Decimal,
        token_address: ChecksumAddress
    ) -> List[Decimal]:
        """
        Calculate optimal capital allocation across paths.
        
        Args:
            paths: List of arbitrage paths
            total_capital: Total capital available
            token_address: Address of the token to allocate
            
        Returns:
            List[Decimal]: Optimal allocations for each path
        """
        try:
            # Get path profitability metrics
            profit_rates = []
            for path in paths:
                # Calculate profit rate (profit per unit of capital)
                profit_rate = path.expected_profit / path.required_amount
                profit_rates.append(float(profit_rate))
            
            # Convert to numpy array for optimization
            profit_rates = np.array(profit_rates)
            
            # Simple optimization: allocate proportionally to profit rates
            # In a real implementation, we would use a more sophisticated algorithm
            # that accounts for diminishing returns due to slippage
            weights = profit_rates / np.sum(profit_rates)
            
            # Apply minimum allocation constraint
            min_allocation = float(self.min_allocation_percent)
            for i in range(len(weights)):
                if weights[i] < min_allocation and weights[i] > 0:
                    weights[i] = min_allocation
            
            # Normalize weights to sum to 1
            weights = weights / np.sum(weights)
            
            # Calculate allocations
            allocations = [Decimal(str(w)) * total_capital for w in weights]
            
            return allocations
            
        except Exception as e:
            logger.error(f"Error calculating optimal allocations: {e}")
            # Return equal allocation as fallback
            equal_allocation = total_capital / Decimal(len(paths))
            return [equal_allocation] * len(paths)
    
    async def _calculate_expected_profit(
        self,
        paths: List[ArbitragePath],
        allocations: List[Decimal],
        token_address: ChecksumAddress
    ) -> Decimal:
        """
        Calculate expected profit from the optimized allocation.
        
        Args:
            paths: List of arbitrage paths
            allocations: Allocated capital for each path
            token_address: Address of the token allocated
            
        Returns:
            Decimal: Expected profit
        """
        try:
            total_profit = Decimal('0')
            
            for i, (path, allocation) in enumerate(zip(paths, allocations)):
                # Calculate profit for this path with the allocated capital
                # In a real implementation, we would account for slippage
                profit_rate = path.expected_profit / path.required_amount
                path_profit = profit_rate * allocation
                
                # Apply slippage based on allocation size
                slippage_factor = self._calculate_slippage_factor(
                    path, allocation, token_address
                )
                
                # Adjust profit for slippage
                adjusted_profit = path_profit * (Decimal('1') - slippage_factor)
                
                total_profit += adjusted_profit
            
            return total_profit
            
        except Exception as e:
            logger.error(f"Error calculating expected profit: {e}")
            return Decimal('0')
    
    def _calculate_slippage_factor(
        self,
        path: ArbitragePath,
        allocation: Decimal,
        token_address: ChecksumAddress
    ) -> Decimal:
        """
        Calculate slippage factor based on allocation size.
        
        Args:
            path: Arbitrage path
            allocation: Allocated capital
            token_address: Address of the token allocated
            
        Returns:
            Decimal: Slippage factor (0-1)
        """
        try:
            # This is a simplified model - in a real implementation,
            # we would use a more sophisticated model based on liquidity depth
            
            # Calculate allocation ratio relative to path's required amount
            allocation_ratio = allocation / path.required_amount
            
            # Apply a simple slippage model
            # Slippage increases quadratically with allocation ratio
            slippage = self.slippage_tolerance * (allocation_ratio ** Decimal('2'))
            
            # Cap slippage at 50%
            return min(slippage, Decimal('0.5'))
            
        except Exception as e:
            logger.error(f"Error calculating slippage factor: {e}")
            return self.slippage_tolerance
    
    async def create_multi_path_opportunity(
        self,
        paths: List[ArbitragePath],
        token_address: ChecksumAddress,
        total_capital: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Create a multi-path arbitrage opportunity from paths.
        
        Args:
            paths: List of arbitrage paths
            token_address: Address of the token to allocate
            total_capital: Total capital to allocate (optional)
            
        Returns:
            Dict[str, Any]: Multi-path opportunity
        """
        async with self._lock:
            try:
                if not paths:
                    return {
                        'success': False,
                        'error': 'No paths provided'
                    }
                
                # Determine total capital if not provided
                if total_capital is None:
                    # Use the sum of required amounts as default
                    total_capital = sum(path.required_amount for path in paths)
                
                # Optimize paths
                allocations, expected_profit = await self.optimize_paths(
                    paths, total_capital, token_address
                )
                
                # Create opportunity
                opportunity = {
                    'success': True,
                    'paths': paths,
                    'allocations': allocations,
                    'token_address': token_address,
                    'total_capital': total_capital,
                    'expected_profit': expected_profit
                }
                
                return opportunity
                
            except Exception as e:
                logger.error(f"Error creating multi-path opportunity: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    async def simulate_multi_path_opportunity(
        self,
        opportunity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate a multi-path opportunity to validate profitability.
        
        Args:
            opportunity: Multi-path opportunity
            
        Returns:
            Dict[str, Any]: Simulation results
        """
        async with self._lock:
            try:
                if not self.simulation_manager:
                    return {
                        'success': False,
                        'error': 'Simulation manager not available'
                    }
                
                # Extract paths and allocations
                paths = opportunity.get('paths', [])
                allocations = opportunity.get('allocations', [])
                
                if not paths or not allocations or len(paths) != len(allocations):
                    return {
                        'success': False,
                        'error': 'Invalid opportunity format'
                    }
                
                # Create transactions for each path with its allocation
                transactions = []
                for path, allocation in zip(paths, allocations):
                    path_txs = await self._create_path_transactions(path, allocation)
                    transactions.extend(path_txs)
                
                # Create bundle
                if self.bundle_manager:
                    bundle = await self.bundle_manager.create_bundle(transactions)
                    
                    # Simulate bundle
                    success, simulation_results = await self.simulation_manager.simulate_bundle(bundle)
                    
                    if success:
                        return {
                            'success': True,
                            'bundle': bundle,
                            'simulation_results': simulation_results
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'Bundle simulation failed',
                            'simulation_results': simulation_results
                        }
                else:
                    return {
                        'success': False,
                        'error': 'Bundle manager not available'
                    }
                
            except Exception as e:
                logger.error(f"Error simulating multi-path opportunity: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    async def _create_path_transactions(
        self,
        path: ArbitragePath,
        allocation: Decimal
    ) -> List[Dict[str, Any]]:
        """
        Create transactions for a path with the specified allocation.
        
        Args:
            path: Arbitrage path
            allocation: Allocated capital
            
        Returns:
            List[Dict[str, Any]]: List of transactions
        """
        # This is a placeholder - in a real implementation,
        # we would create actual transactions based on the path
        return []