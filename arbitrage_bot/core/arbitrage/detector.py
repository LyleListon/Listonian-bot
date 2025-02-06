"""Aggressive arbitrage detector using ML predictions."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
from dataclasses import dataclass

from ..ml.models.manager import ModelManager
from ..dex.dex_manager import DEXManager

@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity."""
    path: List[str]  # List of token addresses in the path
    expected_profit: float
    confidence: float
    gas_cost: float
    execution_time: float  # Estimated execution time in seconds
    position_size: float
    risk_score: float
    timestamp: datetime
    metadata: Dict[str, Any]

class AggressiveArbitrageDetector:
    """Detect and evaluate arbitrage opportunities using ML predictions."""
    
    def __init__(
        self,
        model_manager: ModelManager,
        dex_manager: DEXManager,
        config: Dict[str, Any]
    ):
        """
        Initialize arbitrage detector.
        
        Args:
            model_manager: ML model manager
            dex_manager: DEX manager
            config: Configuration dictionary containing:
                - min_profit_threshold: Minimum profit to consider
                - max_position_size: Maximum position size
                - risk_tolerance: Risk tolerance (0-1)
                - execution_speed: Target execution speed
                - monitoring: Monitoring settings
        """
        self.model_manager = model_manager
        self.dex_manager = dex_manager
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize opportunity tracking
        self.opportunities: List[ArbitrageOpportunity] = []
        self.active_trades: Dict[str, Dict[str, Any]] = {}
        self.performance_stats = {
            'opportunities_found': 0,
            'trades_executed': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'average_execution_time': 0.0
        }
        
        # Configure risk management
        self.risk_manager = RiskManager(config.get('risk_management', {}))
        
        self._running = False
        self._detection_task = None
        
    async def start(self):
        """Start arbitrage detection."""
        self._running = True
        self._detection_task = asyncio.create_task(self._detect_opportunities())
        self.logger.info("Arbitrage detector started")
        
    async def stop(self):
        """Stop arbitrage detection."""
        self._running = False
        if self._detection_task:
            self._detection_task.cancel()
            try:
                await self._detection_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Arbitrage detector stopped")
        
    async def _detect_opportunities(self):
        """Continuously detect arbitrage opportunities."""
        while self._running:
            try:
                # Get latest predictions
                gas_prediction = await self.model_manager.predict_gas_price()
                liquidity_prediction = await self.model_manager.predict_liquidity()
                
                # Find opportunities across DEXs
                opportunities = await self._find_opportunities(
                    gas_prediction,
                    liquidity_prediction
                )
                
                # Evaluate and filter opportunities
                viable_opportunities = [
                    opp for opp in opportunities
                    if self._is_viable_opportunity(opp)
                ]
                
                # Sort by expected profit
                viable_opportunities.sort(
                    key=lambda x: x.expected_profit,
                    reverse=True
                )
                
                # Update tracking
                self.opportunities = viable_opportunities
                self.performance_stats['opportunities_found'] += len(viable_opportunities)
                
                # Log opportunities
                if viable_opportunities:
                    self.logger.info(
                        f"Found {len(viable_opportunities)} opportunities. "
                        f"Best profit: {viable_opportunities[0].expected_profit:.4f}"
                    )
                    
                # Emit opportunities for execution
                for opp in viable_opportunities:
                    await self._emit_opportunity(opp)
                    
                # Brief pause before next detection
                await asyncio.sleep(0.1)  # Fast detection cycle
                
            except Exception as e:
                self.logger.error(f"Error in opportunity detection: {e}")
                await asyncio.sleep(1)
                
    async def _find_opportunities(
        self,
        gas_prediction: Dict[str, Any],
        liquidity_prediction: Dict[str, Any]
    ) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities using ML predictions.
        
        Args:
            gas_prediction: Gas price prediction with metadata
            liquidity_prediction: Liquidity prediction with metadata
            
        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        
        try:
            # Get current state from DEX manager
            pools = await self.dex_manager.get_active_pools()
            
            # Calculate optimal paths
            paths = await self._find_profitable_paths(pools)
            
            for path in paths:
                try:
                    # Calculate expected profit
                    profit, metadata = await self._calculate_profit(
                        path,
                        gas_prediction,
                        liquidity_prediction
                    )
                    
                    if profit > self.config['min_profit_threshold']:
                        # Calculate position size
                        position_size = self._calculate_position_size(
                            profit,
                            gas_prediction['uncertainty'],
                            liquidity_prediction['uncertainty']
                        )
                        
                        # Calculate risk score
                        risk_score = self._calculate_risk_score(
                            gas_prediction,
                            liquidity_prediction,
                            position_size,
                            metadata
                        )
                        
                        # Create opportunity
                        opportunity = ArbitrageOpportunity(
                            path=path,
                            expected_profit=profit,
                            confidence=min(
                                gas_prediction['confidence'],
                                liquidity_prediction['confidence']
                            ),
                            gas_cost=gas_prediction['predicted_price'],
                            execution_time=metadata.get('estimated_execution_time', 1.0),
                            position_size=position_size,
                            risk_score=risk_score,
                            timestamp=datetime.utcnow(),
                            metadata=metadata
                        )
                        
                        opportunities.append(opportunity)
                        
                except Exception as e:
                    self.logger.error(f"Error evaluating path {path}: {e}")
                    continue
                    
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error finding opportunities: {e}")
            return []
            
    async def _find_profitable_paths(
        self,
        pools: List[Dict[str, Any]]
    ) -> List[List[str]]:
        """Find potentially profitable trading paths."""
        paths = []
        
        try:
            # Get token prices
            prices = await self.dex_manager.get_token_prices()
            
            # Find price discrepancies
            for i, pool1 in enumerate(pools):
                for pool2 in pools[i+1:]:
                    if pool1['token0'] == pool2['token0'] and pool1['token1'] == pool2['token1']:
                        # Direct arbitrage between pools
                        price_diff = abs(pool1['price'] - pool2['price'])
                        if price_diff > self.config['min_price_difference']:
                            paths.append([
                                pool1['address'],
                                pool2['address']
                            ])
                            
                    elif pool1['token0'] in [pool2['token0'], pool2['token1']]:
                        # Triangular arbitrage
                        paths.append(self._build_triangular_path(
                            pool1, pool2, pools, prices
                        ))
                        
            return [path for path in paths if path is not None]
            
        except Exception as e:
            self.logger.error(f"Error finding profitable paths: {e}")
            return []
            
    def _calculate_position_size(
        self,
        profit: float,
        gas_uncertainty: float,
        liquidity_uncertainty: float
    ) -> float:
        """
        Calculate optimal position size based on uncertainties.
        
        Uses Kelly Criterion with uncertainty adjustments.
        """
        try:
            # Base Kelly fraction
            win_prob = 1 - (gas_uncertainty + liquidity_uncertainty) / 2
            loss_prob = 1 - win_prob
            
            if loss_prob == 0:
                kelly_fraction = 1.0
            else:
                kelly_fraction = (win_prob - loss_prob) / win_prob
                
            # Adjust for risk tolerance
            adjusted_fraction = kelly_fraction * self.config['risk_tolerance']
            
            # Calculate position size
            position_size = min(
                self.config['max_position_size'] * adjusted_fraction,
                self.config['max_position_size']
            )
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
            
    def _calculate_risk_score(
        self,
        gas_prediction: Dict[str, Any],
        liquidity_prediction: Dict[str, Any],
        position_size: float,
        metadata: Dict[str, Any]
    ) -> float:
        """
        Calculate risk score for opportunity.
        
        Lower score = higher risk
        """
        try:
            # Weight factors
            weights = {
                'gas_uncertainty': 0.2,
                'liquidity_uncertainty': 0.3,
                'position_size': 0.2,
                'execution_time': 0.15,
                'path_complexity': 0.15
            }
            
            # Calculate components
            gas_risk = 1 - gas_prediction['uncertainty']
            liquidity_risk = 1 - liquidity_prediction['uncertainty']
            size_risk = 1 - (position_size / self.config['max_position_size'])
            time_risk = 1 - (metadata.get('estimated_execution_time', 1.0) / 5.0)  # Assume 5s is worst
            path_risk = 1 - (len(metadata.get('path', [])) / 5.0)  # Assume 5 hops is worst
            
            # Combine components
            risk_score = sum([
                weights['gas_uncertainty'] * gas_risk,
                weights['liquidity_uncertainty'] * liquidity_risk,
                weights['position_size'] * size_risk,
                weights['execution_time'] * time_risk,
                weights['path_complexity'] * path_risk
            ])
            
            return max(0.0, min(1.0, risk_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating risk score: {e}")
            return 0.0
            
    def _is_viable_opportunity(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Check if opportunity meets viability criteria.
        
        Aggressive approach: Accept higher risk for higher returns
        """
        try:
            # Must meet minimum profit
            if opportunity.expected_profit < self.config['min_profit_threshold']:
                return False
                
            # Check execution time
            if opportunity.execution_time > self.config['max_execution_time']:
                return False
                
            # Check risk score
            if opportunity.risk_score < self.config['min_risk_score']:
                return False
                
            # Check active trades
            if self._has_conflicting_trade(opportunity):
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking opportunity viability: {e}")
            return False
            
    async def _emit_opportunity(self, opportunity: ArbitrageOpportunity):
        """Emit opportunity for execution."""
        try:
            # Add to active trades
            trade_id = f"{opportunity.timestamp.isoformat()}-{len(opportunity.path)}"
            self.active_trades[trade_id] = {
                'opportunity': opportunity,
                'status': 'pending',
                'timestamp': datetime.utcnow()
            }
            
            # Emit event
            await self.dex_manager.execute_arbitrage(
                opportunity.path,
                opportunity.position_size,
                opportunity.metadata
            )
            
            # Update stats
            self.performance_stats['trades_executed'] += 1
            
        except Exception as e:
            self.logger.error(f"Error emitting opportunity: {e}")
            
    def _has_conflicting_trade(self, opportunity: ArbitrageOpportunity) -> bool:
        """Check for conflicting active trades."""
        try:
            # Check each active trade
            for trade in self.active_trades.values():
                active_opp = trade['opportunity']
                
                # Check for path overlap
                if any(token in active_opp.path for token in opportunity.path):
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking conflicting trades: {e}")
            return True  # Safer to assume conflict
            
    def get_status(self) -> Dict[str, Any]:
        """
        Get detector status.
        
        Returns:
            Dictionary containing:
                - Current opportunities
                - Active trades
                - Performance stats
                - Risk metrics
        """
        return {
            'opportunities': len(self.opportunities),
            'active_trades': len(self.active_trades),
            'performance': self.performance_stats,
            'risk_metrics': self.risk_manager.get_metrics()
        }