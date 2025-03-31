"""
Slippage Manager for Arbitrage Execution

This module provides functionality for managing slippage during arbitrage
execution, including dynamic slippage tolerance calculation, slippage
monitoring, and adaptive strategies.

Key features:
- Dynamic slippage tolerance calculation
- Slippage monitoring during execution
- Adaptive strategies based on observed slippage
- Slippage prediction models
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Set, Union
import numpy as np
from collections import defaultdict

from ..path.interfaces import ArbitragePath, Pool, MultiPathOpportunity
from ...utils.async_utils import gather_with_concurrency
from ...utils.retry import with_retry
from ...web3.interfaces import Web3Client

logger = logging.getLogger(__name__)

class SlippageManager:
    """
    Manages slippage during arbitrage execution.
    
    This class implements algorithms for dynamic slippage tolerance calculation,
    slippage monitoring during execution, and adaptive strategies based on
    observed slippage.
    """
    
    def __init__(
        self,
        web3_client: Optional[Web3Client] = None,
        base_slippage_tolerance: Decimal = Decimal('0.005'),
        max_slippage_tolerance: Decimal = Decimal('0.03'),
        slippage_buffer: Decimal = Decimal('1.2'),
        history_window: int = 100,
        adaptation_rate: float = 0.1
    ):
        """
        Initialize the slippage manager.
        
        Args:
            web3_client: Web3 client for on-chain validation (optional)
            base_slippage_tolerance: Base slippage tolerance (default: 0.5%)
            max_slippage_tolerance: Maximum slippage tolerance (default: 3%)
            slippage_buffer: Buffer for slippage estimates (default: 1.2x)
            history_window: Window size for slippage history (default: 100)
            adaptation_rate: Rate of adaptation to observed slippage (default: 0.1)
        """
        self.web3_client = web3_client
        self.base_slippage_tolerance = base_slippage_tolerance
        self.max_slippage_tolerance = max_slippage_tolerance
        self.slippage_buffer = slippage_buffer
        self.history_window = history_window
        self.adaptation_rate = adaptation_rate
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Slippage history
        self._pool_slippage_history = defaultdict(list)
        self._token_slippage_history = defaultdict(list)
        self._dex_slippage_history = defaultdict(list)
        
        logger.info(
            f"Initialized SlippageManager with base_slippage_tolerance={base_slippage_tolerance:.2%}, "
            f"max_slippage_tolerance={max_slippage_tolerance:.2%}"
        )
    
    async def calculate_slippage_tolerance(
        self,
        path: ArbitragePath,
        amount: Decimal,
        context: Optional[Dict[str, Any]] = None
    ) -> Decimal:
        """
        Calculate slippage tolerance for a path.
        
        Args:
            path: Arbitrage path
            amount: Input amount
            context: Optional context information
                - market_volatility: Market volatility indicator (0.0-1.0)
                - gas_price: Current gas price in gwei
                - execution_priority: Priority for execution (e.g., "speed", "profit")
            
        Returns:
            Slippage tolerance as a decimal (0.0-1.0)
        """
        async with self._lock:
            try:
                # Apply context
                context = context or {}
                
                # Start with base slippage tolerance
                slippage_tolerance = self.base_slippage_tolerance
                
                # Adjust for path complexity
                complexity_factor = Decimal(str(min(1.0, len(path.pools) / 5.0)))
                slippage_tolerance += complexity_factor * Decimal('0.005')  # Add 0.5% per complexity unit
                
                # Adjust for market volatility
                market_volatility = Decimal(str(context.get('market_volatility', 0.5)))
                slippage_tolerance += market_volatility * Decimal('0.01')  # Add up to 1% for high volatility
                
                # Adjust for historical slippage
                historical_slippage = await self._calculate_historical_slippage(path)
                slippage_tolerance = max(slippage_tolerance, historical_slippage)
                
                # Adjust for amount relative to pool liquidity
                amount_factor = await self._calculate_amount_factor(path, amount)
                slippage_tolerance += amount_factor * Decimal('0.01')  # Add up to 1% for large amounts
                
                # Apply buffer
                slippage_tolerance *= self.slippage_buffer
                
                # Cap at maximum
                slippage_tolerance = min(slippage_tolerance, self.max_slippage_tolerance)
                
                logger.debug(
                    f"Calculated slippage tolerance for path with {len(path.pools)} hops: "
                    f"{slippage_tolerance:.2%}"
                )
                
                return slippage_tolerance
            
            except Exception as e:
                logger.error(f"Error calculating slippage tolerance: {e}")
                return self.max_slippage_tolerance  # Return maximum as fallback
    
    async def predict_slippage(
        self,
        path: ArbitragePath,
        amount: Decimal,
        context: Optional[Dict[str, Any]] = None
    ) -> Decimal:
        """
        Predict slippage for a path.
        
        Args:
            path: Arbitrage path
            amount: Input amount
            context: Optional context information
            
        Returns:
            Predicted slippage as a decimal (0.0-1.0)
        """
        try:
            # Apply context
            context = context or {}
            
            # Calculate slippage for each hop
            total_slippage = Decimal('0')
            
            for i, pool in enumerate(path.pools):
                # Get tokens for this hop
                token_in = path.tokens[i]
                token_out = path.tokens[i + 1]
                
                # Calculate hop slippage
                hop_slippage = await self._calculate_hop_slippage(pool, token_in, token_out, amount)
                
                # Accumulate slippage
                # This is a simplified approach - in reality, slippage compounds
                total_slippage += hop_slippage
            
            logger.debug(
                f"Predicted slippage for path with {len(path.pools)} hops: "
                f"{total_slippage:.2%}"
            )
            
            return total_slippage
        
        except Exception as e:
            logger.error(f"Error predicting slippage: {e}")
            return Decimal('0.01')  # Return 1% as fallback
    
    async def monitor_slippage(
        self,
        path: ArbitragePath,
        amount: Decimal,
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Monitor slippage during execution.
        
        Args:
            path: Arbitrage path
            amount: Input amount
            execution_result: Execution result
            
        Returns:
            Slippage monitoring results
        """
        async with self._lock:
            try:
                # Extract actual output from execution result
                actual_output = self._extract_actual_output(execution_result)
                
                if actual_output is None:
                    return {
                        'success': False,
                        'error': 'Failed to extract actual output from execution result'
                    }
                
                # Calculate expected output
                expected_output = await self._calculate_expected_output(path, amount)
                
                if expected_output is None or expected_output <= 0:
                    return {
                        'success': False,
                        'error': 'Failed to calculate expected output'
                    }
                
                # Calculate actual slippage
                actual_slippage = (expected_output - actual_output) / expected_output
                
                # Ensure non-negative slippage
                actual_slippage = max(Decimal('0'), actual_slippage)
                
                # Update slippage history
                self._update_slippage_history(path, actual_slippage)
                
                # Create monitoring result
                result = {
                    'success': True,
                    'expected_output': float(expected_output),
                    'actual_output': float(actual_output),
                    'actual_slippage': float(actual_slippage),
                    'excessive_slippage': actual_slippage > self.max_slippage_tolerance
                }
                
                logger.info(
                    f"Monitored slippage for path with {len(path.pools)} hops: "
                    f"expected={expected_output}, actual={actual_output}, "
                    f"slippage={actual_slippage:.2%}"
                )
                
                return result
            
            except Exception as e:
                logger.error(f"Error monitoring slippage: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    async def adapt_strategy(
        self,
        path: ArbitragePath,
        monitoring_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Adapt strategy based on observed slippage.
        
        Args:
            path: Arbitrage path
            monitoring_result: Slippage monitoring results
            context: Optional context information
            
        Returns:
            Adapted strategy
        """
        try:
            if not monitoring_result.get('success', False):
                return {
                    'success': False,
                    'error': 'Invalid monitoring result'
                }
            
            # Apply context
            context = context or {}
            
            # Extract slippage from monitoring result
            actual_slippage = Decimal(str(monitoring_result.get('actual_slippage', 0)))
            
            # Check if slippage is excessive
            excessive_slippage = actual_slippage > self.max_slippage_tolerance
            
            # Determine adaptation strategy
            if excessive_slippage:
                # Reduce amount for future executions
                amount_reduction_factor = Decimal('0.8')  # Reduce by 20%
                
                # Increase slippage tolerance for future executions
                new_base_slippage = self.base_slippage_tolerance * (Decimal('1') + self.adaptation_rate)
                
                strategy = {
                    'action': 'reduce_amount',
                    'amount_reduction_factor': float(amount_reduction_factor),
                    'new_base_slippage': float(new_base_slippage)
                }
            else:
                # Maintain or slightly increase amount for future executions
                amount_increase_factor = Decimal('1.05')  # Increase by 5%
                
                # Potentially decrease slippage tolerance for future executions
                if actual_slippage < self.base_slippage_tolerance * Decimal('0.5'):
                    # Actual slippage is less than half of base tolerance
                    new_base_slippage = self.base_slippage_tolerance * (Decimal('1') - self.adaptation_rate)
                    new_base_slippage = max(new_base_slippage, Decimal('0.001'))  # Minimum 0.1%
                    
                    strategy = {
                        'action': 'increase_amount',
                        'amount_increase_factor': float(amount_increase_factor),
                        'new_base_slippage': float(new_base_slippage)
                    }
                else:
                    # Maintain current slippage tolerance
                    strategy = {
                        'action': 'maintain',
                        'amount_increase_factor': float(amount_increase_factor),
                        'new_base_slippage': float(self.base_slippage_tolerance)
                    }
            
            # Create adaptation result
            result = {
                'success': True,
                'excessive_slippage': excessive_slippage,
                'strategy': strategy
            }
            
            # Apply adaptation if auto-adapt is enabled
            if context.get('auto_adapt', False):
                self._apply_adaptation(strategy)
            
            logger.info(
                f"Adapted strategy based on slippage={actual_slippage:.2%}: "
                f"action={strategy['action']}"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error adapting strategy: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _calculate_historical_slippage(
        self,
        path: ArbitragePath
    ) -> Decimal:
        """
        Calculate historical slippage for a path.
        
        Args:
            path: Arbitrage path
            
        Returns:
            Historical slippage as a decimal (0.0-1.0)
        """
        try:
            # Calculate pool-specific slippage
            pool_slippages = []
            
            for pool in path.pools:
                pool_history = self._pool_slippage_history.get(pool.address, [])
                if pool_history:
                    # Use 95th percentile of historical slippage
                    pool_slippages.append(np.percentile(pool_history, 95))
            
            # Calculate token-specific slippage
            token_slippages = []
            
            for token in path.tokens:
                token_history = self._token_slippage_history.get(token, [])
                if token_history:
                    # Use 95th percentile of historical slippage
                    token_slippages.append(np.percentile(token_history, 95))
            
            # Calculate DEX-specific slippage
            dex_slippages = []
            
            for dex in path.dexes:
                dex_history = self._dex_slippage_history.get(dex, [])
                if dex_history:
                    # Use 95th percentile of historical slippage
                    dex_slippages.append(np.percentile(dex_history, 95))
            
            # Combine slippages
            if pool_slippages and token_slippages and dex_slippages:
                # Use maximum of averages
                avg_pool_slippage = sum(pool_slippages) / len(pool_slippages)
                avg_token_slippage = sum(token_slippages) / len(token_slippages)
                avg_dex_slippage = sum(dex_slippages) / len(dex_slippages)
                
                return Decimal(str(max(avg_pool_slippage, avg_token_slippage, avg_dex_slippage)))
            elif pool_slippages:
                # Use average pool slippage
                return Decimal(str(sum(pool_slippages) / len(pool_slippages)))
            elif token_slippages:
                # Use average token slippage
                return Decimal(str(sum(token_slippages) / len(token_slippages)))
            elif dex_slippages:
                # Use average DEX slippage
                return Decimal(str(sum(dex_slippages) / len(dex_slippages)))
            else:
                # No historical data
                return self.base_slippage_tolerance
        
        except Exception as e:
            logger.error(f"Error calculating historical slippage: {e}")
            return self.base_slippage_tolerance
    
    async def _calculate_amount_factor(
        self,
        path: ArbitragePath,
        amount: Decimal
    ) -> Decimal:
        """
        Calculate factor based on amount relative to pool liquidity.
        
        Args:
            path: Arbitrage path
            amount: Input amount
            
        Returns:
            Amount factor as a decimal (0.0-1.0)
        """
        try:
            # Calculate amount factor for each pool
            pool_factors = []
            
            for i, pool in enumerate(path.pools):
                # Skip pools without reserves
                if pool.reserves0 is None or pool.reserves1 is None:
                    continue
                
                # Get tokens for this hop
                token_in = path.tokens[i]
                token_out = path.tokens[i + 1]
                
                # Determine token order in the pool
                if token_in == pool.token0 and token_out == pool.token1:
                    # token0 -> token1
                    reserve_in = pool.reserves0
                elif token_in == pool.token1 and token_out == pool.token0:
                    # token1 -> token0
                    reserve_in = pool.reserves1
                else:
                    # Invalid token pair
                    continue
                
                # Calculate amount relative to reserve
                amount_ratio = amount / reserve_in
                
                # Calculate factor (0.0-1.0)
                # This is a simplified approach - in reality, we would use a more
                # sophisticated model based on the pool type and its pricing function
                factor = Decimal('1') - Decimal('1') / (Decimal('1') + amount_ratio * Decimal('10'))
                
                pool_factors.append(factor)
            
            # Use maximum factor
            if pool_factors:
                return max(pool_factors)
            else:
                return Decimal('0')
        
        except Exception as e:
            logger.error(f"Error calculating amount factor: {e}")
            return Decimal('0')
    
    async def _calculate_hop_slippage(
        self,
        pool: Pool,
        token_in: str,
        token_out: str,
        amount: Decimal
    ) -> Decimal:
        """
        Calculate slippage for a single hop.
        
        Args:
            pool: Liquidity pool
            token_in: Input token address
            token_out: Output token address
            amount: Input amount
            
        Returns:
            Estimated slippage as a decimal (0.0-1.0)
        """
        try:
            # Check if pool has reserves
            if pool.reserves0 is None or pool.reserves1 is None:
                return Decimal('0.01')  # Default slippage if reserves unknown
            
            # Determine token order in the pool
            if token_in == pool.token0 and token_out == pool.token1:
                # token0 -> token1
                reserve_in = pool.reserves0
                reserve_out = pool.reserves1
            elif token_in == pool.token1 and token_out == pool.token0:
                # token1 -> token0
                reserve_in = pool.reserves1
                reserve_out = pool.reserves0
            else:
                # Invalid token pair
                logger.warning(f"Invalid token pair: {token_in} -> {token_out} in pool {pool.address}")
                return Decimal('0.01')  # Default slippage
            
            # Calculate amount relative to reserve
            amount_ratio = amount / reserve_in
            
            # Apply slippage model based on pool type
            if pool.pool_type == "constant_product":
                # For constant product pools (e.g., Uniswap V2),
                # slippage increases quadratically with amount ratio
                slippage = amount_ratio * amount_ratio
            elif pool.pool_type == "stable":
                # For stable pools, slippage is lower
                slippage = amount_ratio * amount_ratio * Decimal('0.5')
            else:
                # Default to constant product model
                slippage = amount_ratio * amount_ratio
            
            # Cap slippage at reasonable values
            return min(slippage, Decimal('0.1'))  # Max 10% slippage
        
        except Exception as e:
            logger.error(f"Error calculating hop slippage: {e}")
            return Decimal('0.01')  # Default slippage
    
    def _extract_actual_output(
        self,
        execution_result: Dict[str, Any]
    ) -> Optional[Decimal]:
        """
        Extract actual output from execution result.
        
        Args:
            execution_result: Execution result
            
        Returns:
            Actual output amount or None if not available
        """
        try:
            # This is a placeholder - in a real implementation,
            # we would extract the actual output from the execution result
            # based on the specific format of the result
            
            # For now, return None
            return None
        
        except Exception as e:
            logger.error(f"Error extracting actual output: {e}")
            return None
    
    async def _calculate_expected_output(
        self,
        path: ArbitragePath,
        amount: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate expected output for a path.
        
        Args:
            path: Arbitrage path
            amount: Input amount
            
        Returns:
            Expected output amount or None if calculation fails
        """
        try:
            # This is a simplified implementation - in a real system,
            # we would use a more sophisticated simulation that accounts
            # for fees and other factors
            
            current_amount = amount
            
            # Simulate each hop in the path
            for i in range(len(path.pools)):
                pool = path.pools[i]
                token_in = path.tokens[i]
                token_out = path.tokens[i + 1]
                
                # Skip pools without reserves
                if pool.reserves0 is None or pool.reserves1 is None:
                    return None
                
                # Determine token order in the pool
                if token_in == pool.token0 and token_out == pool.token1:
                    # token0 -> token1
                    reserve_in = pool.reserves0
                    reserve_out = pool.reserves1
                elif token_in == pool.token1 and token_out == pool.token0:
                    # token1 -> token0
                    reserve_in = pool.reserves1
                    reserve_out = pool.reserves0
                else:
                    # Invalid token pair
                    logger.warning(f"Invalid token pair: {token_in} -> {token_out} in pool {pool.address}")
                    return None
                
                # Apply pool-specific pricing function
                if pool.pool_type == "constant_product":
                    # Constant product formula: x * y = k
                    # dy = y * dx / (x + dx)
                    numerator = reserve_out * current_amount
                    denominator = reserve_in + current_amount
                    output_amount = numerator / denominator
                elif pool.pool_type == "stable":
                    # Simplified stable swap formula
                    # In reality, this would be more complex
                    output_amount = current_amount
                else:
                    # Default to constant product
                    numerator = reserve_out * current_amount
                    denominator = reserve_in + current_amount
                    output_amount = numerator / denominator
                
                # Apply fees
                fee_multiplier = Decimal('1') - (Decimal(str(pool.fee)) / Decimal('10000'))
                output_amount = output_amount * fee_multiplier
                
                # Update current amount for next hop
                current_amount = output_amount
            
            return current_amount
        
        except Exception as e:
            logger.error(f"Error calculating expected output: {e}")
            return None
    
    def _update_slippage_history(
        self,
        path: ArbitragePath,
        slippage: Decimal
    ) -> None:
        """
        Update slippage history.
        
        Args:
            path: Arbitrage path
            slippage: Observed slippage
        """
        try:
            # Update pool slippage history
            for pool in path.pools:
                self._pool_slippage_history[pool.address].append(float(slippage))
                
                # Limit history size
                if len(self._pool_slippage_history[pool.address]) > self.history_window:
                    self._pool_slippage_history[pool.address] = self._pool_slippage_history[pool.address][-self.history_window:]
            
            # Update token slippage history
            for token in path.tokens:
                self._token_slippage_history[token].append(float(slippage))
                
                # Limit history size
                if len(self._token_slippage_history[token]) > self.history_window:
                    self._token_slippage_history[token] = self._token_slippage_history[token][-self.history_window:]
            
            # Update DEX slippage history
            for dex in path.dexes:
                self._dex_slippage_history[dex].append(float(slippage))
                
                # Limit history size
                if len(self._dex_slippage_history[dex]) > self.history_window:
                    self._dex_slippage_history[dex] = self._dex_slippage_history[dex][-self.history_window:]
        
        except Exception as e:
            logger.error(f"Error updating slippage history: {e}")
    
    def _apply_adaptation(
        self,
        strategy: Dict[str, Any]
    ) -> None:
        """
        Apply adaptation strategy.
        
        Args:
            strategy: Adaptation strategy
        """
        try:
            # Update base slippage tolerance
            if 'new_base_slippage' in strategy:
                self.base_slippage_tolerance = Decimal(str(strategy['new_base_slippage']))
                
                # Ensure base slippage is within reasonable bounds
                self.base_slippage_tolerance = max(Decimal('0.001'), min(self.base_slippage_tolerance, self.max_slippage_tolerance))
            
            logger.info(f"Applied adaptation: base_slippage_tolerance={self.base_slippage_tolerance:.2%}")
        
        except Exception as e:
            logger.error(f"Error applying adaptation: {e}")