"""Balance and position management system."""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import numpy as np

from .web3.web3_manager import Web3Manager
from .analytics.analytics_system import AnalyticsSystem
from .ml.ml_system import MLSystem
from .monitoring.transaction_monitor import TransactionMonitor
from .dex import DexManager
from .dex.utils import format_amount_with_decimals, COMMON_TOKENS
from .market_analyzer import MarketAnalyzer
from .gas.gas_optimizer import GasOptimizer

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
        dex_manager: DexManager,
        market_analyzer: MarketAnalyzer,
        gas_optimizer: GasOptimizer,
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
                    market_analyzer=market_analyzer,
                    gas_optimizer=gas_optimizer,
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
        dex_manager: DexManager,
        market_analyzer: MarketAnalyzer,
        gas_optimizer: GasOptimizer,
        max_position_size: float = 0.1,  # 10% of total balance
        min_reserve_ratio: float = 0.2,  # 20% minimum reserve
        rebalance_threshold: float = 0.05,  # 5% deviation triggers rebalance
        risk_per_trade: float = 0.02  # 2% risk per trade
    ):
        """Initialize balance manager."""
        self.web3_manager = web3_manager
        self.analytics = analytics
        self.ml_system = ml_system
        self.monitor = monitor
        self.dex_manager = dex_manager
        self.market_analyzer = market_analyzer
        self.gas_optimizer = gas_optimizer
        self.max_position_size = max_position_size
        self.min_reserve_ratio = min_reserve_ratio
        self.rebalance_threshold = rebalance_threshold
        self.risk_per_trade = risk_per_trade
        
        # Balance tracking
        self.balances: Dict[str, int] = {}
        self.token_prices: Dict[str, float] = {}
        self.total_value_usd: float = 0.0
        
        logger.info("BalanceManager instance created successfully")

    async def start(self) -> None:
        """Start balance manager operations."""
        try:
            # Update initial balances
            await self._update_balances()

            # Calculate total portfolio value
            total_value = 0.0
            for token, balance in self.balances.items():
                price = self.token_prices.get(token)
                if price and balance > 0:
                    # Convert balance to float considering token decimals
                    decimals = self.web3_manager.get_token_decimals(token)
                    balance_float = float(balance) / (10 ** decimals)
                    # Calculate value in USD
                    value = balance_float * price
                    total_value += value

            self.total_value_usd = total_value
            logger.info(f"Total portfolio value: ${total_value:.2f}")

            # Start periodic balance updates
            asyncio.create_task(self._periodic_updates())

        except Exception as e:
            logger.error(f"Error starting balance manager: {e}")
            raise

    async def _periodic_updates(self) -> None:
        """Periodically update balances and portfolio value."""
        while True:
            try:
                await self._update_balances()
                await asyncio.sleep(60)  # Update every minute
            except Exception as e:
                logger.error(f"Error in periodic updates: {e}")
                await asyncio.sleep(5)  # Brief delay on error

    def check_balance(self, token: str, amount: float) -> bool:
        """Check if we have enough balance for a trade."""
        try:
            # Get current balance
            balance = self.balances.get(token, 0)
            if balance == 0:
                # Try to get balance directly if not in cache
                contract = self.web3_manager.get_token_contract(token)
                if contract:
                    balance = contract.functions.balanceOf(
                        self.web3_manager.wallet_address
                    ).call()
                    self.balances[token] = balance

            # Convert amount to token decimals
            token_decimals = self.web3_manager.get_token_decimals(token)
            amount_in_decimals = int(amount * (10 ** token_decimals))

            # Check if we have enough balance
            return balance >= amount_in_decimals

        except Exception as e:
            logger.error(f"Error checking balance for {token}: {e}")
            return False

    def check_position_size(self, token: str, amount: float) -> bool:
        """Check if trade size is within position limits."""
        try:
            # Get token price
            token_price = self.token_prices.get(token)
            if not token_price:
                token_price = self.market_analyzer.get_current_price(token)
                if token_price <= 0:
                    logger.error(f"Could not get price for {token}")
                    return False
                self.token_prices[token] = token_price

            # Calculate trade value in USD
            trade_value_usd = amount * token_price

            # Calculate maximum allowed position size
            max_position_usd = self.total_value_usd * self.max_position_size

            # Check if trade size is within limits
            return trade_value_usd <= max_position_usd

        except Exception as e:
            logger.error(f"Error checking position size for {token}: {e}")
            return False

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

                    # Get token price from market analyzer
                    price = self.market_analyzer.get_current_price(token)
                    if price > 0:
                        self.token_prices[token] = price
            
        except Exception as e:
            logger.error(f"Error updating balances: {e}")

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
            
            # Get token price
            token_price = self.token_prices.get(token)
            if not token_price:
                logger.error(f"No price available for {token}")
                return

            # Calculate amount to trade
            amount_to_trade = abs(value_diff) / token_price

            # Find best execution path
            if value_diff > 0:  # Need to buy token
                path = ['WETH', token]
                amount_in = amount_to_trade * token_price  # Amount in ETH
            else:  # Need to sell token
                path = [token, 'WETH']
                amount_in = amount_to_trade

            # Get best DEX for execution
            best_dex = None
            best_output = 0
            for dex in self.dex_manager.get_all_dexes():
                try:
                    quote = dex.get_quote_with_impact(
                        amount_in=int(amount_in),
                        path=path
                    )
                    if quote['amount_out'] > best_output:
                        best_dex = dex
                        best_output = quote['amount_out']
                except Exception as e:
                    logger.debug(f"Error getting quote from {dex.name}: {e}")
                    continue

            if not best_dex:
                logger.error("No viable DEX found for rebalancing")
                return

            # Get optimized gas parameters
            gas_params = self.gas_optimizer.optimize_gas({
                'priority': 'standard',
                'dex': best_dex.name
            })

            # Execute trade
            try:
                tx = await best_dex.swap_exact_tokens_for_tokens(
                    amount_in=int(amount_in),
                    min_amount_out=int(best_output * 0.995),  # 0.5% slippage
                    path=path,
                    to=self.web3_manager.wallet_address,
                    deadline=int(time.time() + 300),  # 5 minutes
                    gas_params={
                        'gas': gas_params['gas'],
                        'maxFeePerGas': gas_params['maxFeePerGas'],
                        'maxPriorityFeePerGas': gas_params['maxPriorityFeePerGas']
                    }
                )
                logger.info(
                    f"Rebalancing trade executed on {best_dex.name}\n"
                    f"Direction: {'Buy' if value_diff > 0 else 'Sell'} {token}\n"
                    f"Amount: {amount_to_trade:.4f}\n"
                    f"TX Hash: {tx.hex()}"
                )
            except Exception as e:
                logger.error(f"Failed to execute rebalancing trade: {e}")
            
        except Exception as e:
            logger.error(f"Error rebalancing token: {e}")
