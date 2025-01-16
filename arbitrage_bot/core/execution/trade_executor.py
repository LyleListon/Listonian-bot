"""Trade execution module."""

import os
import logging
import asyncio
from typing import Dict, Any, Optional
from ...utils.database import Database
from ...utils.market_analyzer import MarketAnalyzer
from ..web3.web3_manager import Web3Manager, create_web3_manager

logger = logging.getLogger(__name__)


class TradeExecutor:
    """Handles trade execution and monitoring."""

    def __init__(self, testing: bool = None):
        """
        Initialize trade executor.

        Args:
            testing (bool, optional): Whether to use mock providers for testing.
        """
        testing = testing if testing is not None else os.getenv('TESTING', '').lower() == 'true'
        self.db = Database(testing=testing)
        self.market_analyzer = MarketAnalyzer()
        self.web3 = create_web3_manager(testing=testing)
        self._trade_queue = asyncio.Queue()
        self._running = False
        logger.info("Trade executor initialized")

    async def execute_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a trade with the given parameters.

        Args:
            trade_data (Dict[str, Any]): Trade parameters including token, amount, and price

        Returns:
            Dict[str, Any]: Trade execution result
        """
        try:
            logger.info(f"Executing trade: {trade_data}")

            # Validate market conditions
            conditions = await self.market_analyzer.analyze_market_conditions(
                trade_data["token"]
            )
            if not self._validate_conditions(conditions):
                raise ValueError("Market conditions not suitable for trade")

            # Execute trade on blockchain
            tx_hash = await self.web3.execute_swap(
                token=trade_data["token"],
                amount=trade_data["amount"],
                price=trade_data["price"],
            )

            # Save trade to database
            trade_record = {
                **trade_data,
                "transaction_hash": tx_hash,
                "status": "completed",
            }
            self.db.save_trade(trade_record)

            # Add to notification queue
            await self._trade_queue.put(trade_record)

            logger.info(f"Trade executed successfully: {tx_hash}")
            return {"success": True, "transaction_hash": tx_hash}

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            # Save failed trade
            if "trade_record" in locals():
                trade_record["status"] = "failed"
                trade_record["error"] = str(e)
                self.db.save_trade(trade_record)

            return {"success": False, "error": str(e)}

    def _validate_conditions(self, conditions: Dict[str, Any]) -> bool:
        """
        Validate market conditions for trade.

        Args:
            conditions (Dict[str, Any]): Market conditions from analyzer

        Returns:
            bool: True if conditions are suitable
        """
        # Check success rate
        if conditions.get("success_rate", 0) < 0.8:
            logger.warning("Low success rate")
            return False

        # Check liquidity
        if conditions.get("liquidity", 0) < 0.5:
            logger.warning("Insufficient liquidity")
            return False

        # Check volatility
        if conditions.get("volatility", 0) > 0.1:
            logger.warning("High volatility")
            return False

        return True

    async def wait_for_trade(self) -> Dict[str, Any]:
        """
        Wait for next completed trade.

        Returns:
            Dict[str, Any]: Trade data
        """
        return await self._trade_queue.get()

    async def start_monitoring(self):
        """Start trade monitoring."""
        self._running = True
        logger.info("Trade monitoring started")

    async def stop_monitoring(self):
        """Stop trade monitoring."""
        self._running = False
        logger.info("Trade monitoring stopped")

    @property
    def is_running(self) -> bool:
        """Check if monitoring is running."""
        return self._running
