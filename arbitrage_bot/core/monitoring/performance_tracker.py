"""Performance tracking and monitoring utilities."""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from ...utils.database import Database

logger = logging.getLogger(__name__)


def create_performance_tracker(db: Optional[Database] = None) -> "PerformanceTracker":
    """
    Create performance tracker instance.

    Args:
        db (Database, optional): Database instance

    Returns:
        PerformanceTracker: Performance tracker instance
    """
    return PerformanceTracker(db)


class PerformanceTracker:
    """Tracks and analyzes trading performance."""

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize performance tracker.

        Args:
            db (Database, optional): Database instance. Creates new one if not provided.
        """
        self.db = db if db else Database()
        self.start_time = time.time()
        logger.info("Performance tracker initialized")

    async def track_trade(self, trade_data: Dict[str, Any]) -> bool:
        """
        Track completed trade.

        Args:
            trade_data (Dict[str, Any]): Trade data to track

        Returns:
            bool: True if tracking successful
        """
        try:
            # Add timestamp
            trade_data["timestamp"] = datetime.utcnow()

            # Save to database
            await self.db.save_trade(trade_data)
            logger.debug("Trade tracked: %s", trade_data)
            return True

        except Exception as e:
            logger.error("Error tracking trade: %s", e)
            return False

    async def get_trade_metrics(self, token: str) -> Dict[str, Any]:
        """
        Get metrics for specific token.

        Args:
            token (str): Token symbol

        Returns:
            Dict[str, Any]: Token trading metrics
        """
        try:
            trades = await self.db.get_trades({"token": token})

            if not trades:
                return {
                    "token": token,
                    "total_trades": 0,
                    "success_rate": 0,
                    "total_profit": 0,
                    "average_profit": 0,
                }

            # Calculate metrics
            total_trades = len(trades)
            successful_trades = len([t for t in trades if t["status"] == "completed"])
            success_rate = successful_trades / total_trades if total_trades > 0 else 0

            profits = [t.get("profit", 0) for t in trades if t["status"] == "completed"]
            total_profit = sum(profits)
            average_profit = (
                total_profit / successful_trades if successful_trades > 0 else 0
            )

            return {
                "token": token,
                "total_trades": total_trades,
                "success_rate": success_rate,
                "total_profit": total_profit,
                "average_profit": average_profit,
            }

        except Exception as e:
            logger.error("Error getting trade metrics: %s", e)
            return {}

    async def get_token_performance(
        self, token: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get token performance history.

        Args:
            token (str): Token symbol
            days (int): Number of days of history

        Returns:
            List[Dict[str, Any]]: Daily performance data
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            trades = await self.db.get_trades(
                {"token": token, "timestamp": {"$gte": start_date}}
            )

            # Group by day
            daily_data = {}
            for trade in trades:
                day = trade["timestamp"].date()
                if day not in daily_data:
                    daily_data[day] = {"date": day, "trades": 0, "profit": 0}
                daily_data[day]["trades"] += 1
                if trade["status"] == "completed":
                    daily_data[day]["profit"] += trade.get("profit", 0)

            return list(daily_data.values())

        except Exception as e:
            logger.error("Error getting token performance: %s", e)
            return []

    async def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get overall performance summary.

        Returns:
            Dict[str, Any]: Performance summary
        """
        try:
            trades = await self.db.get_trades({})

            if not trades:
                return {
                    "total_trades": 0,
                    "success_rate": 0,
                    "total_profit": 0,
                    "average_profit": 0,
                    "uptime": time.time() - self.start_time,
                }

            total_trades = len(trades)
            successful_trades = len([t for t in trades if t["status"] == "completed"])
            success_rate = successful_trades / total_trades if total_trades > 0 else 0

            profits = [t.get("profit", 0) for t in trades if t["status"] == "completed"]
            total_profit = sum(profits)
            average_profit = (
                total_profit / successful_trades if successful_trades > 0 else 0
            )

            return {
                "total_trades": total_trades,
                "success_rate": success_rate,
                "total_profit": total_profit,
                "average_profit": average_profit,
                "uptime": time.time() - self.start_time,
            }

        except Exception as e:
            logger.error("Error getting performance summary: %s", e)
            return {}

    async def get_time_period_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get metrics for recent time period.

        Args:
            hours (int): Number of hours to analyze

        Returns:
            Dict[str, Any]: Time period metrics
        """
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            trades = await self.db.get_trades({"timestamp": {"$gte": start_time}})

            if not trades:
                return {
                    "period_hours": hours,
                    "trades": 0,
                    "profit": 0,
                    "success_rate": 0,
                }

            total_trades = len(trades)
            successful_trades = len([t for t in trades if t["status"] == "completed"])
            success_rate = successful_trades / total_trades if total_trades > 0 else 0

            profits = [t.get("profit", 0) for t in trades if t["status"] == "completed"]
            total_profit = sum(profits)

            return {
                "period_hours": hours,
                "trades": total_trades,
                "profit": total_profit,
                "success_rate": success_rate,
            }

        except Exception as e:
            logger.error("Error getting time period metrics: %s", e)
            return {}
