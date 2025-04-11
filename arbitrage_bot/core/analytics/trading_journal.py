"""
Trading Journal Module

Provides detailed trade logging and analysis for the arbitrage system.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
# from decimal import Decimal # Removed unused import
from datetime import datetime, timedelta
import json
import os
# from pathlib import Path # Removed unused import

logger = logging.getLogger(__name__)


class TradingJournal:
    """
    Manages detailed trade logging and analysis.

    Features:
    - Detailed trade logging
    - Trade categorization and tagging
    - Trade outcome analysis
    - Learning insights extraction
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the trading journal.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.initialized = False
        self.lock = asyncio.Lock()

        # Storage for trade data
        self._trades = []
        self._tags = set()
        self._categories = set()

        # Storage paths
        self.storage_dir = self.config.get("storage_dir", "analytics")
        self.journal_file = os.path.join(self.storage_dir, "trading_journal.json")

        # Analysis settings
        self.min_profit_threshold = float(self.config.get("min_profit_threshold", 0.0))
        self.success_threshold = float(self.config.get("success_threshold", 0.0))

    async def initialize(self) -> bool:
        """
        Initialize the trading journal.

        Returns:
            True if initialization successful
        """
        try:
            # Create storage directory if it doesn't exist
            os.makedirs(self.storage_dir, exist_ok=True)

            # Load historical data if available
            await self._load_journal_data()

            self.initialized = True
            logger.info("Trading journal initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize trading journal: {e}")
            return False

    async def _load_journal_data(self) -> None:
        """Load journal data from storage."""
        try:
            if os.path.exists(self.journal_file):
                async with self.lock:
                    with open(self.journal_file, "r") as f:
                        data = json.load(f)

                    # Process trades
                    if "trades" in data:
                        trades = data["trades"]
                        # Convert string timestamps to datetime objects
                        for trade in trades:
                            if "timestamp" in trade:
                                trade["timestamp"] = datetime.fromisoformat(
                                    trade["timestamp"]
                                )
                        self._trades = trades

                    # Process tags and categories
                    if "tags" in data:
                        self._tags = set(data["tags"])
                    if "categories" in data:
                        self._categories = set(data["categories"])

                    logger.info(f"Loaded {len(self._trades)} trades from journal")
            else:
                logger.info("No trading journal data found")
        except Exception as e:
            logger.error(f"Error loading trading journal data: {e}")

    async def _save_journal_data(self) -> None:
        """Save journal data to storage."""
        try:
            async with self.lock:
                # Prepare data for serialization
                serialized_trades = []
                for trade in self._trades:
                    trade_copy = trade.copy()
                    if isinstance(trade_copy.get("timestamp"), datetime):
                        trade_copy["timestamp"] = trade_copy["timestamp"].isoformat()
                    serialized_trades.append(trade_copy)

                data = {
                    "trades": serialized_trades,
                    "tags": list(self._tags),
                    "categories": list(self._categories),
                }

                with open(self.journal_file, "w") as f:
                    json.dump(data, f, indent=2)

                logger.info(f"Saved {len(self._trades)} trades to journal")
        except Exception as e:
            logger.error(f"Error saving trading journal data: {e}")

    async def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """
        Log a trade to the journal.

        Args:
            trade_data: Dictionary containing trade data with at least:
                - token_in: Input token address (checksummed)
                - token_out: Output token address (checksummed)
                - amount_in: Input amount
                - amount_out: Output amount
                - profit: Profit amount
                - gas_cost: Gas cost in native currency
                - timestamp: Trade timestamp (optional, defaults to now)
                - dexes: List of DEXes used in the trade
                - path: Trading path information
                - category: Trade category (optional)
                - tags: List of tags (optional)
                - notes: Additional notes (optional)
        """
        if not self.initialized:
            raise RuntimeError("Trading journal not initialized")

        # Ensure required fields are present
        required_fields = [
            "token_in",
            "token_out",
            "amount_in",
            "amount_out",
            "profit",
            "gas_cost",
        ]
        for field in required_fields:
            if field not in trade_data:
                raise ValueError(f"Missing required field: {field}")

        # Add timestamp if not present
        if "timestamp" not in trade_data:
            trade_data["timestamp"] = datetime.utcnow()

        # Add trade outcome
        net_profit = float(trade_data.get("profit", 0)) - float(
            trade_data.get("gas_cost", 0)
        )
        trade_data["net_profit"] = net_profit
        trade_data["success"] = net_profit >= self.success_threshold

        # Add default category and tags if not present
        if "category" not in trade_data:
            if net_profit > 0:
                trade_data["category"] = "profitable"
            else:
                trade_data["category"] = "unprofitable"

        if "tags" not in trade_data:
            trade_data["tags"] = []

        # Add automatic tags based on trade data
        if net_profit > self.min_profit_threshold * 5:  # 5x minimum threshold
            trade_data["tags"].append("high_profit")
        elif net_profit < 0:
            trade_data["tags"].append("loss")

        if "gas_cost" in trade_data and float(trade_data["gas_cost"]) > 0:
            gas_to_profit_ratio = (
                float(trade_data["gas_cost"]) / float(trade_data["profit"])
                if float(trade_data["profit"]) > 0
                else float("inf")
            )
            if gas_to_profit_ratio < 0.1:  # Gas cost less than 10% of profit
                trade_data["tags"].append("gas_efficient")
            elif gas_to_profit_ratio > 0.5:  # Gas cost more than 50% of profit
                trade_data["tags"].append("gas_heavy")

        async with self.lock:
            # Add to trades
            self._trades.append(trade_data)

            # Update tags and categories
            if "category" in trade_data:
                self._categories.add(trade_data["category"])

            for tag in trade_data.get("tags", []):
                self._tags.add(tag)

            # Save to storage
            await self._save_journal_data()

    async def get_trades(
        self,
        timeframe: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        token_pair: Optional[str] = None,
        success_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get trades from the journal with filtering.

        Args:
            timeframe: Optional time frame filter ("1h", "24h", "7d", "30d", "all")
            category: Optional category filter
            tags: Optional list of tags to filter by (trades must have ALL tags)
            token_pair: Optional token pair filter (format: "token_in_token_out")
            success_only: If True, only return successful trades
            limit: Maximum number of trades to return
            offset: Number of trades to skip

        Returns:
            List of trades matching the filters
        """
        if not self.initialized:
            raise RuntimeError("Trading journal not initialized")

        async with self.lock:
            # Apply filters
            filtered_trades = self._trades

            # Filter by timeframe
            if timeframe:
                now = datetime.utcnow()
                if timeframe == "1h":
                    start_time = now - timedelta(hours=1)
                elif timeframe == "24h":
                    start_time = now - timedelta(hours=24)
                elif timeframe == "7d":
                    start_time = now - timedelta(days=7)
                elif timeframe == "30d":
                    start_time = now - timedelta(days=30)
                else:  # "all"
                    start_time = datetime.min

                filtered_trades = [
                    trade
                    for trade in filtered_trades
                    if trade.get("timestamp", now) >= start_time
                ]

            # Filter by category
            if category:
                filtered_trades = [
                    trade
                    for trade in filtered_trades
                    if trade.get("category") == category
                ]

            # Filter by tags
            if tags:
                filtered_trades = [
                    trade
                    for trade in filtered_trades
                    if all(tag in trade.get("tags", []) for tag in tags)
                ]

            # Filter by token pair
            if token_pair:
                filtered_trades = [
                    trade
                    for trade in filtered_trades
                    if (
                        trade.get("token_in")
                        and trade.get("token_out")
                        and f"{trade['token_in']}_{trade['token_out']}" == token_pair
                    )
                ]

            # Filter by success
            if success_only:
                filtered_trades = [
                    trade for trade in filtered_trades if trade.get("success", False)
                ]

            # Sort by timestamp (newest first)
            filtered_trades.sort(
                key=lambda x: x.get("timestamp", datetime.min), reverse=True
            )

            # Apply pagination
            paginated_trades = filtered_trades[offset : offset + limit]

            return paginated_trades

    async def analyze_trade_outcomes(
        self, timeframe: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze trade outcomes for the specified timeframe.

        Args:
            timeframe: Optional time frame for analysis ("1h", "24h", "7d", "30d", "all")

        Returns:
            Dictionary with trade outcome analysis
        """
        if not self.initialized:
            raise RuntimeError("Trading journal not initialized")

        async with self.lock:
            # Get trades for the timeframe
            trades = await self.get_trades(timeframe=timeframe, limit=10000)

            if not trades:
                return {
                    "timeframe": timeframe,
                    "total_trades": 0,
                    "successful_trades": 0,
                    "failed_trades": 0,
                    "success_rate": 0,
                    "total_profit": 0,
                    "total_loss": 0,
                    "net_profit": 0,
                    "avg_profit_per_trade": 0,
                    "avg_gas_cost": 0,
                    "most_profitable_trade": None,
                    "least_profitable_trade": None,
                }

            # Calculate metrics
            successful_trades = [
                trade for trade in trades if trade.get("success", False)
            ]
            failed_trades = [
                trade for trade in trades if not trade.get("success", False)
            ]

            total_profit = sum(
                float(trade.get("net_profit", 0)) for trade in successful_trades
            )
            total_loss = abs(
                sum(float(trade.get("net_profit", 0)) for trade in failed_trades)
            )
            net_profit = total_profit - total_loss

            avg_profit = net_profit / len(trades) if trades else 0
            avg_gas_cost = (
                sum(float(trade.get("gas_cost", 0)) for trade in trades) / len(trades)
                if trades
                else 0
            )

            # Find most and least profitable trades
            if trades:
                most_profitable = max(
                    trades, key=lambda x: float(x.get("net_profit", 0))
                )
                least_profitable = min(
                    trades, key=lambda x: float(x.get("net_profit", 0))
                )
            else:
                most_profitable = None
                least_profitable = None

            return {
                "timeframe": timeframe,
                "total_trades": len(trades),
                "successful_trades": len(successful_trades),
                "failed_trades": len(failed_trades),
                "success_rate": len(successful_trades) / len(trades) if trades else 0,
                "total_profit": total_profit,
                "total_loss": total_loss,
                "net_profit": net_profit,
                "avg_profit_per_trade": avg_profit,
                "avg_gas_cost": avg_gas_cost,
                "most_profitable_trade": most_profitable,
                "least_profitable_trade": least_profitable,
            }

    async def get_trade_categories(self) -> List[str]:
        """
        Get all trade categories.

        Returns:
            List of trade categories
        """
        if not self.initialized:
            raise RuntimeError("Trading journal not initialized")

        async with self.lock:
            return list(self._categories)

    async def get_trade_tags(self) -> List[str]:
        """
        Get all trade tags.

        Returns:
            List of trade tags
        """
        if not self.initialized:
            raise RuntimeError("Trading journal not initialized")

        async with self.lock:
            return list(self._tags)

    async def add_note_to_trade(self, trade_id: str, note: str) -> bool:
        """
        Add a note to a trade.

        Args:
            trade_id: ID of the trade
            note: Note to add

        Returns:
            True if note added successfully
        """
        if not self.initialized:
            raise RuntimeError("Trading journal not initialized")

        async with self.lock:
            # Find trade by ID
            for trade in self._trades:
                if trade.get("id") == trade_id:
                    # Add note
                    if "notes" not in trade:
                        trade["notes"] = []

                    trade["notes"].append(
                        {"text": note, "timestamp": datetime.utcnow()}
                    )

                    # Save to storage
                    await self._save_journal_data()
                    return True

            return False

    async def add_tag_to_trade(self, trade_id: str, tag: str) -> bool:
        """
        Add a tag to a trade.

        Args:
            trade_id: ID of the trade
            tag: Tag to add

        Returns:
            True if tag added successfully
        """
        if not self.initialized:
            raise RuntimeError("Trading journal not initialized")

        async with self.lock:
            # Find trade by ID
            for trade in self._trades:
                if trade.get("id") == trade_id:
                    # Add tag
                    if "tags" not in trade:
                        trade["tags"] = []

                    if tag not in trade["tags"]:
                        trade["tags"].append(tag)
                        self._tags.add(tag)

                    # Save to storage
                    await self._save_journal_data()
                    return True

            return False

    async def extract_learning_insights(
        self, timeframe: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract learning insights from trades.

        Args:
            timeframe: Optional time frame for analysis ("1h", "24h", "7d", "30d", "all")

        Returns:
            Dictionary with learning insights
        """
        if not self.initialized:
            raise RuntimeError("Trading journal not initialized")

        async with self.lock:
            # Get trades for the timeframe
            trades = await self.get_trades(timeframe=timeframe, limit=10000)

            if not trades:
                return {
                    "timeframe": timeframe,
                    "insights": [],
                    "common_patterns": [],
                    "improvement_areas": [],
                }

            # Extract insights
            insights = []

            # Analyze profitable vs unprofitable trades
            profitable_trades = [t for t in trades if float(t.get("net_profit", 0)) > 0]
            unprofitable_trades = [
                t for t in trades if float(t.get("net_profit", 0)) <= 0
            ]

            if profitable_trades and unprofitable_trades:
                # Compare gas costs
                avg_gas_profitable = sum(
                    float(t.get("gas_cost", 0)) for t in profitable_trades
                ) / len(profitable_trades)
                avg_gas_unprofitable = sum(
                    float(t.get("gas_cost", 0)) for t in unprofitable_trades
                ) / len(unprofitable_trades)

                if avg_gas_profitable < avg_gas_unprofitable:
                    insights.append(
                        {
                            "type": "gas_optimization",
                            "description": "Profitable trades have lower gas costs on average",
                            "data": {
                                "avg_gas_profitable": avg_gas_profitable,
                                "avg_gas_unprofitable": avg_gas_unprofitable,
                                "difference_percent": (
                                    (avg_gas_unprofitable - avg_gas_profitable)
                                    / avg_gas_unprofitable
                                    * 100
                                    if avg_gas_unprofitable > 0
                                    else 0
                                ),
                            },
                        }
                    )

                # Compare DEXes used
                dexes_profitable = {}
                for trade in profitable_trades:
                    for dex in trade.get("dexes", []):
                        dexes_profitable[dex] = dexes_profitable.get(dex, 0) + 1

                dexes_unprofitable = {}
                for trade in unprofitable_trades:
                    for dex in trade.get("dexes", []):
                        dexes_unprofitable[dex] = dexes_unprofitable.get(dex, 0) + 1

                # Find DEXes that appear more in profitable trades
                profitable_dexes = []
                for dex, count in dexes_profitable.items():
                    profitable_ratio = count / len(profitable_trades)
                    unprofitable_ratio = (
                        dexes_unprofitable.get(dex, 0) / len(unprofitable_trades)
                        if len(unprofitable_trades) > 0
                        else 0
                    )

                    if (
                        profitable_ratio > unprofitable_ratio * 1.5
                    ):  # 50% more common in profitable trades
                        profitable_dexes.append(
                            {
                                "dex": dex,
                                "profitable_ratio": profitable_ratio,
                                "unprofitable_ratio": unprofitable_ratio,
                            }
                        )

                if profitable_dexes:
                    insights.append(
                        {
                            "type": "dex_preference",
                            "description": "Some DEXes appear more frequently in profitable trades",
                            "data": {"profitable_dexes": profitable_dexes},
                        }
                    )

            # Analyze common patterns
            common_patterns = []

            # Token pair analysis
            token_pairs = {}
            for trade in trades:
                if "token_in" in trade and "token_out" in trade:
                    pair = f"{trade['token_in']}_{trade['token_out']}"
                    if pair not in token_pairs:
                        token_pairs[pair] = {
                            "count": 0,
                            "profitable": 0,
                            "unprofitable": 0,
                            "total_profit": 0,
                            "total_loss": 0,
                        }

                    token_pairs[pair]["count"] += 1
                    net_profit = float(trade.get("net_profit", 0))

                    if net_profit > 0:
                        token_pairs[pair]["profitable"] += 1
                        token_pairs[pair]["total_profit"] += net_profit
                    else:
                        token_pairs[pair]["unprofitable"] += 1
                        token_pairs[pair]["total_loss"] += abs(net_profit)

            # Find most profitable token pairs
            profitable_pairs = []
            for pair, data in token_pairs.items():
                if data["count"] >= 5:  # At least 5 trades
                    success_rate = data["profitable"] / data["count"]
                    avg_profit = (
                        data["total_profit"] / data["profitable"]
                        if data["profitable"] > 0
                        else 0
                    )

                    if success_rate > 0.7:  # 70% success rate
                        profitable_pairs.append(
                            {
                                "token_pair": pair,
                                "success_rate": success_rate,
                                "avg_profit": avg_profit,
                                "trade_count": data["count"],
                            }
                        )

            if profitable_pairs:
                common_patterns.append(
                    {
                        "type": "profitable_token_pairs",
                        "description": "Token pairs with high success rates",
                        "data": {"pairs": profitable_pairs},
                    }
                )

            # Identify improvement areas
            improvement_areas = []

            # Gas optimization opportunities
            high_gas_trades = [
                t
                for t in trades
                if float(t.get("gas_cost", 0)) > 0
                and float(t.get("net_profit", 0)) <= 0
            ]
            if high_gas_trades:
                improvement_areas.append(
                    {
                        "type": "gas_optimization",
                        "description": "Reduce gas costs for unprofitable trades",
                        "data": {
                            "trade_count": len(high_gas_trades),
                            "avg_gas_cost": sum(
                                float(t.get("gas_cost", 0)) for t in high_gas_trades
                            )
                            / len(high_gas_trades),
                            "total_gas_spent": sum(
                                float(t.get("gas_cost", 0)) for t in high_gas_trades
                            ),
                        },
                    }
                )

            # DEX selection opportunities
            if unprofitable_trades:
                dex_counts = {}
                for trade in unprofitable_trades:
                    for dex in trade.get("dexes", []):
                        dex_counts[dex] = dex_counts.get(dex, 0) + 1

                problematic_dexes = []
                for dex, count in dex_counts.items():
                    if (
                        count / len(unprofitable_trades) > 0.5
                    ):  # Present in more than 50% of unprofitable trades
                        problematic_dexes.append(
                            {
                                "dex": dex,
                                "occurrence_rate": count / len(unprofitable_trades),
                            }
                        )

                if problematic_dexes:
                    improvement_areas.append(
                        {
                            "type": "dex_selection",
                            "description": "Reconsider using certain DEXes that appear frequently in unprofitable trades",
                            "data": {"dexes": problematic_dexes},
                        }
                    )

            return {
                "timeframe": timeframe,
                "insights": insights,
                "common_patterns": common_patterns,
                "improvement_areas": improvement_areas,
            }


async def create_trading_journal(
    config: Optional[Dict[str, Any]] = None,
) -> TradingJournal:
    """
    Create and initialize a trading journal.

    Args:
        config: Optional configuration

    Returns:
        Initialized TradingJournal instance
    """
    journal = TradingJournal(config)
    if not await journal.initialize():
        raise RuntimeError("Failed to initialize trading journal")
    return journal
