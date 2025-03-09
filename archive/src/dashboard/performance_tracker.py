"""Performance tracking and metrics collection"""

import logging
import time
import json
from typing import Dict, Any, Optional
from decimal import Decimal
import sqlite3
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class PerformanceTracker:
    def __init__(self):
        """Initialize performance tracker"""
        # Get project root directory
        root_dir = Path(__file__).parent.parent.parent
        self.data_dir = root_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.db_path = self.data_dir / "arbitrage.db"
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure required database tables exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create trades table with additional fields
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                        token_in TEXT NOT NULL,
                        token_out TEXT NOT NULL,
                        amount_in DECIMAL(18,8) NOT NULL,
                        amount_out DECIMAL(18,8) NOT NULL,
                        profit DECIMAL(18,8) NOT NULL,
                        gas_used INTEGER NOT NULL,
                        tx_hash TEXT NOT NULL UNIQUE,
                        base_dex TEXT,
                        quote_dex TEXT,
                        price_difference_percent DECIMAL(18,8),
                        status TEXT,
                        net_profit DECIMAL(18,8),
                        gas_cost DECIMAL(18,8)
                    )
                """
                )

                # Create opportunities table for tracking detected opportunities
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS opportunities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                        base_dex TEXT NOT NULL,
                        quote_dex TEXT NOT NULL,
                        token_in TEXT NOT NULL,
                        token_out TEXT NOT NULL,
                        price_difference_percent DECIMAL(18,8) NOT NULL,
                        estimated_profit DECIMAL(18,8) NOT NULL,
                        estimated_gas_cost DECIMAL(18,8) NOT NULL,
                        status TEXT NOT NULL,
                        trade_id INTEGER,
                        FOREIGN KEY(trade_id) REFERENCES trades(id)
                    )
                """
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error ensuring tables: {e}")
            self._create_empty_tables()

    def _create_empty_tables(self):
        """Create empty tables with basic structure"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create basic trades table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                        token_in TEXT NOT NULL DEFAULT '',
                        token_out TEXT NOT NULL DEFAULT '',
                        amount_in DECIMAL(18,8) NOT NULL DEFAULT 0,
                        amount_out DECIMAL(18,8) NOT NULL DEFAULT 0,
                        profit DECIMAL(18,8) NOT NULL DEFAULT 0,
                        gas_used INTEGER NOT NULL DEFAULT 0,
                        tx_hash TEXT NOT NULL DEFAULT '' UNIQUE
                    )
                """
                )

                # Create basic opportunities table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS opportunities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                        base_dex TEXT NOT NULL DEFAULT '',
                        quote_dex TEXT NOT NULL DEFAULT '',
                        token_in TEXT NOT NULL DEFAULT '',
                        token_out TEXT NOT NULL DEFAULT '',
                        price_difference_percent DECIMAL(18,8) NOT NULL DEFAULT 0,
                        estimated_profit DECIMAL(18,8) NOT NULL DEFAULT 0,
                        estimated_gas_cost DECIMAL(18,8) NOT NULL DEFAULT 0,
                        status TEXT NOT NULL DEFAULT ''
                    )
                """
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error creating empty tables: {e}")

    def log_opportunity(self, opportunity: Dict[str, Any], status: str) -> int:
        """
        Log arbitrage opportunity

        :param opportunity: Opportunity details
        :param status: Status of the opportunity (detected/executed/failed)
        :return: Opportunity ID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO opportunities (
                        timestamp,
                        base_dex,
                        quote_dex,
                        token_in,
                        token_out,
                        price_difference_percent,
                        estimated_profit,
                        estimated_gas_cost,
                        status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        int(time.time()),
                        opportunity.get("base_dex", ""),
                        opportunity.get("quote_dex", ""),
                        opportunity.get("token_in", ""),
                        opportunity.get("token_out", ""),
                        float(opportunity.get("price_difference_percent", 0)),
                        float(opportunity.get("net_profit", 0)),
                        float(opportunity.get("estimated_gas_cost", 0)),
                        status,
                    ),
                )

                opportunity_id = cursor.lastrowid
                conn.commit()
                return opportunity_id

        except Exception as e:
            logger.error(f"Error logging opportunity: {e}")
            return -1

    def log_trade(
        self, opportunity_id: int, trade_details: Dict[str, Any], status: str
    ):
        """
        Log executed trade

        :param opportunity_id: ID of the related opportunity
        :param trade_details: Trade execution details
        :param status: Status of the trade (completed/failed)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert trade record
                cursor.execute(
                    """
                    INSERT INTO trades (
                        timestamp,
                        token_in,
                        token_out,
                        amount_in,
                        amount_out,
                        profit,
                        gas_used,
                        tx_hash,
                        base_dex,
                        quote_dex,
                        price_difference_percent,
                        status,
                        net_profit,
                        gas_cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        int(time.time()),
                        trade_details.get("token_in", ""),
                        trade_details.get("token_out", ""),
                        float(trade_details.get("amount_in", 0)),
                        float(trade_details.get("amount_out", 0)),
                        float(trade_details.get("profit", 0)),
                        int(trade_details.get("gas_used", 0)),
                        trade_details.get("tx_hash", "0x" + "0" * 64),
                        trade_details.get("base_dex", ""),
                        trade_details.get("quote_dex", ""),
                        float(trade_details.get("price_difference_percent", 0)),
                        status,
                        float(trade_details.get("net_profit", 0)),
                        float(trade_details.get("gas_cost", 0)),
                    ),
                )

                trade_id = cursor.lastrowid

                # Update opportunity with trade ID
                cursor.execute(
                    """
                    UPDATE opportunities
                    SET trade_id = ?, status = ?
                    WHERE id = ?
                """,
                    (trade_id, status, opportunity_id),
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error logging trade: {e}")

    def get_trade_feed(self, limit: int = 50) -> Dict[str, Any]:
        """
        Get recent trade feed data

        :param limit: Maximum number of entries to return
        :return: Dictionary containing opportunities and trades
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get recent opportunities
                cursor.execute(
                    """
                    SELECT 
                        id,
                        timestamp,
                        base_dex,
                        quote_dex,
                        token_in,
                        token_out,
                        price_difference_percent,
                        estimated_profit,
                        estimated_gas_cost,
                        status
                    FROM opportunities
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (limit,),
                )

                opportunities = [
                    {
                        "id": row[0],
                        "timestamp": row[1],
                        "base_dex": row[2],
                        "quote_dex": row[3],
                        "token_in": row[4],
                        "token_out": row[5],
                        "price_difference_percent": float(row[6]),
                        "estimated_profit": float(row[7]),
                        "estimated_gas_cost": float(row[8]),
                        "status": row[9],
                    }
                    for row in cursor.fetchall()
                ]

                # Get recent trades
                cursor.execute(
                    """
                    SELECT 
                        id,
                        timestamp,
                        token_in,
                        token_out,
                        amount_in,
                        amount_out,
                        profit,
                        gas_used,
                        tx_hash,
                        base_dex,
                        quote_dex,
                        price_difference_percent,
                        status,
                        net_profit,
                        gas_cost
                    FROM trades
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (limit,),
                )

                trades = [
                    {
                        "id": row[0],
                        "timestamp": row[1],
                        "token_in": row[2],
                        "token_out": row[3],
                        "amount_in": float(row[4]),
                        "amount_out": float(row[5]),
                        "profit": float(row[6]),
                        "gas_used": int(row[7]),
                        "tx_hash": row[8],
                        "base_dex": row[9],
                        "quote_dex": row[10],
                        "price_difference_percent": float(row[11]),
                        "status": row[12],
                        "net_profit": float(row[13]),
                        "gas_cost": float(row[14]),
                    }
                    for row in cursor.fetchall()
                ]

                return {"opportunities": opportunities, "trades": trades}

        except Exception as e:
            logger.error(f"Error getting trade feed: {e}")
            return {"opportunities": [], "trades": []}

    def get_performance_data(self) -> Dict[str, Any]:
        """Get performance metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get trade statistics for last 24 hours
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_trades,
                        COALESCE(SUM(net_profit), 0) as total_profit,
                        COALESCE(AVG(gas_used), 0) as avg_gas,
                        COALESCE(SUM(gas_cost), 0) as total_gas_cost
                    FROM trades
                    WHERE timestamp >= ?
                    AND status = 'completed'
                """,
                    (int(time.time() - 86400),),
                )

                row = cursor.fetchone()
                if row:
                    total_trades, total_profit, avg_gas, total_gas_cost = row
                else:
                    total_trades = total_profit = avg_gas = total_gas_cost = 0

                return {
                    "total_trades": total_trades,
                    "total_profit": float(total_profit),
                    "average_gas_used": float(avg_gas),
                    "total_gas_cost": float(total_gas_cost),
                    "last_24h_stats": {
                        "trade_count": total_trades,
                        "profit": float(total_profit),
                        "avg_gas": float(avg_gas),
                        "gas_cost": float(total_gas_cost),
                    },
                }

        except Exception as e:
            logger.error(f"Error getting performance data: {e}")
            return {
                "total_trades": 0,
                "total_profit": 0.0,
                "average_gas_used": 0.0,
                "total_gas_cost": 0.0,
                "last_24h_stats": {
                    "trade_count": 0,
                    "profit": 0.0,
                    "avg_gas": 0.0,
                    "gas_cost": 0.0,
                },
            }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Alias for get_performance_data"""
        return self.get_performance_data()


def get_performance_tracker() -> PerformanceTracker:
    """Get performance tracker instance"""
    return PerformanceTracker()
