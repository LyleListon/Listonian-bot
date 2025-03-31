"""
Gas Optimizer for Multi-Path Arbitrage

This module provides functionality for optimizing gas usage across multiple
arbitrage paths, including gas price prediction, gas sharing across related
transactions, and priority fee optimization.

Key features:
- Gas optimization across multiple paths
- Gas price prediction for optimal timing
- Gas sharing across related transactions
- Priority fee optimization
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
from ...web3.interfaces import Web3Client, Transaction

logger = logging.getLogger(__name__)

class GasOptimizer:
    """
    Optimizes gas usage for multi-path arbitrage execution.
    
    This class implements algorithms for gas optimization across multiple paths,
    gas price prediction, gas sharing across related transactions, and priority
    fee optimization.
    """
    
    def __init__(
        self,
        web3_client: Web3Client,
        base_gas_buffer: float = 1.2,
        max_gas_price: int = 500,  # gwei
        min_priority_fee: int = 1,  # gwei
        max_priority_fee: int = 10,  # gwei
        gas_price_history_window: int = 100,
        gas_price_update_interval: int = 60  # seconds
    ):
        """
        Initialize the gas optimizer.
        
        Args:
            web3_client: Web3 client for blockchain interaction
            base_gas_buffer: Buffer for gas limit estimates (default: 1.2x)
            max_gas_price: Maximum gas price in gwei (default: 500)
            min_priority_fee: Minimum priority fee in gwei (default: 1)
            max_priority_fee: Maximum priority fee in gwei (default: 10)
            gas_price_history_window: Window size for gas price history (default: 100)
            gas_price_update_interval: Interval for gas price updates in seconds (default: 60)
        """
        self.web3_client = web3_client
        self.base_gas_buffer = base_gas_buffer
        self.max_gas_price = max_gas_price
        self.min_priority_fee = min_priority_fee
        self.max_priority_fee = max_priority_fee
        self.gas_price_history_window = gas_price_history_window
        self.gas_price_update_interval = gas_price_update_interval
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Gas price history
        self._gas_price_history = []
        self._last_gas_price_update = 0
        self._current_gas_price = 0
        self._current_base_fee = 0
        
        logger.info(
            f"Initialized GasOptimizer with base_gas_buffer={base_gas_buffer}, "
            f"max_gas_price={max_gas_price} gwei"
        )
    
    async def optimize_gas(
        self,
        opportunity: MultiPathOpportunity,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Optimize gas usage for a multi-path opportunity.
        
        Args:
            opportunity: Multi-path opportunity to optimize
            context: Optional context information
                - execution_strategy: Execution strategy ("parallel", "sequential", "atomic")
                - gas_price: Current gas price in gwei
                - priority_fee: Priority fee in gwei
                - optimization_target: Optimization target ("speed", "cost", "balanced")
            
        Returns:
            Gas optimization results
        """
        async with self._lock:
            try:
                if not opportunity.paths:
                    return {
                        'success': False,
                        'error': 'No paths in opportunity'
                    }
                
                # Apply context
                context = context or {}
                
                # Update gas price if needed
                await self._update_gas_price()
                
                # Override with context gas price if provided
                gas_price = context.get('gas_price', self._current_gas_price)
                base_fee = context.get('base_fee', self._current_base_fee)
                
                # Determine execution strategy
                execution_strategy = context.get('execution_strategy', 'parallel')
                
                # Determine optimization target
                optimization_target = context.get('optimization_target', 'balanced')
                
                # Optimize gas based on strategy
                if execution_strategy == 'atomic':
                    # Optimize gas for atomic execution
                    optimization_result = await self._optimize_atomic_gas(
                        opportunity, gas_price, base_fee, optimization_target
                    )
                elif execution_strategy == 'sequential':
                    # Optimize gas for sequential execution
                    optimization_result = await self._optimize_sequential_gas(
                        opportunity, gas_price, base_fee, optimization_target
                    )
                else:
                    # Optimize gas for parallel execution
                    optimization_result = await self._optimize_parallel_gas(
                        opportunity, gas_price, base_fee, optimization_target
                    )
                
                # Calculate total gas cost
                total_gas_cost = self._calculate_total_gas_cost(optimization_result)
                
                # Create result
                result = {
                    'success': True,
                    'execution_strategy': execution_strategy,
                    'optimization_target': optimization_target,
                    'gas_price': gas_price,
                    'base_fee': base_fee,
                    'total_gas_cost': total_gas_cost,
                    'optimization_result': optimization_result
                }
                
                logger.info(
                    f"Optimized gas for {execution_strategy} execution with {len(opportunity.paths)} paths: "
                    f"gas_price={gas_price} gwei, total_cost={total_gas_cost} ETH"
                )
                
                return result
            
            except Exception as e:
                logger.error(f"Error optimizing gas: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    async def predict_gas_price(
        self,
        time_horizon: int = 60,  # seconds
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict gas price for a future time horizon.
        
        Args:
            time_horizon: Time horizon in seconds (default: 60)
            context: Optional context information
            
        Returns:
            Gas price prediction results
        """
        async with self._lock:
            try:
                # Apply context
                context = context or {}
                
                # Update gas price if needed
                await self._update_gas_price()
                
                # Predict gas price based on historical data
                predicted_gas_price = self._predict_gas_price_from_history(time_horizon)
                
                # Calculate confidence interval
                confidence_interval = self._calculate_gas_price_confidence_interval(predicted_gas_price)
                
                # Create result
                result = {
                    'success': True,
                    'current_gas_price': self._current_gas_price,
                    'current_base_fee': self._current_base_fee,
                    'predicted_gas_price': predicted_gas_price,
                    'confidence_interval': confidence_interval,
                    'time_horizon': time_horizon
                }
                
                logger.info(
                    f"Predicted gas price for {time_horizon}s horizon: "
                    f"{predicted_gas_price} gwei (current: {self._current_gas_price} gwei)"
                )
                
                return result
            
            except Exception as e:
                logger.error(f"Error predicting gas price: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'current_gas_price': self._current_gas_price
                }
    
    async def optimize_priority_fee(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Optimize priority fee for transactions.
        
        Args:
            context: Optional context information
                - gas_price: Current gas price in gwei
                - base_fee: Current base fee in gwei
                - optimization_target: Optimization target ("speed", "cost", "balanced")
            
        Returns:
            Priority fee optimization results
        """
        async with self._lock:
            try:
                # Apply context
                context = context or {}
                
                # Update gas price if needed
                await self._update_gas_price()
                
                # Override with context gas price if provided
                gas_price = context.get('gas_price', self._current_gas_price)
                base_fee = context.get('base_fee', self._current_base_fee)
                
                # Determine optimization target
                optimization_target = context.get('optimization_target', 'balanced')
                
                # Calculate optimal priority fee
                priority_fee = self._calculate_optimal_priority_fee(
                    gas_price, base_fee, optimization_target
                )
                
                # Create result
                result = {
                    'success': True,
                    'gas_price': gas_price,
                    'base_fee': base_fee,
                    'priority_fee': priority_fee,
                    'optimization_target': optimization_target
                }
                
                logger.info(
                    f"Optimized priority fee for {optimization_target} target: "
                    f"{priority_fee} gwei (gas_price: {gas_price} gwei, base_fee: {base_fee} gwei)"
                )
                
                return result
            
            except Exception as e:
                logger.error(f"Error optimizing priority fee: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'priority_fee': self.min_priority_fee
                }
    
    async def estimate_gas_for_path(
        self,
        path: ArbitragePath,
        allocation: Decimal,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Estimate gas usage for a path.
        
        Args:
            path: Arbitrage path
            allocation: Allocated capital for the path
            context: Optional context information
            
        Returns:
            Gas estimation results
        """
        try:
            # Apply context
            context = context or {}
            
            # Estimate base gas usage
            base_gas = self._estimate_base_gas(path)
            
            # Apply buffer
            buffered_gas = int(base_gas * self.base_gas_buffer)
            
            # Create result
            result = {
                'success': True,
                'path': path,
                'allocation': float(allocation),
                'base_gas': base_gas,
                'buffered_gas': buffered_gas
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error estimating gas for path: {e}")
            return {
                'success': False,
                'error': str(e),
                'path': path
            }
    
    async def _update_gas_price(self) -> None:
        """Update current gas price if needed."""
        try:
            current_time = time.time()
            
            # Check if update is needed
            if current_time - self._last_gas_price_update >= self.gas_price_update_interval:
                # Get current gas price from web3 client
                gas_price = await self.web3_client.get_gas_price()
                gas_price_gwei = gas_price / 1e9
                
                # Get current base fee if available
                try:
                    base_fee = await self.web3_client.get_base_fee()
                    base_fee_gwei = base_fee / 1e9
                except:
                    # Fallback to gas price if base fee is not available
                    base_fee_gwei = gas_price_gwei * 0.8
                
                # Update current values
                self._current_gas_price = gas_price_gwei
                self._current_base_fee = base_fee_gwei
                
                # Add to history
                self._gas_price_history.append({
                    'timestamp': current_time,
                    'gas_price': gas_price_gwei,
                    'base_fee': base_fee_gwei
                })
                
                # Limit history size
                if len(self._gas_price_history) > self.gas_price_history_window:
                    self._gas_price_history = self._gas_price_history[-self.gas_price_history_window:]
                
                # Update timestamp
                self._last_gas_price_update = current_time
                
                logger.debug(
                    f"Updated gas price: {gas_price_gwei:.1f} gwei, "
                    f"base fee: {base_fee_gwei:.1f} gwei"
                )
        
        except Exception as e:
            logger.error(f"Error updating gas price: {e}")
    
    async def _optimize_atomic_gas(
        self,
        opportunity: MultiPathOpportunity,
        gas_price: float,
        base_fee: float,
        optimization_target: str
    ) -> Dict[str, Any]:
        """
        Optimize gas for atomic execution.
        
        Args:
            opportunity: Multi-path opportunity
            gas_price: Current gas price in gwei
            base_fee: Current base fee in gwei
            optimization_target: Optimization target
            
        Returns:
            Gas optimization results
        """
        try:
            # Estimate total gas usage
            total_gas = 0
            path_gas = []
            
            for i, path in enumerate(opportunity.paths):
                # Estimate gas for this path
                path_result = await self.estimate_gas_for_path(
                    path, opportunity.allocations[i], {'gas_price': gas_price}
                )
                
                if path_result['success']:
                    # Add to total
                    total_gas += path_result['buffered_gas']
                    
                    # Add to path gas
                    path_gas.append({
                        'path_index': i,
                        'gas': path_result['buffered_gas']
                    })
            
            # Calculate gas savings from atomic execution
            # In atomic execution, we can save gas by combining operations
            gas_savings = int(total_gas * 0.2)  # Assume 20% savings
            optimized_gas = total_gas - gas_savings
            
            # Calculate priority fee based on optimization target
            priority_fee = self._calculate_optimal_priority_fee(
                gas_price, base_fee, optimization_target
            )
            
            # Calculate gas cost
            gas_cost_wei = optimized_gas * (base_fee + priority_fee) * 1e9
            gas_cost_eth = gas_cost_wei / 1e18
            
            # Create result
            result = {
                'total_gas': total_gas,
                'optimized_gas': optimized_gas,
                'gas_savings': gas_savings,
                'gas_savings_percent': gas_savings / total_gas if total_gas > 0 else 0,
                'priority_fee': priority_fee,
                'gas_cost_wei': gas_cost_wei,
                'gas_cost_eth': gas_cost_eth,
                'path_gas': path_gas
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error optimizing atomic gas: {e}")
            return {
                'total_gas': 0,
                'optimized_gas': 0,
                'gas_savings': 0,
                'gas_savings_percent': 0,
                'priority_fee': self.min_priority_fee,
                'gas_cost_wei': 0,
                'gas_cost_eth': 0,
                'path_gas': []
            }
    
    async def _optimize_sequential_gas(
        self,
        opportunity: MultiPathOpportunity,
        gas_price: float,
        base_fee: float,
        optimization_target: str
    ) -> Dict[str, Any]:
        """
        Optimize gas for sequential execution.
        
        Args:
            opportunity: Multi-path opportunity
            gas_price: Current gas price in gwei
            base_fee: Current base fee in gwei
            optimization_target: Optimization target
            
        Returns:
            Gas optimization results
        """
        try:
            # Estimate gas for each path
            path_results = []
            
            for i, path in enumerate(opportunity.paths):
                # Estimate gas for this path
                path_result = await self.estimate_gas_for_path(
                    path, opportunity.allocations[i], {'gas_price': gas_price}
                )
                
                if path_result['success']:
                    # Add to results
                    path_results.append({
                        'path_index': i,
                        'gas': path_result['buffered_gas'],
                        'priority_fee': self._calculate_optimal_priority_fee(
                            gas_price, base_fee, optimization_target
                        )
                    })
            
            # Calculate total gas
            total_gas = sum(result['gas'] for result in path_results)
            
            # No gas savings in sequential execution
            optimized_gas = total_gas
            gas_savings = 0
            
            # Calculate gas cost
            gas_cost_wei = sum(
                result['gas'] * (base_fee + result['priority_fee']) * 1e9
                for result in path_results
            )
            gas_cost_eth = gas_cost_wei / 1e18
            
            # Create result
            result = {
                'total_gas': total_gas,
                'optimized_gas': optimized_gas,
                'gas_savings': gas_savings,
                'gas_savings_percent': 0,
                'path_results': path_results,
                'gas_cost_wei': gas_cost_wei,
                'gas_cost_eth': gas_cost_eth
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error optimizing sequential gas: {e}")
            return {
                'total_gas': 0,
                'optimized_gas': 0,
                'gas_savings': 0,
                'gas_savings_percent': 0,
                'path_results': [],
                'gas_cost_wei': 0,
                'gas_cost_eth': 0
            }
    
    async def _optimize_parallel_gas(
        self,
        opportunity: MultiPathOpportunity,
        gas_price: float,
        base_fee: float,
        optimization_target: str
    ) -> Dict[str, Any]:
        """
        Optimize gas for parallel execution.
        
        Args:
            opportunity: Multi-path opportunity
            gas_price: Current gas price in gwei
            base_fee: Current base fee in gwei
            optimization_target: Optimization target
            
        Returns:
            Gas optimization results
        """
        try:
            # Estimate gas for each path
            path_results = []
            
            for i, path in enumerate(opportunity.paths):
                # Estimate gas for this path
                path_result = await self.estimate_gas_for_path(
                    path, opportunity.allocations[i], {'gas_price': gas_price}
                )
                
                if path_result['success']:
                    # Add to results
                    path_results.append({
                        'path_index': i,
                        'gas': path_result['buffered_gas'],
                        'priority_fee': self._calculate_optimal_priority_fee(
                            gas_price, base_fee, optimization_target
                        )
                    })
            
            # Calculate total gas
            total_gas = sum(result['gas'] for result in path_results)
            
            # No gas savings in parallel execution
            optimized_gas = total_gas
            gas_savings = 0
            
            # Calculate gas cost
            gas_cost_wei = sum(
                result['gas'] * (base_fee + result['priority_fee']) * 1e9
                for result in path_results
            )
            gas_cost_eth = gas_cost_wei / 1e18
            
            # Create result
            result = {
                'total_gas': total_gas,
                'optimized_gas': optimized_gas,
                'gas_savings': gas_savings,
                'gas_savings_percent': 0,
                'path_results': path_results,
                'gas_cost_wei': gas_cost_wei,
                'gas_cost_eth': gas_cost_eth
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error optimizing parallel gas: {e}")
            return {
                'total_gas': 0,
                'optimized_gas': 0,
                'gas_savings': 0,
                'gas_savings_percent': 0,
                'path_results': [],
                'gas_cost_wei': 0,
                'gas_cost_eth': 0
            }
    
    def _predict_gas_price_from_history(
        self,
        time_horizon: int
    ) -> float:
        """
        Predict gas price based on historical data.
        
        Args:
            time_horizon: Time horizon in seconds
            
        Returns:
            Predicted gas price in gwei
        """
        try:
            if not self._gas_price_history:
                return self._current_gas_price
            
            # Extract timestamps and gas prices
            timestamps = [entry['timestamp'] for entry in self._gas_price_history]
            gas_prices = [entry['gas_price'] for entry in self._gas_price_history]
            
            # Calculate time differences
            time_diffs = [t - timestamps[0] for t in timestamps]
            
            # Fit linear regression
            if len(time_diffs) > 1:
                # Use numpy for linear regression
                slope, intercept = np.polyfit(time_diffs, gas_prices, 1)
                
                # Predict gas price
                prediction_time = time_diffs[-1] + time_horizon
                predicted_gas_price = slope * prediction_time + intercept
                
                # Ensure prediction is positive
                predicted_gas_price = max(1.0, predicted_gas_price)
                
                # Cap at maximum
                predicted_gas_price = min(predicted_gas_price, self.max_gas_price)
                
                return predicted_gas_price
            else:
                # Not enough data for regression
                return self._current_gas_price
        
        except Exception as e:
            logger.error(f"Error predicting gas price from history: {e}")
            return self._current_gas_price
    
    def _calculate_gas_price_confidence_interval(
        self,
        predicted_gas_price: float
    ) -> Dict[str, float]:
        """
        Calculate confidence interval for gas price prediction.
        
        Args:
            predicted_gas_price: Predicted gas price in gwei
            
        Returns:
            Confidence interval
        """
        try:
            if not self._gas_price_history:
                return {
                    'lower': predicted_gas_price * 0.8,
                    'upper': predicted_gas_price * 1.2
                }
            
            # Extract gas prices
            gas_prices = [entry['gas_price'] for entry in self._gas_price_history]
            
            # Calculate standard deviation
            std_dev = np.std(gas_prices) if len(gas_prices) > 1 else predicted_gas_price * 0.1
            
            # Calculate confidence interval (95%)
            lower_bound = max(1.0, predicted_gas_price - 1.96 * std_dev)
            upper_bound = min(self.max_gas_price, predicted_gas_price + 1.96 * std_dev)
            
            return {
                'lower': lower_bound,
                'upper': upper_bound
            }
        
        except Exception as e:
            logger.error(f"Error calculating gas price confidence interval: {e}")
            return {
                'lower': predicted_gas_price * 0.8,
                'upper': predicted_gas_price * 1.2
            }
    
    def _calculate_optimal_priority_fee(
        self,
        gas_price: float,
        base_fee: float,
        optimization_target: str
    ) -> float:
        """
        Calculate optimal priority fee based on optimization target.
        
        Args:
            gas_price: Current gas price in gwei
            base_fee: Current base fee in gwei
            optimization_target: Optimization target
            
        Returns:
            Optimal priority fee in gwei
        """
        try:
            if optimization_target == 'speed':
                # Prioritize speed - use higher priority fee
                priority_fee = min(self.max_priority_fee, base_fee * 0.5)
            elif optimization_target == 'cost':
                # Prioritize cost - use lower priority fee
                priority_fee = self.min_priority_fee
            else:
                # Balanced approach
                priority_fee = min(self.max_priority_fee, base_fee * 0.2)
            
            # Ensure priority fee is within bounds
            priority_fee = max(self.min_priority_fee, min(self.max_priority_fee, priority_fee))
            
            return priority_fee
        
        except Exception as e:
            logger.error(f"Error calculating optimal priority fee: {e}")
            return self.min_priority_fee
    
    def _estimate_base_gas(
        self,
        path: ArbitragePath
    ) -> int:
        """
        Estimate base gas usage for a path.
        
        Args:
            path: Arbitrage path
            
        Returns:
            Estimated gas usage
        """
        try:
            # Base gas cost for a transaction
            base_gas = 21000
            
            # Gas cost per hop
            hop_gas_costs = {
                'uniswap_v2': 90000,
                'uniswap_v3': 120000,
                'sushiswap': 90000,
                'pancakeswap_v2': 90000,
                'pancakeswap_v3': 120000,
                'default': 100000
            }
            
            # Calculate total gas
            total_gas = base_gas
            
            for i, pool in enumerate(path.pools):
                dex = path.dexes[i] if i < len(path.dexes) else 'default'
                hop_gas = hop_gas_costs.get(dex, hop_gas_costs['default'])
                total_gas += hop_gas
            
            return total_gas
        
        except Exception as e:
            logger.error(f"Error estimating base gas: {e}")
            return 500000  # Default gas limit
    
    def _calculate_total_gas_cost(
        self,
        optimization_result: Dict[str, Any]
    ) -> float:
        """
        Calculate total gas cost in ETH.
        
        Args:
            optimization_result: Gas optimization result
            
        Returns:
            Total gas cost in ETH
        """
        try:
            return optimization_result.get('gas_cost_eth', 0)
        
        except Exception as e:
            logger.error(f"Error calculating total gas cost: {e}")
            return 0