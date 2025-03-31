"""
Capital Allocator for Multi-Path Arbitrage

This module provides functionality for optimizing capital allocation across
multiple arbitrage paths to maximize risk-adjusted returns.

Key features:
- Kelly criterion for optimal bet sizing
- Risk-adjusted returns calculation
- Dynamic capital allocation based on market conditions
- Capital preservation strategies
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Set, Union
import numpy as np
from collections import defaultdict

from ..path.interfaces import ArbitragePath, MultiPathOpportunity
from ...utils.async_utils import gather_with_concurrency
from ...utils.retry import with_retry

logger = logging.getLogger(__name__)

class CapitalAllocator:
    """
    Optimizes capital allocation across multiple arbitrage paths.
    
    This class implements algorithms for determining the optimal distribution
    of capital across multiple arbitrage paths to maximize risk-adjusted returns.
    It uses the Kelly criterion and other portfolio optimization techniques.
    """
    
    def __init__(
        self,
        min_allocation_percent: Decimal = Decimal('0.05'),
        max_allocation_percent: Decimal = Decimal('0.5'),
        kelly_fraction: Decimal = Decimal('0.5'),
        risk_aversion: Decimal = Decimal('1.0'),
        max_drawdown_percent: Decimal = Decimal('0.1'),
        capital_reserve_percent: Decimal = Decimal('0.2')
    ):
        """
        Initialize the capital allocator.
        
        Args:
            min_allocation_percent: Minimum allocation percentage for any path (default: 5%)
            max_allocation_percent: Maximum allocation percentage for any path (default: 50%)
            kelly_fraction: Fraction of Kelly criterion to use (default: 0.5)
            risk_aversion: Risk aversion parameter (default: 1.0)
            max_drawdown_percent: Maximum acceptable drawdown (default: 10%)
            capital_reserve_percent: Percentage of capital to keep in reserve (default: 20%)
        """
        self.min_allocation_percent = min_allocation_percent
        self.max_allocation_percent = max_allocation_percent
        self.kelly_fraction = kelly_fraction
        self.risk_aversion = risk_aversion
        self.max_drawdown_percent = max_drawdown_percent
        self.capital_reserve_percent = capital_reserve_percent
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Historical performance data
        self._path_performance = {}
        self._market_conditions = {}
        self._last_allocations = {}
        
        logger.info(
            f"Initialized CapitalAllocator with kelly_fraction={kelly_fraction}, "
            f"risk_aversion={risk_aversion}, "
            f"capital_reserve_percent={capital_reserve_percent:.1%}"
        )
    
    async def allocate_capital(
        self,
        paths: List[ArbitragePath],
        total_capital: Decimal,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Decimal], Decimal]:
        """
        Allocate capital across multiple arbitrage paths.
        
        Args:
            paths: List of arbitrage paths to allocate capital across
            total_capital: Total capital available for allocation
            context: Optional context information
                - market_volatility: Market volatility indicator (0.0-1.0)
                - gas_price: Current gas price in gwei
                - token_prices: Dictionary of token prices
                - risk_profile: Risk profile ("conservative", "moderate", "aggressive")
            
        Returns:
            Tuple of (allocations, expected_profit), where allocations is a
            list of allocated amounts for each path, and expected_profit is
            the expected total profit
        """
        async with self._lock:
            try:
                if not paths:
                    return [], Decimal('0')
                
                # Apply context
                context = context or {}
                
                # Calculate available capital after reserve
                available_capital = total_capital * (Decimal('1') - self.capital_reserve_percent)
                
                # Calculate optimal allocations using Kelly criterion
                kelly_allocations = self._calculate_kelly_allocations(paths, available_capital)
                
                # Adjust allocations based on risk profile
                adjusted_allocations = self._adjust_allocations_for_risk(
                    paths, kelly_allocations, context
                )
                
                # Apply constraints (min/max allocation)
                constrained_allocations = self._apply_allocation_constraints(
                    paths, adjusted_allocations, available_capital
                )
                
                # Calculate expected profit
                expected_profit = self._calculate_expected_profit(paths, constrained_allocations)
                
                # Update historical data
                self._update_allocation_history(paths, constrained_allocations)
                
                logger.info(
                    f"Allocated {sum(constrained_allocations)} of {total_capital} "
                    f"across {len(paths)} paths. "
                    f"Expected profit: {expected_profit}"
                )
                
                return constrained_allocations, expected_profit
            
            except Exception as e:
                logger.error(f"Error allocating capital: {e}")
                # Return equal allocation as fallback
                equal_allocation = total_capital / Decimal(max(1, len(paths)))
                allocations = [equal_allocation] * len(paths)
                return allocations, Decimal('0')
    
    async def create_opportunity(
        self,
        paths: List[ArbitragePath],
        total_capital: Decimal,
        context: Optional[Dict[str, Any]] = None
    ) -> MultiPathOpportunity:
        """
        Create a multi-path opportunity with optimized capital allocation.
        
        Args:
            paths: List of arbitrage paths
            total_capital: Total capital available
            context: Optional context information
            
        Returns:
            Multi-path arbitrage opportunity
        """
        try:
            if not paths:
                raise ValueError("No paths provided")
            
            # Allocate capital
            allocations, expected_profit = await self.allocate_capital(
                paths, total_capital, context
            )
            
            # Create opportunity
            opportunity = MultiPathOpportunity(
                paths=paths,
                start_token=paths[0].start_token,
                required_amount=sum(allocations),
                expected_profit=expected_profit,
                allocations=allocations,
                confidence_level=min(path.confidence for path in paths),
                created_at=int(time.time())
            )
            
            # Set expiration time (5 minutes from now)
            opportunity.expiration = int(time.time()) + 300
            
            return opportunity
        
        except Exception as e:
            logger.error(f"Error creating opportunity: {e}")
            raise
    
    async def rebalance_allocations(
        self,
        opportunity: MultiPathOpportunity,
        context: Optional[Dict[str, Any]] = None
    ) -> MultiPathOpportunity:
        """
        Rebalance capital allocations for an existing opportunity.
        
        Args:
            opportunity: Multi-path opportunity to rebalance
            context: Optional context information
            
        Returns:
            Rebalanced multi-path opportunity
        """
        try:
            if not opportunity.paths or not opportunity.allocations:
                return opportunity
            
            # Get current total capital
            total_capital = sum(opportunity.allocations)
            
            # Reallocate capital
            new_allocations, new_expected_profit = await self.allocate_capital(
                opportunity.paths, total_capital, context
            )
            
            # Update opportunity
            opportunity.allocations = new_allocations
            opportunity.expected_profit = new_expected_profit
            opportunity.required_amount = sum(new_allocations)
            
            logger.info(
                f"Rebalanced allocations for opportunity with {len(opportunity.paths)} paths. "
                f"New expected profit: {new_expected_profit}"
            )
            
            return opportunity
        
        except Exception as e:
            logger.error(f"Error rebalancing allocations: {e}")
            return opportunity
    
    def _calculate_kelly_allocations(
        self,
        paths: List[ArbitragePath],
        available_capital: Decimal
    ) -> List[Decimal]:
        """
        Calculate optimal allocations using the Kelly criterion.
        
        Args:
            paths: List of arbitrage paths
            available_capital: Available capital for allocation
            
        Returns:
            List of allocated amounts for each path
        """
        try:
            # Calculate Kelly fraction for each path
            kelly_fractions = []
            
            for path in paths:
                if path.optimal_amount is None or path.expected_output is None:
                    kelly_fractions.append(Decimal('0'))
                    continue
                
                # Calculate win probability (confidence)
                win_probability = Decimal(str(path.confidence))
                
                # Calculate odds (profit per unit of capital)
                if path.optimal_amount > 0:
                    odds = (path.expected_output / path.optimal_amount) - Decimal('1')
                else:
                    odds = Decimal('0')
                
                # Calculate Kelly fraction: f* = (bp - q) / b
                # where b = odds, p = win probability, q = 1 - p
                if odds > 0:
                    kelly = (win_probability * odds - (Decimal('1') - win_probability)) / odds
                    
                    # Apply Kelly fraction adjustment
                    kelly *= self.kelly_fraction
                    
                    # Ensure non-negative allocation
                    kelly = max(Decimal('0'), kelly)
                else:
                    kelly = Decimal('0')
                
                kelly_fractions.append(kelly)
            
            # Normalize fractions to sum to 1
            total_fraction = sum(kelly_fractions)
            if total_fraction > 0:
                normalized_fractions = [f / total_fraction for f in kelly_fractions]
            else:
                # Equal allocation if all Kelly fractions are 0
                normalized_fractions = [Decimal('1') / Decimal(len(paths))] * len(paths)
            
            # Calculate allocations
            allocations = [f * available_capital for f in normalized_fractions]
            
            return allocations
        
        except Exception as e:
            logger.error(f"Error calculating Kelly allocations: {e}")
            # Return equal allocation as fallback
            equal_allocation = available_capital / Decimal(max(1, len(paths)))
            return [equal_allocation] * len(paths)
    
    def _adjust_allocations_for_risk(
        self,
        paths: List[ArbitragePath],
        allocations: List[Decimal],
        context: Dict[str, Any]
    ) -> List[Decimal]:
        """
        Adjust allocations based on risk profile and market conditions.
        
        Args:
            paths: List of arbitrage paths
            allocations: Initial allocations
            context: Context information
            
        Returns:
            Adjusted allocations
        """
        try:
            # Get risk profile from context
            risk_profile = context.get('risk_profile', 'moderate')
            
            # Get market volatility from context
            market_volatility = Decimal(str(context.get('market_volatility', 0.5)))
            
            # Adjust risk aversion based on risk profile
            risk_adjustment = Decimal('1.0')
            if risk_profile == 'conservative':
                risk_adjustment = Decimal('1.5')
            elif risk_profile == 'moderate':
                risk_adjustment = Decimal('1.0')
            elif risk_profile == 'aggressive':
                risk_adjustment = Decimal('0.7')
            
            # Adjust risk aversion based on market volatility
            volatility_adjustment = Decimal('1.0') + market_volatility
            
            # Calculate combined risk adjustment
            combined_adjustment = risk_adjustment * volatility_adjustment
            
            # Apply risk adjustment to allocations
            adjusted_allocations = []
            for i, allocation in enumerate(allocations):
                path = paths[i]
                
                # Calculate path-specific risk adjustment
                path_risk = Decimal('1.0') - Decimal(str(path.confidence))
                path_adjustment = Decimal('1.0') + (path_risk * combined_adjustment)
                
                # Adjust allocation
                adjusted_allocation = allocation / path_adjustment
                adjusted_allocations.append(adjusted_allocation)
            
            # Normalize allocations to maintain the same total
            total_allocation = sum(allocations)
            total_adjusted = sum(adjusted_allocations)
            
            if total_adjusted > 0:
                normalized_allocations = [
                    alloc * (total_allocation / total_adjusted)
                    for alloc in adjusted_allocations
                ]
            else:
                normalized_allocations = allocations
            
            return normalized_allocations
        
        except Exception as e:
            logger.error(f"Error adjusting allocations for risk: {e}")
            return allocations
    
    def _apply_allocation_constraints(
        self,
        paths: List[ArbitragePath],
        allocations: List[Decimal],
        available_capital: Decimal
    ) -> List[Decimal]:
        """
        Apply min/max allocation constraints.
        
        Args:
            paths: List of arbitrage paths
            allocations: Initial allocations
            available_capital: Available capital for allocation
            
        Returns:
            Constrained allocations
        """
        try:
            # Calculate min and max allocation amounts
            min_allocation = available_capital * self.min_allocation_percent
            max_allocation = available_capital * self.max_allocation_percent
            
            # Apply constraints
            constrained_allocations = []
            for i, allocation in enumerate(allocations):
                path = paths[i]
                
                # Skip allocation if path is not profitable
                if path.profit is None or path.profit <= 0:
                    constrained_allocations.append(Decimal('0'))
                    continue
                
                # Apply min allocation constraint
                if allocation > 0 and allocation < min_allocation:
                    allocation = min_allocation
                
                # Apply max allocation constraint
                if allocation > max_allocation:
                    allocation = max_allocation
                
                # Apply path-specific constraints
                if path.optimal_amount is not None and path.optimal_amount > 0:
                    # Don't allocate more than optimal amount
                    allocation = min(allocation, path.optimal_amount)
                
                constrained_allocations.append(allocation)
            
            # Normalize allocations to not exceed available capital
            total_constrained = sum(constrained_allocations)
            if total_constrained > available_capital:
                normalized_allocations = [
                    alloc * (available_capital / total_constrained)
                    for alloc in constrained_allocations
                ]
            else:
                normalized_allocations = constrained_allocations
            
            return normalized_allocations
        
        except Exception as e:
            logger.error(f"Error applying allocation constraints: {e}")
            return allocations
    
    def _calculate_expected_profit(
        self,
        paths: List[ArbitragePath],
        allocations: List[Decimal]
    ) -> Decimal:
        """
        Calculate expected profit from the allocations.
        
        Args:
            paths: List of arbitrage paths
            allocations: Allocated amounts
            
        Returns:
            Expected profit
        """
        try:
            total_profit = Decimal('0')
            
            for i, (path, allocation) in enumerate(zip(paths, allocations)):
                if allocation <= 0:
                    continue
                
                # Calculate profit for this path with the allocated capital
                if path.optimal_amount is not None and path.optimal_amount > 0 and path.profit is not None:
                    # Calculate profit rate (profit per unit of capital)
                    profit_rate = path.profit / path.optimal_amount
                    
                    # Calculate expected profit
                    path_profit = profit_rate * allocation
                    
                    # Adjust for confidence
                    adjusted_profit = path_profit * Decimal(str(path.confidence))
                    
                    total_profit += adjusted_profit
            
            return total_profit
        
        except Exception as e:
            logger.error(f"Error calculating expected profit: {e}")
            return Decimal('0')
    
    def _update_allocation_history(
        self,
        paths: List[ArbitragePath],
        allocations: List[Decimal]
    ) -> None:
        """
        Update historical allocation data.
        
        Args:
            paths: List of arbitrage paths
            allocations: Allocated amounts
        """
        try:
            current_time = int(time.time())
            
            for i, (path, allocation) in enumerate(zip(paths, allocations)):
                path_id = self._get_path_identifier(path)
                
                if path_id not in self._last_allocations:
                    self._last_allocations[path_id] = []
                
                # Add allocation to history
                self._last_allocations[path_id].append({
                    'timestamp': current_time,
                    'allocation': allocation,
                    'optimal_amount': path.optimal_amount,
                    'expected_profit': path.profit,
                    'confidence': path.confidence
                })
                
                # Limit history size
                if len(self._last_allocations[path_id]) > 100:
                    self._last_allocations[path_id] = self._last_allocations[path_id][-100:]
        
        except Exception as e:
            logger.error(f"Error updating allocation history: {e}")
    
    def _get_path_identifier(self, path: ArbitragePath) -> str:
        """
        Generate a unique identifier for a path.
        
        Args:
            path: Arbitrage path
            
        Returns:
            Unique identifier string
        """
        try:
            # Create a string representation of the path
            path_elements = []
            
            for i, token in enumerate(path.tokens):
                path_elements.append(token)
                if i < len(path.pools):
                    path_elements.append(path.pools[i].address)
            
            return ":".join(path_elements)
        
        except Exception as e:
            logger.error(f"Error generating path identifier: {e}")
            return str(hash(tuple(path.tokens)))