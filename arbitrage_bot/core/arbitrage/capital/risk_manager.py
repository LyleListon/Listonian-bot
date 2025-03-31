"""
Risk Manager for Multi-Path Arbitrage

This module provides functionality for assessing and managing risk for
arbitrage opportunities, including risk scoring, position sizing, and
maximum drawdown protection.

Key features:
- Risk scoring for arbitrage opportunities
- Position sizing based on risk assessment
- Maximum drawdown protection
- Correlation analysis for diversification
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

class RiskManager:
    """
    Assesses and manages risk for arbitrage opportunities.
    
    This class implements algorithms for risk scoring, position sizing,
    maximum drawdown protection, and correlation analysis for diversification.
    """
    
    def __init__(
        self,
        max_risk_per_trade: Decimal = Decimal('0.02'),
        max_risk_per_token: Decimal = Decimal('0.05'),
        max_risk_per_dex: Decimal = Decimal('0.1'),
        max_drawdown: Decimal = Decimal('0.1'),
        risk_free_rate: Decimal = Decimal('0.02'),
        volatility_window: int = 100,
        correlation_threshold: float = 0.7
    ):
        """
        Initialize the risk manager.
        
        Args:
            max_risk_per_trade: Maximum risk per trade as percentage of capital (default: 2%)
            max_risk_per_token: Maximum risk per token as percentage of capital (default: 5%)
            max_risk_per_dex: Maximum risk per DEX as percentage of capital (default: 10%)
            max_drawdown: Maximum acceptable drawdown (default: 10%)
            risk_free_rate: Annual risk-free rate for Sharpe ratio calculation (default: 2%)
            volatility_window: Window size for volatility calculation (default: 100)
            correlation_threshold: Threshold for high correlation (default: 0.7)
        """
        self.max_risk_per_trade = max_risk_per_trade
        self.max_risk_per_token = max_risk_per_token
        self.max_risk_per_dex = max_risk_per_dex
        self.max_drawdown = max_drawdown
        self.risk_free_rate = risk_free_rate
        self.volatility_window = volatility_window
        self.correlation_threshold = correlation_threshold
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Historical performance data
        self._trade_history = []
        self._token_risk_exposure = defaultdict(Decimal)
        self._dex_risk_exposure = defaultdict(Decimal)
        self._current_drawdown = Decimal('0')
        self._peak_capital = Decimal('0')
        self._current_capital = Decimal('0')
        
        logger.info(
            f"Initialized RiskManager with max_risk_per_trade={max_risk_per_trade:.1%}, "
            f"max_drawdown={max_drawdown:.1%}"
        )
    
    async def assess_risk(
        self,
        path: ArbitragePath,
        allocation: Decimal,
        total_capital: Decimal,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assess risk for a single arbitrage path.
        
        Args:
            path: Arbitrage path to assess
            allocation: Allocated capital for the path
            total_capital: Total capital available
            context: Optional context information
                - market_volatility: Market volatility indicator (0.0-1.0)
                - gas_price: Current gas price in gwei
                - token_prices: Dictionary of token prices
            
        Returns:
            Risk assessment results
        """
        async with self._lock:
            try:
                # Apply context
                context = context or {}
                
                # Calculate risk metrics
                risk_score = self._calculate_risk_score(path, context)
                max_loss = self._calculate_max_loss(path, allocation)
                risk_adjusted_return = self._calculate_risk_adjusted_return(path, allocation, max_loss)
                sharpe_ratio = self._calculate_sharpe_ratio(path, context)
                
                # Calculate risk exposure
                token_exposure = self._calculate_token_exposure(path, allocation, total_capital)
                dex_exposure = self._calculate_dex_exposure(path, allocation, total_capital)
                
                # Check if risk is acceptable
                risk_acceptable = self._is_risk_acceptable(
                    path, allocation, total_capital, max_loss, token_exposure, dex_exposure
                )
                
                # Calculate maximum acceptable position size
                max_position_size = self._calculate_max_position_size(
                    path, total_capital, context
                )
                
                # Create risk assessment result
                assessment = {
                    'risk_score': float(risk_score),
                    'max_loss': float(max_loss),
                    'risk_adjusted_return': float(risk_adjusted_return),
                    'sharpe_ratio': float(sharpe_ratio),
                    'token_exposure': {token: float(exposure) for token, exposure in token_exposure.items()},
                    'dex_exposure': {dex: float(exposure) for dex, exposure in dex_exposure.items()},
                    'risk_acceptable': risk_acceptable,
                    'max_position_size': float(max_position_size)
                }
                
                return assessment
            
            except Exception as e:
                logger.error(f"Error assessing risk: {e}")
                return {
                    'risk_score': 1.0,
                    'max_loss': float(allocation),
                    'risk_adjusted_return': 0.0,
                    'sharpe_ratio': 0.0,
                    'token_exposure': {},
                    'dex_exposure': {},
                    'risk_acceptable': False,
                    'max_position_size': 0.0
                }
    
    async def assess_opportunity_risk(
        self,
        opportunity: MultiPathOpportunity,
        total_capital: Decimal,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assess risk for a multi-path opportunity.
        
        Args:
            opportunity: Multi-path opportunity to assess
            total_capital: Total capital available
            context: Optional context information
            
        Returns:
            Risk assessment results
        """
        async with self._lock:
            try:
                if not opportunity.paths or not opportunity.allocations:
                    return {
                        'risk_score': 1.0,
                        'max_loss': float(opportunity.required_amount),
                        'risk_acceptable': False,
                        'max_position_size': 0.0
                    }
                
                # Apply context
                context = context or {}
                
                # Assess risk for each path
                path_assessments = []
                for path, allocation in zip(opportunity.paths, opportunity.allocations):
                    assessment = await self.assess_risk(
                        path, allocation, total_capital, context
                    )
                    path_assessments.append(assessment)
                
                # Calculate combined risk metrics
                combined_risk_score = self._calculate_combined_risk_score(path_assessments)
                combined_max_loss = self._calculate_combined_max_loss(path_assessments)
                combined_sharpe = self._calculate_combined_sharpe(path_assessments)
                
                # Calculate correlation-adjusted risk
                correlation_adjusted_risk = self._calculate_correlation_adjusted_risk(
                    opportunity.paths, opportunity.allocations, path_assessments
                )
                
                # Check if combined risk is acceptable
                risk_acceptable = combined_max_loss <= (total_capital * self.max_risk_per_trade)
                
                # Calculate maximum acceptable position size
                max_position_size = self._calculate_max_opportunity_size(
                    opportunity, total_capital, context
                )
                
                # Create risk assessment result
                assessment = {
                    'risk_score': float(combined_risk_score),
                    'max_loss': float(combined_max_loss),
                    'sharpe_ratio': float(combined_sharpe),
                    'correlation_adjusted_risk': float(correlation_adjusted_risk),
                    'path_assessments': path_assessments,
                    'risk_acceptable': risk_acceptable,
                    'max_position_size': float(max_position_size),
                    'diversification_benefit': float(combined_max_loss - correlation_adjusted_risk)
                }
                
                return assessment
            
            except Exception as e:
                logger.error(f"Error assessing opportunity risk: {e}")
                return {
                    'risk_score': 1.0,
                    'max_loss': float(opportunity.required_amount),
                    'risk_acceptable': False,
                    'max_position_size': 0.0
                }
    
    async def size_position(
        self,
        path: ArbitragePath,
        total_capital: Decimal,
        context: Optional[Dict[str, Any]] = None
    ) -> Decimal:
        """
        Calculate optimal position size for a path based on risk assessment.
        
        Args:
            path: Arbitrage path
            total_capital: Total capital available
            context: Optional context information
            
        Returns:
            Optimal position size
        """
        try:
            # Apply context
            context = context or {}
            
            # Calculate maximum position size based on risk
            max_position = self._calculate_max_position_size(path, total_capital, context)
            
            # If path has an optimal amount, use the smaller of the two
            if path.optimal_amount is not None and path.optimal_amount > 0:
                position_size = min(max_position, path.optimal_amount)
            else:
                position_size = max_position
            
            logger.debug(
                f"Sized position for path: {position_size} "
                f"(max_position={max_position}, "
                f"optimal_amount={path.optimal_amount})"
            )
            
            return position_size
        
        except Exception as e:
            logger.error(f"Error sizing position: {e}")
            return Decimal('0')
    
    async def update_risk_metrics(
        self,
        trade_result: Dict[str, Any],
        current_capital: Decimal
    ) -> None:
        """
        Update risk metrics based on trade results.
        
        Args:
            trade_result: Trade result information
                - paths: List of paths used in the trade
                - allocations: List of allocations used
                - profit_loss: Profit or loss from the trade
                - success: Whether the trade was successful
            current_capital: Current total capital
        """
        async with self._lock:
            try:
                # Update trade history
                self._trade_history.append({
                    'timestamp': time.time(),
                    'trade_result': trade_result,
                    'capital': current_capital
                })
                
                # Limit history size
                if len(self._trade_history) > self.volatility_window:
                    self._trade_history = self._trade_history[-self.volatility_window:]
                
                # Update current capital
                self._current_capital = current_capital
                
                # Update peak capital
                if current_capital > self._peak_capital:
                    self._peak_capital = current_capital
                
                # Update current drawdown
                if self._peak_capital > 0:
                    self._current_drawdown = (self._peak_capital - current_capital) / self._peak_capital
                
                # Update token and DEX risk exposure
                self._update_risk_exposure(trade_result)
                
                logger.debug(
                    f"Updated risk metrics: current_capital={current_capital}, "
                    f"current_drawdown={self._current_drawdown:.2%}"
                )
            
            except Exception as e:
                logger.error(f"Error updating risk metrics: {e}")
    
    def _calculate_risk_score(
        self,
        path: ArbitragePath,
        context: Dict[str, Any]
    ) -> Decimal:
        """
        Calculate risk score for a path.
        
        Args:
            path: Arbitrage path
            context: Context information
            
        Returns:
            Risk score (0.0-1.0, where higher is riskier)
        """
        try:
            # Base risk is inverse of confidence
            base_risk = Decimal('1') - Decimal(str(path.confidence))
            
            # Adjust for path complexity
            complexity_factor = Decimal(str(min(1.0, len(path.pools) / 5.0)))
            
            # Adjust for market volatility
            market_volatility = Decimal(str(context.get('market_volatility', 0.5)))
            
            # Calculate combined risk score
            risk_score = (
                base_risk * Decimal('0.5') +
                complexity_factor * Decimal('0.3') +
                market_volatility * Decimal('0.2')
            )
            
            return risk_score
        
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return Decimal('1.0')  # Maximum risk as fallback
    
    def _calculate_max_loss(
        self,
        path: ArbitragePath,
        allocation: Decimal
    ) -> Decimal:
        """
        Calculate maximum potential loss for a path.
        
        Args:
            path: Arbitrage path
            allocation: Allocated capital
            
        Returns:
            Maximum potential loss
        """
        try:
            # In worst case, we lose the entire allocation
            # This is a simplified approach - in reality, we would need to
            # consider slippage, gas costs, and other factors
            
            # Calculate loss probability (inverse of confidence)
            loss_probability = Decimal('1') - Decimal(str(path.confidence))
            
            # Calculate expected loss
            expected_loss = allocation * loss_probability
            
            # Add gas costs
            if path.estimated_gas_cost is not None:
                expected_loss += path.estimated_gas_cost
            
            return expected_loss
        
        except Exception as e:
            logger.error(f"Error calculating max loss: {e}")
            return allocation  # Assume worst case
    
    def _calculate_risk_adjusted_return(
        self,
        path: ArbitragePath,
        allocation: Decimal,
        max_loss: Decimal
    ) -> Decimal:
        """
        Calculate risk-adjusted return for a path.
        
        Args:
            path: Arbitrage path
            allocation: Allocated capital
            max_loss: Maximum potential loss
            
        Returns:
            Risk-adjusted return
        """
        try:
            if path.profit is None or max_loss <= 0:
                return Decimal('0')
            
            # Calculate expected profit
            expected_profit = path.profit * Decimal(str(path.confidence))
            
            # Calculate risk-adjusted return
            return expected_profit / max_loss
        
        except Exception as e:
            logger.error(f"Error calculating risk-adjusted return: {e}")
            return Decimal('0')
    
    def _calculate_sharpe_ratio(
        self,
        path: ArbitragePath,
        context: Dict[str, Any]
    ) -> Decimal:
        """
        Calculate Sharpe ratio for a path.
        
        Args:
            path: Arbitrage path
            context: Context information
            
        Returns:
            Sharpe ratio
        """
        try:
            if path.profit is None or path.optimal_amount is None or path.optimal_amount <= 0:
                return Decimal('0')
            
            # Calculate expected return
            expected_return = path.profit / path.optimal_amount
            
            # Adjust for confidence
            expected_return *= Decimal(str(path.confidence))
            
            # Calculate volatility (simplified)
            volatility = Decimal('1') - Decimal(str(path.confidence))
            volatility = max(volatility, Decimal('0.01'))  # Avoid division by zero
            
            # Calculate Sharpe ratio
            # (expected_return - risk_free_rate) / volatility
            daily_risk_free = self.risk_free_rate / Decimal('365')
            sharpe = (expected_return - daily_risk_free) / volatility
            
            return sharpe
        
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return Decimal('0')
    
    def _calculate_token_exposure(
        self,
        path: ArbitragePath,
        allocation: Decimal,
        total_capital: Decimal
    ) -> Dict[str, Decimal]:
        """
        Calculate token exposure for a path.
        
        Args:
            path: Arbitrage path
            allocation: Allocated capital
            total_capital: Total capital available
            
        Returns:
            Dictionary of token exposures as percentage of total capital
        """
        try:
            exposures = {}
            
            for token in path.tokens:
                # Calculate exposure for this token
                exposure = allocation / total_capital
                
                # Add to existing exposure
                exposures[token] = exposure
            
            return exposures
        
        except Exception as e:
            logger.error(f"Error calculating token exposure: {e}")
            return {}
    
    def _calculate_dex_exposure(
        self,
        path: ArbitragePath,
        allocation: Decimal,
        total_capital: Decimal
    ) -> Dict[str, Decimal]:
        """
        Calculate DEX exposure for a path.
        
        Args:
            path: Arbitrage path
            allocation: Allocated capital
            total_capital: Total capital available
            
        Returns:
            Dictionary of DEX exposures as percentage of total capital
        """
        try:
            exposures = {}
            
            for dex in path.dexes:
                # Calculate exposure for this DEX
                exposure = allocation / total_capital
                
                # Add to existing exposure
                exposures[dex] = exposure
            
            return exposures
        
        except Exception as e:
            logger.error(f"Error calculating DEX exposure: {e}")
            return {}
    
    def _is_risk_acceptable(
        self,
        path: ArbitragePath,
        allocation: Decimal,
        total_capital: Decimal,
        max_loss: Decimal,
        token_exposure: Dict[str, Decimal],
        dex_exposure: Dict[str, Decimal]
    ) -> bool:
        """
        Check if risk is acceptable.
        
        Args:
            path: Arbitrage path
            allocation: Allocated capital
            total_capital: Total capital available
            max_loss: Maximum potential loss
            token_exposure: Token exposure
            dex_exposure: DEX exposure
            
        Returns:
            True if risk is acceptable, False otherwise
        """
        try:
            # Check if max loss exceeds max risk per trade
            if max_loss > (total_capital * self.max_risk_per_trade):
                return False
            
            # Check if token exposure exceeds max risk per token
            for token, exposure in token_exposure.items():
                if exposure > self.max_risk_per_token:
                    return False
            
            # Check if DEX exposure exceeds max risk per DEX
            for dex, exposure in dex_exposure.items():
                if exposure > self.max_risk_per_dex:
                    return False
            
            # Check if current drawdown exceeds max drawdown
            if self._current_drawdown > self.max_drawdown:
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error checking if risk is acceptable: {e}")
            return False
    
    def _calculate_max_position_size(
        self,
        path: ArbitragePath,
        total_capital: Decimal,
        context: Dict[str, Any]
    ) -> Decimal:
        """
        Calculate maximum position size based on risk assessment.
        
        Args:
            path: Arbitrage path
            total_capital: Total capital available
            context: Context information
            
        Returns:
            Maximum position size
        """
        try:
            # Calculate risk score
            risk_score = self._calculate_risk_score(path, context)
            
            # Calculate max position size based on max risk per trade
            max_position = total_capital * self.max_risk_per_trade
            
            # Adjust based on risk score
            adjusted_position = max_position * (Decimal('1') - risk_score)
            
            # Ensure position is not too small
            min_position = total_capital * Decimal('0.01')  # 1% of capital
            adjusted_position = max(adjusted_position, min_position)
            
            # Adjust for current drawdown
            if self._current_drawdown > Decimal('0'):
                drawdown_factor = Decimal('1') - (self._current_drawdown / self.max_drawdown)
                adjusted_position *= drawdown_factor
            
            return adjusted_position
        
        except Exception as e:
            logger.error(f"Error calculating max position size: {e}")
            return Decimal('0')
    
    def _calculate_combined_risk_score(
        self,
        path_assessments: List[Dict[str, Any]]
    ) -> Decimal:
        """
        Calculate combined risk score for multiple paths.
        
        Args:
            path_assessments: List of path risk assessments
            
        Returns:
            Combined risk score
        """
        try:
            if not path_assessments:
                return Decimal('1.0')
            
            # Calculate weighted average risk score
            total_risk_score = Decimal('0')
            total_weight = Decimal('0')
            
            for assessment in path_assessments:
                risk_score = Decimal(str(assessment['risk_score']))
                # Use max_loss as weight
                weight = Decimal(str(assessment['max_loss']))
                
                total_risk_score += risk_score * weight
                total_weight += weight
            
            if total_weight > 0:
                return total_risk_score / total_weight
            else:
                return Decimal('1.0')
        
        except Exception as e:
            logger.error(f"Error calculating combined risk score: {e}")
            return Decimal('1.0')
    
    def _calculate_combined_max_loss(
        self,
        path_assessments: List[Dict[str, Any]]
    ) -> Decimal:
        """
        Calculate combined maximum loss for multiple paths.
        
        Args:
            path_assessments: List of path risk assessments
            
        Returns:
            Combined maximum loss
        """
        try:
            if not path_assessments:
                return Decimal('0')
            
            # Sum max losses
            total_max_loss = Decimal('0')
            
            for assessment in path_assessments:
                max_loss = Decimal(str(assessment['max_loss']))
                total_max_loss += max_loss
            
            return total_max_loss
        
        except Exception as e:
            logger.error(f"Error calculating combined max loss: {e}")
            return Decimal('0')
    
    def _calculate_combined_sharpe(
        self,
        path_assessments: List[Dict[str, Any]]
    ) -> Decimal:
        """
        Calculate combined Sharpe ratio for multiple paths.
        
        Args:
            path_assessments: List of path risk assessments
            
        Returns:
            Combined Sharpe ratio
        """
        try:
            if not path_assessments:
                return Decimal('0')
            
            # Calculate weighted average Sharpe ratio
            total_sharpe = Decimal('0')
            total_weight = Decimal('0')
            
            for assessment in path_assessments:
                sharpe = Decimal(str(assessment.get('sharpe_ratio', 0)))
                # Use max_loss as weight
                weight = Decimal(str(assessment['max_loss']))
                
                total_sharpe += sharpe * weight
                total_weight += weight
            
            if total_weight > 0:
                return total_sharpe / total_weight
            else:
                return Decimal('0')
        
        except Exception as e:
            logger.error(f"Error calculating combined Sharpe ratio: {e}")
            return Decimal('0')
    
    def _calculate_correlation_adjusted_risk(
        self,
        paths: List[ArbitragePath],
        allocations: List[Decimal],
        path_assessments: List[Dict[str, Any]]
    ) -> Decimal:
        """
        Calculate correlation-adjusted risk for multiple paths.
        
        Args:
            paths: List of arbitrage paths
            allocations: List of allocations
            path_assessments: List of path risk assessments
            
        Returns:
            Correlation-adjusted risk
        """
        try:
            if not paths or not allocations or not path_assessments:
                return Decimal('0')
            
            # This is a simplified approach - in reality, we would need to
            # calculate the full correlation matrix and use portfolio theory
            
            # Check for path correlations
            correlation_groups = self._group_correlated_paths(paths)
            
            # Calculate adjusted risk
            adjusted_risk = Decimal('0')
            
            for group in correlation_groups:
                group_risk = Decimal('0')
                
                for i in group:
                    if i < len(path_assessments):
                        max_loss = Decimal(str(path_assessments[i]['max_loss']))
                        group_risk += max_loss
                
                adjusted_risk += group_risk
            
            return adjusted_risk
        
        except Exception as e:
            logger.error(f"Error calculating correlation-adjusted risk: {e}")
            return self._calculate_combined_max_loss(path_assessments)
    
    def _group_correlated_paths(
        self,
        paths: List[ArbitragePath]
    ) -> List[List[int]]:
        """
        Group correlated paths.
        
        Args:
            paths: List of arbitrage paths
            
        Returns:
            List of groups, where each group is a list of path indices
        """
        try:
            if not paths:
                return []
            
            # Calculate correlation matrix
            n = len(paths)
            correlation_matrix = np.zeros((n, n))
            
            for i in range(n):
                for j in range(i + 1, n):
                    correlation = self._calculate_path_correlation(paths[i], paths[j])
                    correlation_matrix[i, j] = correlation
                    correlation_matrix[j, i] = correlation
            
            # Group paths using a simple threshold-based approach
            correlation_threshold = self.correlation_threshold
            groups = []
            visited = set()
            
            for i in range(n):
                if i in visited:
                    continue
                
                group = [i]
                visited.add(i)
                
                for j in range(n):
                    if j in visited:
                        continue
                    
                    if correlation_matrix[i, j] > correlation_threshold:
                        group.append(j)
                        visited.add(j)
                
                groups.append(group)
            
            return groups
        
        except Exception as e:
            logger.error(f"Error grouping correlated paths: {e}")
            return [[i] for i in range(len(paths))]  # Each path in its own group
    
    def _calculate_path_correlation(
        self,
        path1: ArbitragePath,
        path2: ArbitragePath
    ) -> float:
        """
        Calculate correlation between two paths.
        
        Args:
            path1: First arbitrage path
            path2: Second arbitrage path
            
        Returns:
            Correlation coefficient (-1.0 to 1.0)
        """
        try:
            # Calculate token overlap
            tokens1 = set(path1.tokens)
            tokens2 = set(path2.tokens)
            token_overlap = len(tokens1.intersection(tokens2)) / len(tokens1.union(tokens2))
            
            # Calculate pool overlap
            pools1 = set(pool.address for pool in path1.pools)
            pools2 = set(pool.address for pool in path2.pools)
            pool_overlap = len(pools1.intersection(pools2)) / len(pools1.union(pools2))
            
            # Calculate DEX overlap
            dexes1 = set(path1.dexes)
            dexes2 = set(path2.dexes)
            dex_overlap = len(dexes1.intersection(dexes2)) / len(dexes1.union(dexes2))
            
            # Calculate correlation
            correlation = (
                token_overlap * 0.4 +
                pool_overlap * 0.4 +
                dex_overlap * 0.2
            )
            
            return correlation
        
        except Exception as e:
            logger.error(f"Error calculating path correlation: {e}")
            return 0.0
    
    def _calculate_max_opportunity_size(
        self,
        opportunity: MultiPathOpportunity,
        total_capital: Decimal,
        context: Dict[str, Any]
    ) -> Decimal:
        """
        Calculate maximum size for a multi-path opportunity.
        
        Args:
            opportunity: Multi-path opportunity
            total_capital: Total capital available
            context: Context information
            
        Returns:
            Maximum opportunity size
        """
        try:
            # Calculate max size based on max risk per trade
            max_size = total_capital * self.max_risk_per_trade
            
            # Adjust based on opportunity confidence
            confidence = Decimal(str(opportunity.confidence_level))
            adjusted_size = max_size * confidence
            
            # Adjust for current drawdown
            if self._current_drawdown > Decimal('0'):
                drawdown_factor = Decimal('1') - (self._current_drawdown / self.max_drawdown)
                adjusted_size *= drawdown_factor
            
            return adjusted_size
        
        except Exception as e:
            logger.error(f"Error calculating max opportunity size: {e}")
            return Decimal('0')
    
    def _update_risk_exposure(
        self,
        trade_result: Dict[str, Any]
    ) -> None:
        """
        Update token and DEX risk exposure based on trade results.
        
        Args:
            trade_result: Trade result information
        """
        try:
            paths = trade_result.get('paths', [])
            allocations = trade_result.get('allocations', [])
            
            if not paths or not allocations or len(paths) != len(allocations):
                return
            
            # Reset exposures
            self._token_risk_exposure = defaultdict(Decimal)
            self._dex_risk_exposure = defaultdict(Decimal)
            
            # Update exposures
            for path, allocation in zip(paths, allocations):
                # Update token exposure
                for token in path.tokens:
                    self._token_risk_exposure[token] += allocation
                
                # Update DEX exposure
                for dex in path.dexes:
                    self._dex_risk_exposure[dex] += allocation
        
        except Exception as e:
            logger.error(f"Error updating risk exposure: {e}")