"""
Profit Tracker Module

Provides comprehensive profit tracking and analysis for the arbitrage system.
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


class ProfitTracker:
    """
    Tracks and analyzes profit metrics for arbitrage operations.

    Features:
    - Historical performance tracking
    - Profit attribution by token pair
    - ROI calculation with various time frames
    - Profit visualization with time series analysis
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the profit tracker.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.initialized = False
        self.lock = asyncio.Lock()

        # Storage for profit data
        self._profit_history = []
        self._token_pair_profits = {}
        self._timeframe_profits = {"1h": [], "24h": [], "7d": [], "30d": [], "all": []}

        # Storage paths
        self.storage_dir = self.config.get("storage_dir", "analytics")
        self.profit_file = os.path.join(self.storage_dir, "profit_history.json")

        # Cache settings
        self.cache_ttl = int(self.config.get("cache_ttl", 300))  # 5 minutes
        self._last_cache_update = 0

    async def initialize(self) -> bool:
        """
        Initialize the profit tracker.

        Returns:
            True if initialization successful
        """
        try:
            # Create storage directory if it doesn't exist
            os.makedirs(self.storage_dir, exist_ok=True)

            # Load historical data if available
            await self._load_historical_data()

            self.initialized = True
            logger.info("Profit tracker initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize profit tracker: {e}")
            return False

    async def _load_historical_data(self) -> None:
        """Load historical profit data from storage."""
        try:
            if os.path.exists(self.profit_file):
                async with self.lock:
                    with open(self.profit_file, "r") as f:
                        data = json.load(f)

                    # Convert string timestamps back to datetime objects
                    for entry in data:
                        if "timestamp" in entry:
                            entry["timestamp"] = datetime.fromisoformat(
                                entry["timestamp"]
                            )

                    self._profit_history = data
                    await self._update_derived_metrics()
                    logger.info(f"Loaded {len(data)} historical profit entries")
            else:
                logger.info("No historical profit data found")
        except Exception as e:
            logger.error(f"Error loading historical profit data: {e}")

    async def _save_historical_data(self) -> None:
        """Save historical profit data to storage."""
        try:
            async with self.lock:
                # Convert datetime objects to ISO format strings for JSON serialization
                data_to_save = []
                for entry in self._profit_history:
                    entry_copy = entry.copy()
                    if isinstance(entry_copy.get("timestamp"), datetime):
                        entry_copy["timestamp"] = entry_copy["timestamp"].isoformat()
                    data_to_save.append(entry_copy)

                with open(self.profit_file, "w") as f:
                    json.dump(data_to_save, f, indent=2)

                logger.info(
                    f"Saved {len(data_to_save)} profit entries to {self.profit_file}"
                )
        except Exception as e:
            logger.error(f"Error saving historical profit data: {e}")

    async def track_profit(self, trade_data: Dict[str, Any]) -> None:
        """
        Track a new profit entry.

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
        """
        if not self.initialized:
            raise RuntimeError("Profit tracker not initialized")

        # Ensure required fields are present
        required_fields = ["token_in", "token_out", "amount_in", "amount_out", "profit"]
        for field in required_fields:
            if field not in trade_data:
                raise ValueError(f"Missing required field: {field}")

        # Add timestamp if not present
        if "timestamp" not in trade_data:
            trade_data["timestamp"] = datetime.utcnow()

        # Create token pair identifier
        token_pair = f"{trade_data['token_in']}_{trade_data['token_out']}"
        trade_data["token_pair"] = token_pair

        async with self.lock:
            # Add to profit history
            self._profit_history.append(trade_data)

            # Update derived metrics
            await self._update_derived_metrics()

            # Save to storage
            await self._save_historical_data()

    async def _update_derived_metrics(self) -> None:
        """Update all derived profit metrics."""
        try:
            # Update cache timestamp
            self._last_cache_update = asyncio.get_event_loop().time()

            # Clear existing derived metrics
            self._token_pair_profits = {}
            for timeframe in self._timeframe_profits:
                self._timeframe_profits[timeframe] = []

            # Process all profit entries
            now = datetime.utcnow()
            for entry in self._profit_history:
                # Token pair attribution
                token_pair = entry.get("token_pair")
                if not token_pair and "token_in" in entry and "token_out" in entry:
                    token_pair = f"{entry['token_in']}_{entry['token_out']}"

                if token_pair:
                    if token_pair not in self._token_pair_profits:
                        self._token_pair_profits[token_pair] = []
                    self._token_pair_profits[token_pair].append(entry)

                # Timeframe attribution
                timestamp = entry.get("timestamp", now)

                # All time
                self._timeframe_profits["all"].append(entry)

                # Last 30 days
                if timestamp >= now - timedelta(days=30):
                    self._timeframe_profits["30d"].append(entry)

                # Last 7 days
                if timestamp >= now - timedelta(days=7):
                    self._timeframe_profits["7d"].append(entry)

                # Last 24 hours
                if timestamp >= now - timedelta(hours=24):
                    self._timeframe_profits["24h"].append(entry)

                # Last hour
                if timestamp >= now - timedelta(hours=1):
                    self._timeframe_profits["1h"].append(entry)

            logger.debug("Updated derived profit metrics")

        except Exception as e:
            logger.error(f"Error updating derived profit metrics: {e}")

    async def _ensure_cache_fresh(self) -> None:
        """Ensure the cache is fresh, update if needed."""
        current_time = asyncio.get_event_loop().time()
        if current_time - self._last_cache_update > self.cache_ttl:
            await self._update_derived_metrics()

    async def get_profit_by_token_pair(
        self, token_pair: Optional[str] = None, timeframe: str = "24h"
    ) -> Dict[str, Any]:
        """
        Get profit metrics for specific token pairs.

        Args:
            token_pair: Optional token pair identifier (format: "token_in_token_out")
                        If None, returns metrics for all token pairs
            timeframe: Time frame for metrics ("1h", "24h", "7d", "30d", "all")

        Returns:
            Dictionary with profit metrics for the specified token pair(s)
        """
        if not self.initialized:
            raise RuntimeError("Profit tracker not initialized")

        if timeframe not in self._timeframe_profits:
            raise ValueError(
                f"Invalid timeframe: {timeframe}. Valid options: {list(self._timeframe_profits.keys())}"
            )

        async with self.lock:
            await self._ensure_cache_fresh()

            # Filter by timeframe
            entries = self._timeframe_profits[timeframe]

            if token_pair:
                # Filter by token pair
                entries = [
                    e
                    for e in entries
                    if e.get("token_pair") == token_pair
                    or (
                        e.get("token_in")
                        and e.get("token_out")
                        and f"{e['token_in']}_{e['token_out']}" == token_pair
                    )
                ]

                # Calculate metrics for specific token pair
                total_profit = sum(float(e.get("profit", 0)) for e in entries)
                total_volume = sum(float(e.get("amount_in", 0)) for e in entries)
                trade_count = len(entries)
                avg_profit = total_profit / trade_count if trade_count > 0 else 0

                return {
                    "token_pair": token_pair,
                    "timeframe": timeframe,
                    "total_profit": total_profit,
                    "total_volume": total_volume,
                    "trade_count": trade_count,
                    "avg_profit": avg_profit,
                    "profit_per_volume": (
                        total_profit / total_volume if total_volume > 0 else 0
                    ),
                }
            else:
                # Calculate metrics for all token pairs
                result = {
                    "timeframe": timeframe,
                    "total_profit": sum(float(e.get("profit", 0)) for e in entries),
                    "total_volume": sum(float(e.get("amount_in", 0)) for e in entries),
                    "trade_count": len(entries),
                    "token_pairs": {},
                }

                # Group by token pair
                token_pair_entries = {}
                for entry in entries:
                    pair = entry.get("token_pair")
                    if not pair and "token_in" in entry and "token_out" in entry:
                        pair = f"{entry['token_in']}_{entry['token_out']}"

                    if pair:
                        if pair not in token_pair_entries:
                            token_pair_entries[pair] = []
                        token_pair_entries[pair].append(entry)

                # Calculate metrics for each token pair
                for pair, pair_entries in token_pair_entries.items():
                    pair_profit = sum(float(e.get("profit", 0)) for e in pair_entries)
                    pair_volume = sum(
                        float(e.get("amount_in", 0)) for e in pair_entries
                    )
                    pair_count = len(pair_entries)

                    result["token_pairs"][pair] = {
                        "total_profit": pair_profit,
                        "total_volume": pair_volume,
                        "trade_count": pair_count,
                        "avg_profit": pair_profit / pair_count if pair_count > 0 else 0,
                        "profit_per_volume": (
                            pair_profit / pair_volume if pair_volume > 0 else 0
                        ),
                        "percentage_of_total": (
                            pair_profit / result["total_profit"] * 100
                            if result["total_profit"] > 0
                            else 0
                        ),
                    }

                # Add average metrics
                if result["trade_count"] > 0:
                    result["avg_profit"] = (
                        result["total_profit"] / result["trade_count"]
                    )
                else:
                    result["avg_profit"] = 0

                if result["total_volume"] > 0:
                    result["profit_per_volume"] = (
                        result["total_profit"] / result["total_volume"]
                    )
                else:
                    result["profit_per_volume"] = 0

                return result

    async def get_roi(self, timeframe: str = "24h") -> Dict[str, Any]:
        """
        Calculate ROI for the specified timeframe.

        Args:
            timeframe: Time frame for ROI calculation ("1h", "24h", "7d", "30d", "all")

        Returns:
            Dictionary with ROI metrics
        """
        if not self.initialized:
            raise RuntimeError("Profit tracker not initialized")

        if timeframe not in self._timeframe_profits:
            raise ValueError(
                f"Invalid timeframe: {timeframe}. Valid options: {list(self._timeframe_profits.keys())}"
            )

        async with self.lock:
            await self._ensure_cache_fresh()

            entries = self._timeframe_profits[timeframe]

            total_investment = sum(float(e.get("amount_in", 0)) for e in entries)
            total_profit = sum(float(e.get("profit", 0)) for e in entries)
            total_gas_cost = sum(float(e.get("gas_cost", 0)) for e in entries)
            net_profit = total_profit - total_gas_cost

            # Calculate ROI
            roi = net_profit / total_investment * 100 if total_investment > 0 else 0

            # Calculate annualized ROI
            days_factor = {
                "1h": 365 * 24,  # Hourly to annual
                "24h": 365,  # Daily to annual
                "7d": 365 / 7,  # Weekly to annual
                "30d": 12,  # Monthly to annual
                "all": 1,  # All time (no annualization)
            }

            annualized_roi = (
                roi * days_factor.get(timeframe, 1) if timeframe != "all" else None
            )

            return {
                "timeframe": timeframe,
                "total_investment": total_investment,
                "total_profit": total_profit,
                "total_gas_cost": total_gas_cost,
                "net_profit": net_profit,
                "roi": roi,
                "annualized_roi": annualized_roi,
                "trade_count": len(entries),
            }

    async def get_profit_time_series(
        self, timeframe: str = "7d", interval: str = "1h"
    ) -> Dict[str, List[Any]]:
        """
        Get profit time series data for visualization.

        Args:
            timeframe: Time frame for data ("1h", "24h", "7d", "30d", "all")
            interval: Data aggregation interval ("5m", "15m", "1h", "4h", "1d")

        Returns:
            Dictionary with time series data for visualization
        """
        if not self.initialized:
            raise RuntimeError("Profit tracker not initialized")

        # Validate timeframe
        if timeframe not in self._timeframe_profits and timeframe != "custom":
            raise ValueError(
                f"Invalid timeframe: {timeframe}. Valid options: {list(self._timeframe_profits.keys())}"
            )

        # Define interval durations in minutes
        interval_minutes = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}

        if interval not in interval_minutes:
            raise ValueError(
                f"Invalid interval: {interval}. Valid options: {list(interval_minutes.keys())}"
            )

        async with self.lock:
            await self._ensure_cache_fresh()

            # Determine time range
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
                # Find earliest timestamp in data
                if self._profit_history:
                    timestamps = [e.get("timestamp", now) for e in self._profit_history]
                    start_time = min(timestamps)
                else:
                    start_time = now - timedelta(
                        days=30
                    )  # Default to 30 days if no data

            # Filter entries by timeframe
            entries = [
                e for e in self._profit_history if e.get("timestamp", now) >= start_time
            ]

            # Group entries by interval
            interval_delta = timedelta(minutes=interval_minutes[interval])
            intervals = []

            current_time = start_time
            while current_time <= now:
                intervals.append((current_time, current_time + interval_delta))
                current_time += interval_delta

            # Initialize result structure
            result = {
                "timestamps": [],
                "profit": [],
                "cumulative_profit": [],
                "trade_count": [],
                "volume": [],
            }

            # Calculate metrics for each interval
            cumulative_profit = 0
            for start, end in intervals:
                interval_entries = [
                    e for e in entries if start <= e.get("timestamp", now) < end
                ]

                interval_profit = sum(
                    float(e.get("profit", 0)) for e in interval_entries
                )
                interval_volume = sum(
                    float(e.get("amount_in", 0)) for e in interval_entries
                )
                interval_count = len(interval_entries)

                cumulative_profit += interval_profit

                result["timestamps"].append(start.isoformat())
                result["profit"].append(interval_profit)
                result["cumulative_profit"].append(cumulative_profit)
                result["trade_count"].append(interval_count)
                result["volume"].append(interval_volume)

            return result

    async def get_top_token_pairs(
        self, timeframe: str = "7d", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top performing token pairs by profit.

        Args:
            timeframe: Time frame for analysis ("1h", "24h", "7d", "30d", "all")
            limit: Maximum number of pairs to return

        Returns:
            List of dictionaries with token pair metrics, sorted by profit
        """
        if not self.initialized:
            raise RuntimeError("Profit tracker not initialized")

        if timeframe not in self._timeframe_profits:
            raise ValueError(
                f"Invalid timeframe: {timeframe}. Valid options: {list(self._timeframe_profits.keys())}"
            )

        async with self.lock:
            await self._ensure_cache_fresh()

            # Get all token pairs with their metrics
            all_pairs = await self.get_profit_by_token_pair(timeframe=timeframe)

            # Extract and sort token pairs
            pairs = []
            for pair_id, metrics in all_pairs.get("token_pairs", {}).items():
                pairs.append({"token_pair": pair_id, **metrics})

            # Sort by total profit (descending)
            pairs.sort(key=lambda x: x.get("total_profit", 0), reverse=True)

            # Return top N pairs
            return pairs[:limit]

    async def get_profit_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive profit summary across all timeframes.

        Returns:
            Dictionary with profit summary metrics
        """
        if not self.initialized:
            raise RuntimeError("Profit tracker not initialized")

        async with self.lock:
            await self._ensure_cache_fresh()

            # Get metrics for all timeframes
            result = {}
            for timeframe in self._timeframe_profits:
                metrics = await self.get_profit_by_token_pair(timeframe=timeframe)
                roi = await self.get_roi(timeframe=timeframe)

                result[timeframe] = {
                    "total_profit": metrics.get("total_profit", 0),
                    "total_volume": metrics.get("total_volume", 0),
                    "trade_count": metrics.get("trade_count", 0),
                    "roi": roi.get("roi", 0),
                    "annualized_roi": roi.get("annualized_roi"),
                    "token_pair_count": len(metrics.get("token_pairs", {})),
                }

            # Add all-time stats
            all_time = result.get("all", {})
            result["summary"] = {
                "total_profit_all_time": all_time.get("total_profit", 0),
                "total_volume_all_time": all_time.get("total_volume", 0),
                "trade_count_all_time": all_time.get("trade_count", 0),
                "first_trade_date": self._get_first_trade_date(),
                "most_profitable_day": await self._get_most_profitable_day(),
                "most_profitable_pair": await self._get_most_profitable_pair(),
            }

            return result

    def _get_first_trade_date(self) -> Optional[str]:
        """Get the date of the first recorded trade."""
        if not self._profit_history:
            return None

        timestamps = [
            e.get("timestamp") for e in self._profit_history if e.get("timestamp")
        ]
        if not timestamps:
            return None

        return min(timestamps).date().isoformat()

    async def _get_most_profitable_day(self) -> Dict[str, Any]:
        """Get the most profitable day."""
        if not self._profit_history:
            return {"date": None, "profit": 0}

        # Group profits by day
        daily_profits = {}
        for entry in self._profit_history:
            timestamp = entry.get("timestamp")
            if not timestamp:
                continue

            date_str = timestamp.date().isoformat()
            if date_str not in daily_profits:
                daily_profits[date_str] = 0

            daily_profits[date_str] += float(entry.get("profit", 0))

        if not daily_profits:
            return {"date": None, "profit": 0}

        # Find the most profitable day
        most_profitable_date = max(daily_profits.items(), key=lambda x: x[1])
        return {"date": most_profitable_date[0], "profit": most_profitable_date[1]}

    async def _get_most_profitable_pair(self) -> Dict[str, Any]:
        """Get the most profitable token pair."""
        all_time_pairs = await self.get_top_token_pairs(timeframe="all", limit=1)
        if not all_time_pairs:
            return {"token_pair": None, "profit": 0}

        return {
            "token_pair": all_time_pairs[0].get("token_pair"),
            "profit": all_time_pairs[0].get("total_profit", 0),
        }


async def create_profit_tracker(
    config: Optional[Dict[str, Any]] = None,
) -> ProfitTracker:
    """
    Create and initialize a profit tracker.

    Args:
        config: Optional configuration

    Returns:
        Initialized ProfitTracker instance
    """
    tracker = ProfitTracker(config)
    if not await tracker.initialize():
        raise RuntimeError("Failed to initialize profit tracker")
    return tracker
