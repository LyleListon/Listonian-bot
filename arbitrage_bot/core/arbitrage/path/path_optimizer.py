"""
Path Optimizer Implementation

This module provides a concrete implementation of the PathOptimizer interface
for optimizing capital allocation across multiple paths.
"""

import asyncio
import logging
import random
import time
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple, Union

import numpy as np
from web3 import Web3

from ...dex.interfaces import DexManager
from ...price.interfaces import PriceFetcher
from ...utils.decimal import format_decimal
from .interfaces import PathOptimizer, ArbitragePath, MultiPathOpportunity

logger = logging.getLogger(__name__)


class MonteCarloPathOptimizer(PathOptimizer):
    """
    Path optimizer that uses Monte Carlo simulation to find optimal
    capital allocation across multiple arbitrage paths.
    
    This optimizer generates random allocations and evaluates them, then
    refines the best allocation using gradient ascent to maximize profit.
    """
    
    def __init__(
        self,
        dex_manager: DexManager,
        price_fetcher: Optional[PriceFetcher] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Monte Carlo path optimizer.
        
        Args:
            dex_manager: Manager for DEX interactions
            price_fetcher: Optional price fetcher for price data
            config: Configuration parameters
        """
        self.dex_manager = dex_manager
        self.price_fetcher = price_fetcher
        self.config = config or {}
        
        # Extract configuration parameters
        self.num_simulations = self.config.get("num_simulations", 1000)
        self.gradient_steps = self.config.get("gradient_steps", 20)
        self.learning_rate = Decimal(self.config.get("learning_rate", "0.001"))
        self.min_allocation = Decimal(self.config.get("min_allocation", "0.001"))
        self.slippage_tolerance = Decimal(self.config.get("slippage_tolerance", "0.005"))
        
        # Seed the random number generator for reproducibility
        random.seed(42)
        np.random.seed(42)
        
        # State
        self._initialized = False
        self._initialization_lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """
        Initialize the path optimizer.
        
        Returns:
            True if initialization succeeds, False otherwise
        """
        async with self._initialization_lock:
            if self._initialized:
                return True
            
            try:
                logger.info("Initializing Monte Carlo path optimizer")
                
                self._initialized = True
                logger.info("Monte Carlo path optimizer initialized successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize Monte Carlo path optimizer: {e}")
                return False
    
    async def optimize_allocation(
        self,
        paths: List[ArbitragePath],
        total_capital: Decimal,
        optimization_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Decimal], Decimal]:
        """
        Optimize capital allocation across multiple paths.
        
        Args:
            paths: List of arbitrage paths to allocate capital across
            total_capital: Total capital available for allocation
            optimization_params: Additional parameters for optimization
            
        Returns:
            Tuple of (allocations, expected_profit), where allocations is a
            list of allocated amounts for each path, and expected_profit is
            the expected total profit
        """
        await self._ensure_initialized()
        
        optimization_params = optimization_params or {}
        
        # If no paths, return empty allocation and zero profit
        if not paths:
            return [], Decimal("0")
        
        # If only one path, allocate all capital to it
        if len(paths) == 1:
            path = paths[0]
            optimal_amount = path.optimal_amount or Decimal("0")
            
            # Cap at total capital
            allocation = min(optimal_amount, total_capital)
            
            # Calculate expected profit
            profit = self._calculate_profit_from_allocation([allocation], paths)
            
            return [allocation], profit
        
        # Extract parameters
        num_simulations = optimization_params.get("num_simulations", self.num_simulations)
        gradient_steps = optimization_params.get("gradient_steps", self.gradient_steps)
        learning_rate = Decimal(str(optimization_params.get("learning_rate", self.learning_rate)))
        
        logger.info(
            f"Optimizing allocation for {len(paths)} paths with "
            f"{num_simulations} simulations and {gradient_steps} gradient steps"
        )
        
        try:
            # Run Monte Carlo simulation
            best_allocation, best_profit = await self._monte_carlo_optimize(
                paths=paths,
                total_capital=total_capital,
                num_simulations=num_simulations
            )
            
            logger.info(
                f"Monte Carlo optimization result: "
                f"profit={format_decimal(best_profit)}, "
                f"allocation={[format_decimal(a) for a in best_allocation]}"
            )
            
            # Refine with gradient descent if profit is positive
            if best_profit > 0:
                refined_allocation, refined_profit = await self._gradient_descent_optimize(
                    paths=paths,
                    total_capital=total_capital,
                    initial_allocation=best_allocation,
                    steps=gradient_steps,
                    learning_rate=learning_rate
                )
                
                logger.info(
                    f"Gradient descent optimization result: "
                    f"profit={format_decimal(refined_profit)}, "
                    f"allocation={[format_decimal(a) for a in refined_allocation]}"
                )
                
                # Use refined allocation if it's better
                if refined_profit > best_profit:
                    best_allocation = refined_allocation
                    best_profit = refined_profit
            
            return best_allocation, best_profit
            
        except Exception as e:
            logger.error(f"Error optimizing allocation: {e}")
            
            # Return default allocation (equal division)
            even_allocation = [total_capital / Decimal(len(paths)) for _ in paths]
            profit = self._calculate_profit_from_allocation(even_allocation, paths)
            
            return even_allocation, profit
    
    async def create_opportunity(
        self,
        paths: List[ArbitragePath],
        allocations: List[Decimal],
        expected_profit: Decimal,
        start_token: str
    ) -> MultiPathOpportunity:
        """
        Create a multi-path opportunity from the optimized allocation.
        
        Args:
            paths: List of arbitrage paths
            allocations: Optimized capital allocations for each path
            expected_profit: Expected total profit
            start_token: Starting token address (checksummed)
            
        Returns:
            Multi-path arbitrage opportunity
        """
        await self._ensure_initialized()
        
        try:
            # Ensure token is checksummed
            start_token = Web3.to_checksum_address(start_token)
            
            # Calculate required amount
            required_amount = sum(allocations)
            
            # Create execution data
            execution_data = {
                "allocations": [float(a) for a in allocations],
                "paths": [
                    {
                        "tokens": path.tokens,
                        "pools": [pool.address for pool in path.pools],
                        "dexes": path.dexes,
                        "swap_data": path.swap_data
                    }
                    for path in paths
                ],
                "slippage_tolerance": float(self.slippage_tolerance)
            }
            
            # Create opportunity
            opportunity = MultiPathOpportunity(
                paths=paths,
                start_token=start_token,
                required_amount=required_amount,
                expected_profit=expected_profit,
                allocations=allocations,
                confidence_level=self._calculate_confidence_level(paths),
                execution_data=execution_data,
                created_at=int(time.time())
            )
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error creating opportunity: {e}")
            
            # Create a default opportunity
            return MultiPathOpportunity(
                paths=paths,
                start_token=start_token,
                required_amount=Decimal("0"),
                expected_profit=Decimal("0"),
                allocations=[Decimal("0") for _ in paths],
                confidence_level=0.0,
                execution_data={},
                created_at=int(time.time())
            )
    
    async def close(self) -> None:
        """Close the path optimizer and clean up resources."""
        logger.info("Closing Monte Carlo path optimizer")
        self._initialized = False
    
    async def _monte_carlo_optimize(
        self,
        paths: List[ArbitragePath],
        total_capital: Decimal,
        num_simulations: int = 1000
    ) -> Tuple[List[Decimal], Decimal]:
        """
        Optimize allocation using Monte Carlo simulation.
        
        This method generates random allocations and evaluates them to find
        the one that maximizes profit.
        
        Args:
            paths: List of arbitrage paths
            total_capital: Total capital available
            num_simulations: Number of simulations to run
            
        Returns:
            Tuple of (best_allocation, best_profit)
        """
        best_allocation = []
        best_profit = Decimal("0")
        
        # Initialize with path optimal amounts or proportional yields
        initial_allocation = self._get_initial_allocation(paths, total_capital)
        current_profit = self._calculate_profit_from_allocation(initial_allocation, paths)
        
        if current_profit > best_profit:
            best_allocation = initial_allocation
            best_profit = current_profit
        
        # Run Monte Carlo simulation
        for _ in range(num_simulations):
            # Generate random allocation
            allocation = self._generate_random_allocation(paths, total_capital)
            
            # Calculate profit
            profit = self._calculate_profit_from_allocation(allocation, paths)
            
            # Update best allocation if better
            if profit > best_profit:
                best_allocation = allocation
                best_profit = profit
        
        return best_allocation, best_profit
    
    async def _gradient_descent_optimize(
        self,
        paths: List[ArbitragePath],
        total_capital: Decimal,
        initial_allocation: List[Decimal],
        steps: int = 20,
        learning_rate: Decimal = Decimal("0.001")
    ) -> Tuple[List[Decimal], Decimal]:
        """
        Optimize allocation using gradient descent.
        
        This method refines an initial allocation using gradient descent to
        maximize profit.
        
        Args:
            paths: List of arbitrage paths
            total_capital: Total capital available
            initial_allocation: Initial allocation to refine
            steps: Number of gradient descent steps
            learning_rate: Learning rate for gradient descent
            
        Returns:
            Tuple of (best_allocation, best_profit)
        """
        current_allocation = initial_allocation.copy()
        current_profit = self._calculate_profit_from_allocation(current_allocation, paths)
        
        best_allocation = current_allocation.copy()
        best_profit = current_profit
        
        # Run gradient descent
        for _ in range(steps):
            # Calculate gradient
            gradient = []
            
            for i in range(len(paths)):
                # Increase allocation slightly
                delta_allocation = [Decimal("0") for _ in paths]
                delta = min(current_allocation[i] * Decimal("0.01"), Decimal("0.1"))
                delta_allocation[i] = delta
                
                # Normalize to maintain total capital
                normalized_allocation = self._normalize_allocation(
                    [a + da for a, da in zip(current_allocation, delta_allocation)],
                    total_capital
                )
                
                # Calculate profit change
                profit_delta = (
                    self._calculate_profit_from_allocation(normalized_allocation, paths) -
                    current_profit
                )
                
                # Calculate gradient component
                gradient_component = profit_delta / delta if delta > 0 else Decimal("0")
                gradient.append(gradient_component)
            
            # Update allocation based on gradient
            update = [lr * g for lr, g in zip([learning_rate] * len(paths), gradient)]
            new_allocation = [a + u for a, u in zip(current_allocation, update)]
            
            # Normalize to maintain total capital
            new_allocation = self._normalize_allocation(new_allocation, total_capital)
            
            # Calculate new profit
            new_profit = self._calculate_profit_from_allocation(new_allocation, paths)
            
            # Update current allocation and profit
            current_allocation = new_allocation
            current_profit = new_profit
            
            # Update best allocation if better
            if current_profit > best_profit:
                best_allocation = current_allocation.copy()
                best_profit = current_profit
        
        return best_allocation, best_profit
    
    def _generate_random_allocation(
        self,
        paths: List[ArbitragePath],
        total_capital: Decimal
    ) -> List[Decimal]:
        """
        Generate a random allocation of capital across paths.
        
        Args:
            paths: List of arbitrage paths
            total_capital: Total capital available
            
        Returns:
            List of allocated amounts
        """
        # Generate random weights
        weights = [random.random() for _ in paths]
        total_weight = sum(weights)
        
        # Normalize weights
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in weights]
        else:
            normalized_weights = [1.0 / len(paths) for _ in paths]
        
        # Apply minimum allocation
        min_allocation_value = self.min_allocation
        
        # Ensure minimum allocation doesn't exceed total capital
        if min_allocation_value * len(paths) > total_capital:
            min_allocation_value = total_capital / Decimal(len(paths))
        
        # Calculate allocations
        allocations = [
            max(Decimal(str(w)) * total_capital, min_allocation_value)
            for w in normalized_weights
        ]
        
        # Normalize to maintain total capital
        return self._normalize_allocation(allocations, total_capital)
    
    def _get_initial_allocation(
        self,
        paths: List[ArbitragePath],
        total_capital: Decimal
    ) -> List[Decimal]:
        """
        Get an initial allocation based on path optimal amounts or yields.
        
        Args:
            paths: List of arbitrage paths
            total_capital: Total capital available
            
        Returns:
            Initial allocation
        """
        # Try using optimal amounts
        optimal_amounts = [
            path.optimal_amount if path.optimal_amount is not None else Decimal("0")
            for path in paths
        ]
        
        # If optimal amounts are available, use them
        if sum(optimal_amounts) > 0:
            allocations = optimal_amounts
            
            # Normalize to maintain total capital
            return self._normalize_allocation(allocations, total_capital)
        
        # Otherwise, allocate based on path yields
        yields = [
            Decimal(str(path.path_yield)) if path.path_yield > 0 else Decimal("0.001")
            for path in paths
        ]
        
        total_yield = sum(yields)
        
        if total_yield > 0:
            allocations = [
                (y / total_yield) * total_capital
                for y in yields
            ]
        else:
            # Even allocation if no yield information
            allocations = [total_capital / Decimal(len(paths)) for _ in paths]
        
        # Normalize to maintain total capital
        return self._normalize_allocation(allocations, total_capital)
    
    def _normalize_allocation(
        self,
        allocations: List[Decimal],
        total_capital: Decimal
    ) -> List[Decimal]:
        """
        Normalize an allocation to maintain the total capital constraint.
        
        Args:
            allocations: List of allocated amounts
            total_capital: Total capital available
            
        Returns:
            Normalized allocation
        """
        # Handle empty allocations
        if not allocations:
            return []
        
        # Calculate current total
        current_total = sum(allocations)
        
        # If current total is zero, use equal allocation
        if current_total <= 0:
            return [total_capital / Decimal(len(allocations)) for _ in allocations]
        
        # Normalize
        scaling_factor = total_capital / current_total
        normalized = [a * scaling_factor for a in allocations]
        
        # Ensure minimum allocation
        min_allocation_value = self.min_allocation
        
        # Adjust minimum allocation if necessary
        if min_allocation_value * len(allocations) > total_capital:
            min_allocation_value = total_capital / Decimal(len(allocations))
        
        # Apply minimum allocation
        result = [max(a, min_allocation_value) for a in normalized]
        
        # Handle case where applying minimum exceeds total
        new_total = sum(result)
        if new_total > total_capital:
            # Reduce proportionally to match total
            scaling_factor = total_capital / new_total
            result = [a * scaling_factor for a in result]
        
        return result
    
    def _calculate_profit_from_allocation(
        self,
        allocations: List[Decimal],
        paths: List[ArbitragePath]
    ) -> Decimal:
        """
        Calculate the expected profit from a given allocation.
        
        Args:
            allocations: List of allocated amounts
            paths: List of arbitrage paths
            
        Returns:
            Expected profit
        """
        total_profit = Decimal("0")
        
        for i, (allocation, path) in enumerate(zip(allocations, paths)):
            # Skip paths with no yield information
            if path.path_yield <= 0:
                continue
            
            # Calculate profit based on allocation and path yield
            path_yield = Decimal(str(path.path_yield))
            path_profit = allocation * path_yield
            
            # Adjust profit for slippage based on allocation vs. optimal amount
            if path.optimal_amount and path.optimal_amount > 0:
                if allocation > path.optimal_amount:
                    # Apply penalty for exceeding optimal amount
                    excess_ratio = allocation / path.optimal_amount
                    slippage_factor = Decimal("1") - self.slippage_tolerance * (excess_ratio - Decimal("1"))
                    slippage_factor = max(slippage_factor, Decimal("0"))
                    path_profit *= slippage_factor
            
            total_profit += path_profit
        
        return total_profit
    
    def _calculate_confidence_level(self, paths: List[ArbitragePath]) -> float:
        """
        Calculate the overall confidence level for a set of paths.
        
        Args:
            paths: List of arbitrage paths
            
        Returns:
            Overall confidence level (0.0-1.0)
        """
        if not paths:
            return 0.0
        
        # Get individual confidence levels
        confidences = [path.confidence for path in paths]
        
        # Remove zeros
        confidences = [c for c in confidences if c > 0]
        
        if not confidences:
            return 0.5  # Default confidence
        
        # Calculate weighted average of confidence levels
        return sum(confidences) / len(confidences)
    
    async def _ensure_initialized(self) -> None:
        """Ensure the path optimizer is initialized."""
        if not self._initialized:
            if not await self.initialize():
                raise RuntimeError("Failed to initialize Monte Carlo path optimizer")