"""Balance and position management system."""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import numpy as np

from .web3.web3_manager import Web3Manager
from .analytics.analytics_system import AnalyticsSystem
from .ml.ml_system import MLSystem
from .monitoring.transaction_monitor import TransactionMonitor
from .dex.dex_manager import DEXManager
from .dex.utils import format_amount_with_decimals, COMMON_TOKENS

logger = logging.getLogger(__name__)

class BalanceManager:
    """Manages token balances and position sizing."""

    _instance = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(
        cls,
        web3_manager: Web3Manager,
        analytics: AnalyticsSystem,
        ml_system: MLSystem,
        monitor: TransactionMonitor,
        dex_manager: DEXManager,
        max_position_size: float = 0.1,
        min_reserve_ratio: float = 0.2,
        rebalance_threshold: float = 0.05,
        risk_per_trade: float = 0.02
    ) -> 'BalanceManager':
        """Get or create singleton instance."""
        async with cls._lock:
            if not cls._instance:
                logger.info("Creating new BalanceManager instance")
                cls._instance = cls(
                    web3_manager=web3_manager,
                    analytics=analytics,
                    ml_system=ml_system,
                    monitor=monitor,
                    dex_manager=dex_manager,
                    max_position_size=max_position_size,
                    min_reserve_ratio=min_reserve_ratio,
                    rebalance_threshold=rebalance_threshold,
                    risk_per_trade=risk_per_trade
                )
                await cls._instance.start()
            return cls._instance
            
    def __init__(
        self,
        web3_manager: Web3Manager,
        analytics: AnalyticsSystem,
        ml_system: MLSystem,
        monitor: TransactionMonitor,
        dex_manager: DEXManager,
        max_position_size: float = 0.1,  # 10% of total balance
        min_reserve_ratio: float = 0.2,  # 20% minimum reserve
        rebalance_threshold: float = 0.05,  # 5% deviation triggers rebalance
        risk_per_trade: float = 0.02  # 2% risk per trade
    ):
        """Initialize balance manager."""
        if not web3_manager:
            logger.error("web3_manager cannot be None")
            raise ValueError("web3_manager cannot be None")
            
        if not hasattr(web3_manager, 'get_token_contract'):
            logger.error("web3_manager missing get_token_contract method")
            raise ValueError("web3_manager missing get_token_contract method")
            
        if not hasattr(web3_manager, 'wallet_address'):
            logger.error("web3_manager missing wallet_address")
            raise ValueError("web3_manager missing wallet_address")
            
        logger.info(
            "Initializing BalanceManager with:\n"
            f"  web3_manager: {web3_manager}\n"
            f"  analytics: {analytics}\n"
            f"  ml_system: {ml_system}\n"
            f"  monitor: {monitor}\n"
            f"  dex_manager: {dex_manager}"
        )
        
        self.web3_manager = web3_manager
        self.analytics = analytics
        self.ml_system = ml_system
        self.monitor = monitor
        self.dex_manager = dex_manager
        self.max_position_size = max_position_size
        self.min_reserve_ratio = min_reserve_ratio
        self.rebalance_threshold = rebalance_threshold
        self.risk_per_trade = risk_per_trade
        
        # Balance tracking
        self.balances: Dict[str, int] = {}
        self.token_prices: Dict[str, float] = {}
        self.total_value_usd: float = 0.0
        
        # Position tracking
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.position_history: List[Dict[str, Any]] = []
        
        # Risk metrics
        self.drawdown_history: List[float] = []
        self.profit_factor: float = 0.0
        self.sharpe_ratio: float = 0.0
        
        # Performance thresholds
        self.max_drawdown = 0.1  # 10% maximum drawdown
        self.min_profit_factor = 1.5  # Minimum 1.5:1 profit:loss ratio
        self.min_sharpe = 1.0  # Minimum Sharpe ratio
        
        # State tracking
        self._initialized = False
        self._tasks = []
        
        logger.info("BalanceManager instance created successfully")

    async def start(self) -> None:
        """Start balance management."""
        try:
            if self._initialized:
                logger.warning("BalanceManager already initialized")
                return
                
            # Initialize balances
            await self._update_balances()
            
            # Start management tasks
            self._tasks = [
                asyncio.create_task(self._monitor_balances()),
                asyncio.create_task(self._rebalance_positions()),
                asyncio.create_task(self._update_risk_metrics()),
                asyncio.create_task(self._monitor_state())
            ]
            
            # Wait for initial balance update to complete
            await asyncio.sleep(1)
            
            # Verify initialization
            if not self.balances:
                raise ValueError("Failed to initialize balances")
                
            self._initialized = True
            logger.info("Balance manager started successfully")
            
        except Exception as e:
            logger.error(f"Error starting balance manager: {e}")
            await self.cleanup()
            raise
            
    async def _monitor_state(self) -> None:
        """Monitor BalanceManager state."""
        try:
            while True:
                if not self.web3_manager:
                    logger.error("web3_manager has become None")
                    await self.cleanup()
                    raise RuntimeError("web3_manager has become None")
                    
                if not hasattr(self.web3_manager, 'get_token_contract'):
                    logger.error("web3_manager lost get_token_contract method")
                    await self.cleanup()
                    raise RuntimeError("web3_manager lost get_token_contract method")
                    
                if not hasattr(self.web3_manager, 'wallet_address'):
                    logger.error("web3_manager lost wallet_address")
                    await self.cleanup()
                    raise RuntimeError("web3_manager lost wallet_address")
                    
                if not self._initialized:
                    logger.error("BalanceManager lost initialization state")
                    await self.cleanup()
                    raise RuntimeError("BalanceManager lost initialization state")
                    
                logger.debug(
                    "BalanceManager state:\n"
                    f"  Initialized: {self._initialized}\n"
                    f"  Active Tasks: {len(self._tasks)}\n"
                    f"  Balances Count: {len(self.balances)}\n"
                    f"  Total Value: ${self.total_value_usd:.2f}"
                )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except Exception as e:
            logger.error(f"Error in state monitoring: {e}")
            await self.cleanup()
            raise

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            if hasattr(self, '_tasks'):
                for task in self._tasks:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            logger.info("Balance manager cleanup complete")
        except Exception as e:
            logger.error(f"Error during balance manager cleanup: {e}")

    async def get_optimal_position_size(
        self,
        opportunity: Dict[str, Any]
    ) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Calculate optimal position size for opportunity.
        
        Args:
            opportunity: Trade opportunity details
            
        Returns:
            Tuple[int, Dict[str, Any]]: Position size and risk metrics
        """
        try:
            # Get ML predictions
            success_prob, importance = await self.ml_system.predict_trade_success(
                opportunity
            )
            predicted_profit, _ = await self.ml_system.predict_profit(opportunity)
            
            # Get market conditions
            market_conditions = await self.ml_system.analyze_market_conditions()
            
            # Calculate base position size
            token_in = opportunity['buy_path'][0]
            total_balance = self.balances.get(token_in, 0)
            base_size = int(total_balance * self.max_position_size)
            
            # Adjust for risk factors
            risk_score = self._calculate_risk_score(
                success_prob,
                predicted_profit,
                market_conditions
            )
            
            # Calculate final position size
            position_size = int(base_size * risk_score)
            
            # Ensure within limits
            position_size = min(
                position_size,
                int(total_balance * (1 - self.min_reserve_ratio))
            )
            
            # Calculate risk metrics
            risk_metrics = {
                'success_probability': success_prob,
                'predicted_profit': predicted_profit,
                'risk_score': risk_score,
                'market_volatility': market_conditions['volatility'].get(
                    opportunity['buy_dex'],
                    0
                ),
                'competition_level': market_conditions['competition']['rate']
            }
            
            return position_size, risk_metrics
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return None

    async def approve_trade(
        self,
        opportunity: Dict[str, Any],
        position_size: int
    ) -> bool:
        """
        Approve trade execution based on risk management rules.
        
        Args:
            opportunity: Trade opportunity details
            position_size: Proposed position size
            
        Returns:
            bool: True if trade is approved
        """
        try:
            # Check basic requirements
            if not self._check_basic_requirements(opportunity, position_size):
                return False
            
            # Check risk metrics
            if not await self._check_risk_metrics():
                return False
            
            # Check market conditions
            market_conditions = await self.ml_system.analyze_market_conditions()
            if not self._check_market_conditions(market_conditions):
                return False
            
            # Check competitor activity
            if not self._check_competitor_activity():
                return False
            
            # All checks passed
            return True
            
        except Exception as e:
            logger.error(f"Error approving trade: {e}")
            return False

    async def record_trade_result(
        self,
        trade_result: Dict[str, Any],
        opportunity: Dict[str, Any]
    ) -> None:
        """Record trade execution result."""
        try:
            # Update balances
            await self._update_balances()
            
            # Record position result
            position_result = {
                'timestamp': datetime.now().isoformat(),
                'trade_result': trade_result,
                'opportunity': opportunity,
                'profit_usd': trade_result['profit_usd'],
                'success': trade_result['success']
            }
            self.position_history.append(position_result)
            
            # Update metrics
            await self._update_risk_metrics()
            
            # Log result
            logger.info(
                f"Trade completed - Profit: ${trade_result['profit_usd']:.2f}, "
                f"Success: {trade_result['success']}"
            )
            
        except Exception as e:
            logger.error(f"Error recording trade result: {e}")

    async def _monitor_balances(self) -> None:
        """Monitor token balances."""
        try:
            while True:
                # Update balances
                await self._update_balances()
                
                # Check for significant changes
                total_value = sum(
                    balance * self.token_prices.get(token, 0)
                    for token, balance in self.balances.items()
                )
                
                if abs(total_value - self.total_value_usd) / self.total_value_usd > 0.05:
                    logger.warning(
                        f"Significant balance change detected: "
                        f"${self.total_value_usd:.2f} -> ${total_value:.2f}"
                    )
                
                self.total_value_usd = total_value
                await asyncio.sleep(60)  # Check every minute
                
        except Exception as e:
            logger.error(f"Error monitoring balances: {e}")

    async def _rebalance_positions(self) -> None:
        """Rebalance token positions."""
        try:
            while True:
                # Get target allocation
                target = await self._calculate_target_allocation()
                
                # Check current allocation
                current = {
                    token: (balance * self.token_prices.get(token, 0)) / self.total_value_usd
                    for token, balance in self.balances.items()
                }
                
                # Find tokens needing rebalance
                for token, target_weight in target.items():
                    current_weight = current.get(token, 0)
                    if abs(current_weight - target_weight) > self.rebalance_threshold:
                        await self._rebalance_token(
                            token,
                            current_weight,
                            target_weight
                        )
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
        except Exception as e:
            logger.error(f"Error rebalancing positions: {e}")

    async def _update_risk_metrics(self) -> None:
        """Update risk management metrics."""
        try:
            while True:
                if self.position_history:
                    # Calculate drawdown
                    equity_curve = [
                        pos['profit_usd']
                        for pos in self.position_history
                    ]
                    peak = max(equity_curve)
                    drawdown = (peak - equity_curve[-1]) / peak
                    self.drawdown_history.append(drawdown)
                    
                    # Calculate profit factor
                    profits = sum(
                        pos['profit_usd']
                        for pos in self.position_history
                        if pos['profit_usd'] > 0
                    )
                    losses = abs(sum(
                        pos['profit_usd']
                        for pos in self.position_history
                        if pos['profit_usd'] < 0
                    ))
                    self.profit_factor = profits / losses if losses > 0 else float('inf')
                    
                    # Calculate Sharpe ratio
                    returns = [
                        pos['profit_usd'] / self.total_value_usd
                        for pos in self.position_history
                    ]
                    if len(returns) > 1:
                        avg_return = np.mean(returns)
                        std_return = np.std(returns)
                        self.sharpe_ratio = (
                            (avg_return - 0.02/365) / std_return  # Assuming 2% risk-free rate
                            if std_return > 0 else 0
                        )
                
                await asyncio.sleep(60)  # Update every minute
                
        except Exception as e:
            logger.error(f"Error updating risk metrics: {e}")

    async def _update_balances(self) -> None:
        """Update token balances."""
        try:
            for token in COMMON_TOKENS.values():
                contract = self.web3_manager.get_token_contract(token)
                if contract:
                    balance = await contract.functions.balanceOf(
                        self.web3_manager.wallet_address
                    ).call()
                    self.balances[token] = balance
                    
                    # Get token price (simplified - replace with actual price feed)
                    self.token_prices[token] = 1.0  # TODO: Implement price feed
            
        except Exception as e:
            logger.error(f"Error updating balances: {e}")

    def _calculate_risk_score(
        self,
        success_prob: float,
        predicted_profit: float,
        market_conditions: Dict[str, Any]
    ) -> float:
        """Calculate risk score for position sizing."""
        try:
            # Base score on success probability
            base_score = success_prob
            
            # Adjust for predicted profit
            profit_score = min(predicted_profit / (self.total_value_usd * 0.01), 1.0)
            
            # Adjust for market conditions
            volatility_penalty = sum(
                vol for vol in market_conditions['volatility'].values()
            ) / len(market_conditions['volatility'])
            
            competition_penalty = market_conditions['competition']['rate']
            
            # Calculate final score
            risk_score = (
                base_score * 0.4 +  # 40% weight on success probability
                profit_score * 0.3 +  # 30% weight on profit potential
                (1 - volatility_penalty) * 0.15 +  # 15% weight on volatility
                (1 - competition_penalty) * 0.15  # 15% weight on competition
            )
            
            return max(0.1, min(1.0, risk_score))  # Ensure between 0.1 and 1.0
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 0.1

    def _check_basic_requirements(
        self,
        opportunity: Dict[str, Any],
        position_size: int
    ) -> bool:
        """Check basic trade requirements."""
        try:
            # Check sufficient balance
            token_in = opportunity['buy_path'][0]
            if position_size > self.balances.get(token_in, 0):
                return False
            
            # Check position size limits
            if position_size > self.total_value_usd * self.max_position_size:
                return False
            
            # Check reserve requirements
            remaining_balance = self.balances[token_in] - position_size
            if remaining_balance < self.balances[token_in] * self.min_reserve_ratio:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking requirements: {e}")
            return False

    async def _check_risk_metrics(self) -> bool:
        """Check risk management metrics."""
        try:
            # Check drawdown
            if self.drawdown_history and max(self.drawdown_history) > self.max_drawdown:
                return False
            
            # Check profit factor
            if self.profit_factor < self.min_profit_factor:
                return False
            
            # Check Sharpe ratio
            if self.sharpe_ratio < self.min_sharpe:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking risk metrics: {e}")
            return False

    def _check_market_conditions(
        self,
        conditions: Dict[str, Any]
    ) -> bool:
        """Check market conditions."""
        try:
            # Check volatility
            avg_volatility = sum(
                conditions['volatility'].values()
            ) / len(conditions['volatility'])
            if avg_volatility > 0.1:  # 10% volatility threshold
                return False
            
            # Check competition
            if conditions['competition']['rate'] > 0.8:  # 80% competition threshold
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking market conditions: {e}")
            return False

    def _check_competitor_activity(self) -> bool:
        """Check competitor activity levels."""
        try:
            # Get recent competitor transactions
            recent_time = datetime.now() - timedelta(minutes=5)
            recent_competitor_txs = [
                tx for tx in self.monitor.recent_transactions
                if (
                    tx['transaction']['from'] in self.monitor.known_competitors and
                    tx['timestamp'] > recent_time
                )
            ]
            
            # Check activity level
            if len(recent_competitor_txs) > 10:  # More than 10 competitor trades in 5 min
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking competitor activity: {e}")
            return False

    async def _calculate_target_allocation(self) -> Dict[str, float]:
        """Calculate target token allocation."""
        try:
            # Get market analysis
            market_conditions = await self.ml_system.analyze_market_conditions()
            
            # Base allocation
            allocation = {
                COMMON_TOKENS['WETH']: 0.4,  # 40% WETH
                COMMON_TOKENS['USDC']: 0.4,  # 40% USDC
                COMMON_TOKENS['DAI']: 0.2   # 20% DAI
            }
            
            # Adjust based on market conditions
            if market_conditions['volatility'].get(COMMON_TOKENS['WETH'], 0) > 0.05:
                # Reduce ETH exposure in high volatility
                allocation[COMMON_TOKENS['WETH']] *= 0.8
                allocation[COMMON_TOKENS['USDC']] += (
                    allocation[COMMON_TOKENS['WETH']] * 0.2
                )
            
            return allocation
            
        except Exception as e:
            logger.error(f"Error calculating target allocation: {e}")
            return {
                COMMON_TOKENS['WETH']: 0.33,
                COMMON_TOKENS['USDC']: 0.33,
                COMMON_TOKENS['DAI']: 0.34
            }

    async def check_pair_balance(self, token0: str, token1: str) -> bool:
        """Check if we have sufficient balance for a token pair."""
        try:
            if not self.web3_manager:
                logger.error("Web3 manager not initialized")
                return False
                
            if not hasattr(self.web3_manager, 'get_token_contract'):
                logger.error("Web3 manager missing get_token_contract method")
                return False
                
            if not hasattr(self.web3_manager, 'wallet_address'):
                logger.error("Web3 manager missing wallet_address")
                return False
                
            # Get token contracts
            token0_contract = self.web3_manager.get_token_contract(token0)
            token1_contract = self.web3_manager.get_token_contract(token1)
            
            if not token0_contract or not token1_contract:
                logger.warning(f"Could not get contracts for {token0} or {token1}")
                return False
                
            # Get balances
            balance0 = await token0_contract.functions.balanceOf(
                self.web3_manager.wallet_address
            ).call()
            balance1 = await token1_contract.functions.balanceOf(
                self.web3_manager.wallet_address
            ).call()
            
            # Get token prices
            self.token_prices[token0] = 1.0  # TODO: Get real prices
            self.token_prices[token1] = 1.0
            
            # Calculate USD values
            value0 = balance0 * self.token_prices[token0]
            value1 = balance1 * self.token_prices[token1]
            
            # For monitoring mode, return True if we have any balance
            return value0 > 0 or value1 > 0
            
        except Exception as e:
            logger.error(f"Error checking pair balance: {e}")
            return False

    async def _rebalance_token(
        self,
        token: str,
        current_weight: float,
        target_weight: float
    ) -> None:
        """Rebalance single token position."""
        try:
            # Calculate required adjustment
            value_diff = (target_weight - current_weight) * self.total_value_usd
            
            if abs(value_diff) < 100:  # Skip small adjustments
                return
            
            # TODO: Implement rebalancing logic
            # This would involve:
            # 1. Finding best execution path
            # 2. Calculating optimal trade size
            # 3. Executing trades
            # For now, just log the requirement
            logger.info(
                f"Rebalance needed for {token}: "
                f"{current_weight:.2%} -> {target_weight:.2%} "
                f"(${value_diff:.2f})"
            )
            
        except Exception as e:
            logger.error(f"Error rebalancing token: {e}")
