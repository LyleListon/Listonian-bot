"""Risk management system for arbitrage trading."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass

@dataclass
class RiskMetrics:
    """Current risk metrics."""
    volatility: float
    drawdown: float
    exposure: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    recovery_factor: float
    win_rate: float

class RiskManager:
    """Manage trading risk and position sizing."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize risk manager.
        
        Args:
            config: Configuration dictionary containing:
                - initial_capital: Starting capital
                - max_drawdown: Maximum allowed drawdown
                - max_exposure: Maximum total exposure
                - volatility_window: Window for volatility calculation
                - risk_free_rate: Risk-free rate for Sharpe ratio
                - recovery_threshold: Required recovery factor
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize tracking
        self.capital = config['initial_capital']
        self.peak_capital = self.capital
        self.current_exposure = 0.0
        
        # Track trades
        self.trades: List[Dict[str, Any]] = []
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.daily_returns: List[float] = []
        self.drawdowns: List[float] = []
        self.exposures: List[float] = []
        
        # Risk metrics
        self.metrics = RiskMetrics(
            volatility=0.0,
            drawdown=0.0,
            exposure=0.0,
            profit_factor=1.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            recovery_factor=1.0,
            win_rate=0.0
        )
        
    def calculate_position_size(
        self,
        profit_potential: float,
        uncertainty: float,
        current_volatility: float
    ) -> float:
        """
        Calculate optimal position size based on risk metrics.
        
        Args:
            profit_potential: Expected profit
            uncertainty: Prediction uncertainty
            current_volatility: Current market volatility
            
        Returns:
            Optimal position size
        """
        try:
            # Base position size using Kelly Criterion
            win_rate = self._calculate_win_rate()
            loss_rate = 1 - win_rate
            
            if loss_rate == 0:
                kelly_fraction = 1.0
            else:
                kelly_fraction = (win_rate * profit_potential - loss_rate) / profit_potential
                
            # Adjust for uncertainty
            uncertainty_factor = 1 - uncertainty
            
            # Adjust for volatility
            volatility_factor = 1 - (current_volatility / self.metrics.volatility)
            volatility_factor = max(0.1, min(1.0, volatility_factor))
            
            # Adjust for drawdown
            drawdown_factor = 1 - (self.metrics.drawdown / self.config['max_drawdown'])
            drawdown_factor = max(0.1, min(1.0, drawdown_factor))
            
            # Adjust for exposure
            exposure_factor = 1 - (self.metrics.exposure / self.config['max_exposure'])
            exposure_factor = max(0.1, min(1.0, exposure_factor))
            
            # Combine factors
            adjustment = np.mean([
                uncertainty_factor,
                volatility_factor,
                drawdown_factor,
                exposure_factor
            ])
            
            # Calculate final position size
            position_size = self.capital * kelly_fraction * adjustment
            
            # Apply limits
            max_position = self.capital * self.config['max_exposure']
            position_size = min(position_size, max_position)
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
            
    def update_metrics(self, current_price: float):
        """
        Update risk metrics with current market state.
        
        Args:
            current_price: Current market price
        """
        try:
            # Update capital and drawdown
            self.peak_capital = max(self.peak_capital, self.capital)
            current_drawdown = (self.peak_capital - self.capital) / self.peak_capital
            self.drawdowns.append(current_drawdown)
            
            # Update exposure
            self.exposures.append(self.current_exposure / self.capital)
            
            # Calculate daily return
            if len(self.daily_returns) > 0:
                daily_return = (current_price / self.daily_returns[-1]) - 1
                self.daily_returns.append(daily_return)
            else:
                self.daily_returns.append(0.0)
                
            # Update metrics
            self.metrics.volatility = np.std(
                self.daily_returns[-self.config['volatility_window']:]
            )
            self.metrics.drawdown = current_drawdown
            self.metrics.exposure = self.current_exposure / self.capital
            self.metrics.max_drawdown = max(self.drawdowns)
            
            # Calculate profit factor
            profits = sum(t['profit'] for t in self.trades if t['profit'] > 0)
            losses = abs(sum(t['profit'] for t in self.trades if t['profit'] < 0))
            self.metrics.profit_factor = profits / losses if losses > 0 else float('inf')
            
            # Calculate Sharpe ratio
            returns = np.array(self.daily_returns[-252:])  # Last year
            excess_returns = returns - self.config['risk_free_rate'] / 252
            self.metrics.sharpe_ratio = (
                np.mean(excess_returns) / np.std(excess_returns)
                if len(returns) > 0 else 0.0
            ) * np.sqrt(252)
            
            # Calculate recovery factor
            if self.metrics.max_drawdown > 0:
                total_return = (self.capital / self.config['initial_capital']) - 1
                self.metrics.recovery_factor = total_return / self.metrics.max_drawdown
            else:
                self.metrics.recovery_factor = float('inf')
                
            # Calculate win rate
            wins = sum(1 for t in self.trades if t['profit'] > 0)
            self.metrics.win_rate = wins / len(self.trades) if self.trades else 0.0
            
        except Exception as e:
            self.logger.error(f"Error updating metrics: {e}")
            
    def check_risk_limits(self) -> Tuple[bool, Optional[str]]:
        """
        Check if current risk metrics are within limits.
        
        Returns:
            Tuple of (within_limits, reason)
        """
        try:
            # Check drawdown
            if self.metrics.drawdown > self.config['max_drawdown']:
                return False, f"Drawdown ({self.metrics.drawdown:.2%}) exceeds limit"
                
            # Check exposure
            if self.metrics.exposure > self.config['max_exposure']:
                return False, f"Exposure ({self.metrics.exposure:.2%}) exceeds limit"
                
            # Check recovery factor
            if self.metrics.recovery_factor < self.config['recovery_threshold']:
                return False, f"Recovery factor ({self.metrics.recovery_factor:.2f}) below threshold"
                
            # Check profit factor
            if self.metrics.profit_factor < 1.0:
                return False, f"Profit factor ({self.metrics.profit_factor:.2f}) below 1.0"
                
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error checking risk limits: {e}")
            return False, str(e)
            
    def record_trade(
        self,
        trade_id: str,
        position_size: float,
        entry_price: float,
        profit: float
    ):
        """
        Record completed trade.
        
        Args:
            trade_id: Unique trade identifier
            position_size: Size of position
            entry_price: Entry price
            profit: Realized profit/loss
        """
        try:
            # Update capital
            self.capital += profit
            
            # Record trade
            self.trades.append({
                'trade_id': trade_id,
                'position_size': position_size,
                'entry_price': entry_price,
                'profit': profit,
                'timestamp': datetime.utcnow()
            })
            
            # Update exposure
            if trade_id in self.active_positions:
                self.current_exposure -= position_size
                del self.active_positions[trade_id]
                
            # Update metrics
            self.update_metrics(entry_price)
            
        except Exception as e:
            self.logger.error(f"Error recording trade: {e}")
            
    def open_position(
        self,
        trade_id: str,
        position_size: float,
        entry_price: float
    ):
        """
        Record new position.
        
        Args:
            trade_id: Unique trade identifier
            position_size: Size of position
            entry_price: Entry price
        """
        try:
            # Record position
            self.active_positions[trade_id] = {
                'position_size': position_size,
                'entry_price': entry_price,
                'timestamp': datetime.utcnow()
            }
            
            # Update exposure
            self.current_exposure += position_size
            
            # Update metrics
            self.update_metrics(entry_price)
            
        except Exception as e:
            self.logger.error(f"Error opening position: {e}")
            
    def get_metrics(self) -> Dict[str, float]:
        """
        Get current risk metrics.
        
        Returns:
            Dictionary of risk metrics
        """
        return {
            'volatility': self.metrics.volatility,
            'drawdown': self.metrics.drawdown,
            'exposure': self.metrics.exposure,
            'profit_factor': self.metrics.profit_factor,
            'sharpe_ratio': self.metrics.sharpe_ratio,
            'max_drawdown': self.metrics.max_drawdown,
            'recovery_factor': self.metrics.recovery_factor,
            'win_rate': self.metrics.win_rate,
            'capital': self.capital,
            'peak_capital': self.peak_capital,
            'active_positions': len(self.active_positions)
        }
        
    def _calculate_win_rate(self) -> float:
        """Calculate recent win rate."""
        try:
            recent_trades = self.trades[-100:]  # Last 100 trades
            if not recent_trades:
                return 0.5  # Default to 50% if no trades
                
            wins = sum(1 for t in recent_trades if t['profit'] > 0)
            return wins / len(recent_trades)
            
        except Exception as e:
            self.logger.error(f"Error calculating win rate: {e}")
            return 0.5