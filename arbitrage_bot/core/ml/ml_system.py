"""Real-time ML system for market analysis and predictions."""

import logging
from typing import Dict, Any, Tuple, Optional, List, Union
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
        self.memory_bank = None

    async def initialize(self) -> bool:
        """Initialize ML system."""
        try:
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize ML system: {e}")
            return False

    async def score_opportunities(self, opportunities: List[Any]) -> List[float]:
        """
        Score arbitrage opportunities using ML predictions.

        Args:
            opportunities: List of ArbitrageOpportunity instances

        Returns:
            List of scores between 0 and 1
        """
        try:
            # Get current market conditions
            market_state = await self.analyze_market_conditions()
            
            scores = []
            for opp in opportunities:
                try:
                    # Convert opportunity to dict format
                    opp_dict = {
                        'token_address': opp.token_address,
                        'buy_dex': opp.buy_dex,
                        'sell_dex': opp.sell_dex,
                        'profit_percent': float(opp.profit_margin),
                        'buy_price': float(opp.buy_price),
                        'sell_price': float(opp.sell_price)
                    }

                    # Get predictions
                    success_prob, _ = await self.predict_trade_success(opp_dict)
                    profit_amount, metrics = await self.predict_profit(opp_dict)

                    # Combine predictions into final score
                    score = success_prob * min(1.0, profit_amount / market_state['network']['gas_price'])
                    scores.append(score)
                except Exception as e:
                    logger.error(f"Error scoring opportunity: {e}")
                    scores.append(0.0)

            return scores
        except Exception as e:
            logger.error(f"Error scoring opportunities: {e}")
            return [0.0] * len(opportunities)

    async def predict_trade_success(self, opportunity: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """Predict trade success probability."""
        try:
            # For mainnet operation, we focus on real metrics
            market_state = await self.analyze_market_conditions()
            
            # Get token volatility
            token_volatility = market_state['volatility'].get(
                opportunity['token_address'],
                0.01  # Default volatility
            )
            
            # Get historical success rate if available
            historical_success = 0.5  # Default
            if self.memory_bank:
                history = await self.memory_bank.get_token_history(opportunity['token_address'])
                if history and history.get('total_trades', 0) > 0:
                    historical_success = history.get('success_rate', 0.5)
            
            # Calculate base probability
            profit_percent = opportunity.get('profit_percent', 0)
            base_prob = min(1.0, profit_percent * 10)
            
            # Adjust for market conditions
            congestion_factor = 1.0 - market_state['network']['congestion'] * 0.5
            competition_factor = 1.0 - market_state['competition']['rate'] * 0.3
            volatility_factor = 1.0 - token_volatility * 2
            
            # Feature importance
            importance = {
                'profit_percent': 0.4,
                'historical_success': 0.2,
                'network_congestion': 0.15,
                'competition': 0.15,
                'volatility': 0.1
            }
            
            # Calculate weighted probability
            final_prob = (
                base_prob * importance['profit_percent'] +
                historical_success * importance['historical_success'] +
                congestion_factor * importance['network_congestion'] +
                competition_factor * importance['competition'] +
                volatility_factor * importance['volatility']
            )
            
            final_prob = max(0.0, min(1.0, final_prob))
            return final_prob, importance
            
        except Exception as e:
            logger.error(f"Error predicting trade success: {e}")
            return 0.0, {}

    async def predict_profit(self, opportunity: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Predict potential profit."""
        try:
            market_state = await self.analyze_market_conditions()
            
            # Get base profit
            buy_amount = opportunity.get('buy_amount', 0)
            if not buy_amount:
                buy_amount = float(opportunity.get('buy_price', 0))
            
            profit = opportunity.get('profit_percent', 0) * buy_amount
            
            # Estimate gas cost
            gas_price = market_state['network']['gas_price'] * 10**9  # Convert to wei
            estimated_gas = 300000  # Base gas estimate
            gas_cost = gas_price * estimated_gas
            
            # Calculate net profit
            net_profit = profit - gas_cost
            
            # Get historical metrics if available
            historical_metrics = {}
            if self.memory_bank:
                history = await self.memory_bank.get_token_history(opportunity['token_address'])
                if history:
                    historical_metrics = history.get('profit_metrics', {})
            
            metrics = {
                'base_profit': profit,
                'gas_cost': gas_cost,
                'net_profit': net_profit,
                'roi': net_profit / buy_amount if buy_amount else 0,
                'historical': historical_metrics
            }
            
            return float(net_profit), metrics
            
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

    async def update_model(
        self,
        trade_result: Dict[str, Any],
        opportunity: Optional[Any] = None
    ) -> None:
        """Update model with trade result."""
        try:
            if not self.memory_bank:
                return

            # Update token history
            if opportunity and hasattr(opportunity, 'token_address'):
                await self.memory_bank.update_token_history(
                    token_address=opportunity.token_address,
                    success=trade_result.get('success', False),
                    profit=trade_result.get('profit', 0),
                    gas_used=trade_result.get('gas_used', 0)
                )

            # Update market state
            self.market_state.update(trade_result.get('market_state', {}))
            self.last_update = time.time()

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
    config=None,
    memory_bank=None
) -> MLSystem:
    """
    Create and initialize ML system.
    
    Args:
        analytics: Analytics system instance
        market_analyzer: Market analyzer instance
        config: Configuration dictionary
        memory_bank: Memory bank instance
        
    Returns:
        Initialized ML system instance
    """
    try:
        ml_system = MLSystem(analytics, market_analyzer, config)
        ml_system.memory_bank = memory_bank
        await ml_system.initialize()
        logger.info("ML system created and initialized")
        return ml_system
    except Exception as e:
        logger.error(f"Error creating ML system: {e}")
        raise
