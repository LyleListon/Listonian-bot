"""SQLite database utilities for dashboard."""
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DashboardDB:
    """Database operations for dashboard."""

    def __init__(self, db_path: str = "arbitrage_bot.db"):
        """Initialize database connection.
        
        Args:
            db_path (str): Path to SQLite database
        """
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def get_db(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Initialize database with required tables."""
        with self.get_db() as conn:
            cursor = conn.cursor()

            # Create trades table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    dex_from TEXT NOT NULL,
                    dex_to TEXT NOT NULL,
                    token_in TEXT NOT NULL,
                    token_out TEXT NOT NULL,
                    amount_in DECIMAL(18,8) NOT NULL,
                    amount_out DECIMAL(18,8) NOT NULL,
                    amount_in_usd DECIMAL(18,2),
                    amount_out_usd DECIMAL(18,2),
                    profit_usd DECIMAL(18,2) NOT NULL,
                    gas_cost_usd DECIMAL(18,2) NOT NULL,
                    net_profit_usd DECIMAL(18,2) NOT NULL,
                    status TEXT NOT NULL,
                    tx_hash TEXT
                )
            """)

            # Create opportunities table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    token_in TEXT NOT NULL,
                    token_out TEXT NOT NULL,
                    dex_from TEXT NOT NULL,
                    dex_to TEXT NOT NULL,
                    amount_in DECIMAL(18,8) NOT NULL,
                    expected_out DECIMAL(18,8) NOT NULL,
                    profit_usd DECIMAL(18,2) NOT NULL,
                    status TEXT NOT NULL
                )
            """)

            conn.commit()

    def is_bot_running(self) -> bool:
        """Check if the arbitrage bot is running."""
        try:
            # Check if bot.pid exists and process is running
            if os.path.exists('bot.pid'):
                with open('bot.pid', 'r') as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)  # Check if process exists
                    return True
                except OSError:
                    return False
            return False
        except Exception as e:
            logger.error(f"Error checking bot status: {e}")
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """Get current trading metrics."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()

                # Calculate total metrics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_trades,
                        SUM(net_profit_usd) as total_profit
                    FROM trades
                """)
                total_row = cursor.fetchone()
                total_trades, successful_trades, total_profit = total_row

                # Calculate 24h metrics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as trades_24h,
                        SUM(net_profit_usd) as profit_24h,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_24h,
                        SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_24h
                    FROM trades 
                    WHERE datetime(timestamp) > datetime('now', '-1 day')
                """)
                day_row = cursor.fetchone()
                trades_24h, profit_24h, failed_24h, rejected_24h = day_row

                # Get active opportunities count
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM opportunities
                    WHERE status = 'pending'
                    AND datetime(timestamp) > datetime('now', '-5 minutes')
                """)
                active_opportunities = cursor.fetchone()[0]

                success_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0

                return {
                    "total_trades": total_trades,
                    "success_rate": round(success_rate, 2),
                    "total_profit": round(float(total_profit or 0), 2),
                    "active_opportunities": active_opportunities,
                    "last_24h": {
                        "trades": trades_24h or 0,
                        "profit": round(float(profit_24h or 0), 2),
                        "failed": failed_24h or 0,
                        "rejected": rejected_24h or 0
                    },
                    "bot_running": self.is_bot_running()
                }

        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {
                "total_trades": 0,
                "success_rate": 0,
                "total_profit": 0,
                "active_opportunities": 0,
                "last_24h": {"trades": 0, "profit": 0, "failed": 0, "rejected": 0},
                "bot_running": self.is_bot_running()
            }

    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT 
                        timestamp, dex_from, dex_to, token_in, token_out,
                        amount_in, amount_out, profit_usd, gas_cost_usd,
                        net_profit_usd, status, tx_hash
                    FROM trades 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))

                trades = []
                for row in cursor.fetchall():
                    trades.append({
                        "timestamp": row[0],
                        "dex_from": row[1],
                        "dex_to": row[2],
                        "token_in": row[3],
                        "token_out": row[4],
                        "amount_in": float(row[5]),
                        "amount_out": float(row[6]),
                        "profit_usd": float(row[7]),
                        "gas_cost_usd": float(row[8]),
                        "net_profit_usd": float(row[9]),
                        "status": row[10],
                        "tx_hash": row[11]
                    })

                return trades

        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []

    def get_performance_analytics(self) -> Dict[str, List[Any]]:
        """Get performance analytics data."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    WITH RECURSIVE hours AS (
                        SELECT strftime('%Y-%m-%d %H:00:00', datetime('now', '-7 days')) as hour
                        UNION ALL
                        SELECT strftime('%Y-%m-%d %H:00:00', datetime(hour, '+1 hour'))
                        FROM hours
                        WHERE datetime(hour) < datetime('now')
                    ),
                    hourly_metrics AS (
                        SELECT 
                            strftime('%Y-%m-%d %H:00:00', timestamp) as trade_hour,
                            SUM(COALESCE(net_profit_usd, 0)) as hourly_profit,
                            COUNT(*) as trade_count,
                            AVG(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100 as success_rate,
                            AVG(COALESCE(gas_cost_usd, 0)) as avg_gas,
                            SUM(COALESCE(amount_in_usd, amount_in)) as volume_usd
                        FROM trades
                        WHERE timestamp > datetime('now', '-7 days')
                        GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
                    )
                    SELECT 
                        hours.hour,
                        COALESCE(hourly_metrics.hourly_profit, 0) as hourly_profit,
                        COALESCE(hourly_metrics.trade_count, 0) as trade_count,
                        COALESCE(hourly_metrics.success_rate, 0) as success_rate,
                        COALESCE(hourly_metrics.avg_gas, 0) as avg_gas,
                        COALESCE(hourly_metrics.volume_usd, 0) as volume_usd
                    FROM hours
                    LEFT JOIN hourly_metrics ON hours.hour = hourly_metrics.trade_hour
                    ORDER BY hours.hour
                """)

                profit_history = []
                success_rate = []
                gas_usage = []
                volume_history = []
                cumulative_profit = 0

                for row in cursor.fetchall():
                    try:
                        if row[0] is None:
                            continue

                        dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                        timestamp = int(dt.timestamp() * 1000)
                        
                        hourly_profit = float(row[1] if row[1] is not None else 0)
                        cumulative_profit += hourly_profit

                        profit_history.append([timestamp, round(cumulative_profit, 2)])
                        success_rate.append([timestamp, round(float(row[3] if row[3] is not None else 0), 2)])
                        gas_usage.append([timestamp, round(float(row[4] if row[4] is not None else 0), 2)])
                        volume_history.append([timestamp, round(float(row[5] if row[5] is not None else 0), 2)])
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error processing row {row}: {e}")
                        continue

                return {
                    "profit_history": profit_history,
                    "success_rate": success_rate,
                    "gas_usage": gas_usage,
                    "execution_time": [],  # This would come from performance monitoring
                    "volume_history": volume_history
                }

        except Exception as e:
            logger.error(f"Error getting performance analytics: {e}")
            return {
                "profit_history": [],
                "success_rate": [],
                "gas_usage": [],
                "execution_time": [],
                "volume_history": []
            }

    def get_chart_data(self) -> Dict[str, List[Any]]:
        """Get data for charts."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    WITH RECURSIVE hours AS (
                        SELECT strftime('%Y-%m-%d %H:00:00', datetime('now', '-7 days')) as hour
                        UNION ALL
                        SELECT strftime('%Y-%m-%d %H:00:00', datetime(hour, '+1 hour'))
                        FROM hours
                        WHERE datetime(hour) < datetime('now')
                    ),
                    hourly_volume AS (
                        SELECT 
                            strftime('%Y-%m-%d %H:00:00', timestamp) as trade_hour,
                            COUNT(*) as trade_count,
                            SUM(COALESCE(amount_in_usd, amount_in)) as volume_usd
                        FROM trades
                        WHERE timestamp > datetime('now', '-7 days')
                        GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
                    )
                    SELECT 
                        hours.hour,
                        COALESCE(hourly_volume.trade_count, 0) as trade_count,
                        COALESCE(hourly_volume.volume_usd, 0) as volume_usd
                    FROM hours
                    LEFT JOIN hourly_volume ON hours.hour = hourly_volume.trade_hour
                    ORDER BY hours.hour
                """)

                volume_history = []
                
                for row in cursor.fetchall():
                    try:
                        if row[0] is None:
                            continue

                        dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                        timestamp = int(dt.timestamp() * 1000)
                        
                        volume = round(float(row[2] if row[2] is not None else 0), 2)
                        volume_history.append([timestamp, volume])
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error processing row {row}: {e}")
                        continue

                return {
                    "volume_history": volume_history
                }

        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return {
                "volume_history": []
            }
