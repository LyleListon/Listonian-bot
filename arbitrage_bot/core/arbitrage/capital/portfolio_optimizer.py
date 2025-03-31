"""
Portfolio Optimizer for Multi-Path Arbitrage

This module provides functionality for optimizing the overall arbitrage
portfolio for maximum risk-adjusted returns.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from ..path.interfaces import ArbitragePath, MultiPathOpportunity

logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    """
    Optimizes the overall arbitrage portfolio for maximum returns.
    """
    
    def __init__(
        self,
        risk_free_rate: Decimal = Decimal('0.02'),
        target_sharpe: Decimal = Decimal('2.0'),
        max_correlation: float = 0.7,
        rebalance_threshold: Decimal = Decimal('0.1'),
        min_weight: Decimal = Decimal('0.01'),
        max_weight: Decimal = Decimal('0.5')
    ):
        """Initialize the portfolio optimizer."""
        self.risk_free_rate = risk_free_rate
        self.target_sharpe = target_sharpe
        self.max_correlation = max_correlation
        self.rebalance_threshold = rebalance_threshold
        self.min_weight = min_weight
        self.max_weight = max_weight
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Portfolio state
        self._current_portfolio = {}
        self._historical_performance = []
        self._last_rebalance_time = 0
        
        logger.info(
            f"Initialized PortfolioOptimizer with target_sharpe={target_sharpe}, "
            f"rebalance_threshold={rebalance_threshold:.1%}"
        )
    
    async def optimize_portfolio(
        self,
        opportunities: List[MultiPathOpportunity],
        total_capital: Decimal,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Optimize capital allocation across multiple arbitrage opportunities.
        
        Args:
            opportunities: List of arbitrage opportunities
            total_capital: Total capital available
            context: Optional context information
            
        Returns:
            Optimization results
        """
        async with self._lock:
            try:
                if not opportunities:
                    return {
                        'success': False,
                        'error': 'No opportunities provided'
                    }
                
                # Apply context
                context = context or {}
                
                # Calculate simple allocations based on expected profit
                allocations = self._calculate_simple_allocations(
                    opportunities, total_capital
                )
                
                # Calculate expected portfolio metrics
                portfolio_metrics = self._calculate_simple_metrics(
                    opportunities, allocations
                )
                
                # Create result
                result = {
                    'success': True,
                    'allocations': {str(i): float(a) for i, a in enumerate(allocations)},
                    'portfolio_metrics': {
                        'expected_return': float(portfolio_metrics['expected_return']),
                        'sharpe_ratio': float(portfolio_metrics['sharpe_ratio'])
                    }
                }
                
                logger.info(
                    f"Optimized portfolio with {len(opportunities)} opportunities. "
                    f"Expected return: {portfolio_metrics['expected_return']:.2%}"
                )
                
                return result
            
            except Exception as e:
                logger.error(f"Error optimizing portfolio: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def _calculate_simple_allocations(
        self,
        opportunities: List[MultiPathOpportunity],
        total_capital: Decimal
    ) -> List[Decimal]:
        """
        Calculate simple allocations based on expected profit.
        
        Args:
            opportunities: List of arbitrage opportunities
            total_capital: Total capital available
            
        Returns:
            List of allocations
        """
        try:
            if not opportunities:
                return []
            
            # Calculate weights based on expected profit
            total_profit = sum(
                opp.expected_profit for opp in opportunities
                if opp.expected_profit > 0
            )
            
            if total_profit <= 0:
                # Equal allocation if no profitable opportunities
                equal_allocation = total_capital / Decimal(len(opportunities))
                return [equal_allocation] * len(opportunities)
            
            # Calculate weights proportional to expected profit
            weights = [
                opp.expected_profit / total_profit if opp.expected_profit > 0 else Decimal('0')
                for opp in opportunities
            ]
            
            # Apply min/max weight constraints
            constrained_weights = []
            for weight in weights:
                if weight > 0 and weight < self.min_weight:
                    weight = self.min_weight
                if weight > self.max_weight:
                    weight = self.max_weight
                constrained_weights.append(weight)
            
            # Normalize weights to sum to 1
            total_weight = sum(constrained_weights)
            if total_weight > 0:
                normalized_weights = [w / total_weight for w in constrained_weights]
            else:
                # Equal weights if all weights are 0
                normalized_weights = [Decimal('1') / Decimal(len(opportunities))] * len(opportunities)
            
            # Calculate allocations
            allocations = [w * total_capital for w in normalized_weights]
            
            return allocations
        
        except Exception as e:
            logger.error(f"Error calculating simple allocations: {e}")
            # Return equal allocation as fallback
            equal_allocation = total_capital / Decimal(max(1, len(opportunities)))
            return [equal_allocation] * len(opportunities)
    
    def _calculate_simple_metrics(
        self,
        opportunities: List[MultiPathOpportunity],
        allocations: List[Decimal]
    ) -> Dict[str, Decimal]:
        """
        Calculate simple portfolio metrics.
        
        Args:
            opportunities: List of arbitrage opportunities
            allocations: List of allocations
            
        Returns:
            Portfolio metrics
        """
        try:
            if not opportunities or not allocations or len(opportunities) != len(allocations):
                return {
                    'expected_return': Decimal('0'),
                    'sharpe_ratio': Decimal('0')
                }
            
            # Calculate total allocation
            total_allocation = sum(allocations)
            if total_allocation <= 0:
                return {
                    'expected_return': Decimal('0'),
                    'sharpe_ratio': Decimal('0')
                }
            
            # Calculate expected return
            total_profit = sum(
                opp.expected_profit for opp in opportunities
                if opp.expected_profit > 0
            )
            expected_return = total_profit / total_allocation
            
            # Calculate simple Sharpe ratio
            # Use average confidence as a proxy for volatility
            avg_confidence = sum(
                opp.confidence_level for opp in opportunities
            ) / len(opportunities)
            
            volatility = Decimal('1') - Decimal(str(avg_confidence))
            volatility = max(volatility, Decimal('0.01'))  # Avoid division by zero
            
            daily_risk_free = self.risk_free_rate / Decimal('365')
            sharpe_ratio = (expected_return - daily_risk_free) / volatility
            
            return {
                'expected_return': expected_return,
                'sharpe_ratio': sharpe_ratio
            }
        
        except Exception as e:
            logger.error(f"Error calculating simple metrics: {e}")
            return {
                'expected_return': Decimal('0'),
                'sharpe_ratio': Decimal('0')
            }
