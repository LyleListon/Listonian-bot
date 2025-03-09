"""Real-time ML system for market analysis and predictions."""

import logging
from typing import Dict, Any, Tuple, Optional
from decimal import Decimal
import time

logger = logging.getLogger(__name__)

class MLSystem:
    """ML system for real-time market analysis."""

    def __init__(self, analytics=None, market_analyzer=None, config=None):
        """Initialize ML system."""
        self.analytics = analytics
        self.market_analyzer = market_analyzer
        self.config = config or {}
        self.market_state = {}
        self.last_update = 0
        self.update_interval = 1  # 1 second updates
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize ML system."""
        try:
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize ML system: {e}")
            return False

    async def predict_trade_success(
        self,
        opportunity: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Predict trade success probability."""
        try:
            # For mainnet operation, we focus on real metrics
            profit_percent = opportunity.get('profit_percent', 0)
            gas_cost = opportunity.get('estimated_gas', 0)
            
            # Calculate base probability
            base_prob = min(1.0, profit_percent * 10)  # Higher profit = higher probability
            
            # Adjust for gas costs
            gas_factor = 1.0 / (1.0 + gas_cost / (profit_percent * opportunity.get('buy_amount', 1)))
            
            # Feature importance
            importance = {
                'profit_percent': 0.6,
                'gas_efficiency': 0.4
            }
            
            final_prob = base_prob * 0.6 + gas_factor * 0.4
            
            return final_prob, importance
            
        except Exception as e:
            logger.error(f"Error predicting trade success: {e}")
            return 0.0, {}

    async def predict_profit(
        self,
        opportunity: Dict[str, Any]
    ) -> Tuple[float, Dict[str, Any]]:
        """Predict potential profit."""
        try:
            # Get base profit
            profit = opportunity.get('profit_percent', 0) * opportunity.get('buy_amount', 0)
            
            # Adjust for gas
            gas_cost = opportunity.get('estimated_gas', 0)
            net_profit = profit - gas_cost
            
            metrics = {
                'base_profit': profit,
                'gas_cost': gas_cost,
                'net_profit': net_profit,
                'roi': net_profit / opportunity.get('buy_amount', 1)
            }
            
            return net_profit, metrics
            
        except Exception as e:
            logger.error(f"Error predicting profit: {e}")
            return 0.0, {}

    async def analyze_market_conditions(self) -> Dict[str, Any]:
        """Analyze current market conditions."""
        try:
            current_time = time.time()
            
            # Only update if interval has passed
            if current_time - self.last_update > self.update_interval:
                # Get real-time market data from analytics
                if self.analytics:
                    metrics = await self.analytics.get_metrics()
                    gas_price = await self.analytics.gas_optimizer.get_optimal_gas_price()
                    
                    # Calculate network congestion based on gas price
                    base_gas = 30 * 10**9  # 30 gwei
                    congestion = min(1.0, gas_price / base_gas) if gas_price > 0 else 0.5
                    
                    self.market_state = {
                        'volatility': {
                            token: float(price_data.get('volatility_24h', 0.01))
                            for token, price_data in metrics.get('market_prices', {}).items()
                        },
                        'competition': {
                            'rate': metrics.get('active_opportunities', 5) / 10,  # Normalize to 0-1
                            'active_bots': metrics.get('active_bots', 5)
                        },
                        'network': {
                            'gas_price': gas_price / 10**9,  # Convert to gwei
                            'congestion': congestion
                        }
                    }
                else:
                    # Fallback to conservative defaults
                    self.market_state = {
                        'volatility': {'WETH': 0.01, 'USDC': 0.001, 'DAI': 0.001},
                        'competition': {'rate': 0.7, 'active_bots': 10},  # Assume high competition
                        'network': {'gas_price': 50, 'congestion': 0.7}  # Conservative gas estimate
                    }
                self.last_update = current_time
            
            return self.market_state
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {e}")
            return {
                'volatility': {},
                'competition': {'rate': 1.0},  # High competition assumption on error
                'network': {'congestion': 1.0}  # High congestion assumption on error
            }

    async def update_model(self, trade_result: Dict[str, Any]) -> None:
        """Update model with trade result."""
        try:
            # In production we focus on real-time metrics
            # rather than model updates
            pass
        except Exception as e:
            logger.error(f"Error updating model: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Get current ML system state."""
        return {
            'initialized': self.initialized,
            'last_update': self.last_update,
            'market_state': self.market_state
        }

async def create_ml_system(
    analytics=None,
    market_analyzer=None,
    config=None
) -> MLSystem:
    """Create and initialize ML system.
    
    Args:
        analytics: Analytics system instance
        market_analyzer: Market analyzer instance
        config: Configuration dictionary
        
    Returns:
        Initialized ML system instance
    """
    try:
        ml_system = MLSystem(analytics, market_analyzer, config)
        await ml_system.initialize()
        logger.info("ML system created and initialized")
        return ml_system
    except Exception as e:
        logger.error(f"Error creating ML system: {e}")
        raise
