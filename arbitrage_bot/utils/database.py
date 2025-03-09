"""Database utilities."""

import os
import json
import logging
from json import JSONEncoder
from datetime import datetime
from decimal import Decimal

class DateTimeEncoder(JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'isoformat'):  # Handle other datetime-like objects
            return obj.isoformat()
        elif isinstance(obj, (Decimal, float)):
            return str(obj)  # Convert Decimal/float to string
        return super().default(obj)

import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

def init_db(testing: bool = False) -> "Database":
    """Initialize database connection."""
    return Database(testing=testing)

class Database:
    """Database connection and operations."""

    def __init__(self, testing: bool = None):
        """Initialize database connection."""
        self.testing = testing if testing is not None else os.getenv('TESTING', '').lower() == 'true'
        self._conn = None
        self._trades = []  # In-memory storage for testing
        if not self.testing:
            self.connect()
        logger.info("Database initialized")

    def connect(self):
        """Connect to database."""
        if not self.testing:
            try:
                # Create data directory if it doesn't exist
                Path('data').mkdir(exist_ok=True)
                
                # Connect to SQLite database
                self._conn = sqlite3.connect('data/trades.db')
                self._conn.row_factory = sqlite3.Row
                
                # Create tables if they don't exist
                self._conn.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                ''')
                self._conn.execute('''
                    CREATE TABLE IF NOT EXISTS metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                ''')
                self._conn.commit()
                logger.info("Connected to SQLite database")
            except Exception as e:
                logger.warning(f"SQLite initialization failed, falling back to in-memory storage: {e}")
                self.testing = True
                self._conn = None

    async def save_trade(self, trade_data: Dict[str, Any]) -> str:
        """Save trade record."""
        if self.testing:
            self._trades.append(trade_data)
            return str(len(self._trades))

        try:
            if not self._conn:
                self.connect()

            # Add timestamp if not present
            if 'timestamp' not in trade_data:
                trade_data['timestamp'] = datetime.utcnow().isoformat()

            # Convert dict to JSON string
            data_json = json.dumps(trade_data, cls=DateTimeEncoder)
            
            cursor = self._conn.execute(
                'INSERT INTO trades (data, timestamp) VALUES (?, ?)',
                (data_json, trade_data['timestamp'] if isinstance(trade_data['timestamp'], str) else trade_data['timestamp'].isoformat())
            )
            self._conn.commit()
            return str(cursor.lastrowid)

        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            raise

    async def get_trades(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get trade records."""
        if self.testing:
            return [
                t for t in self._trades if all(t.get(k) == v for k, v in query.items())
            ]

        try:
            if not self._conn:
                self.connect()

            cursor = self._conn.execute('SELECT data FROM trades')
            trades = []
            for row in cursor:
                trade = json.loads(row['data'])
                if all(trade.get(k) == v for k, v in query.items()):
                    trades.append(trade)
            return trades

        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []

    async def update_trade(self, trade_id: str, update_data: Dict[str, Any]) -> bool:
        """Update trade record."""
        if self.testing:
            try:
                idx = int(trade_id) - 1
                if 0 <= idx < len(self._trades):
                    self._trades[idx].update(update_data)
                    return True
            except ValueError:
                pass
            return False

        try:
            if not self._conn:
                self.connect()

            # Get existing trade
            cursor = self._conn.execute('SELECT data FROM trades WHERE id = ?', (trade_id,))
            row = cursor.fetchone()
            if not row:
                return False

            # Update trade data
            trade_data = json.loads(row['data'])
            trade_data.update(update_data)
            data_json = json.dumps(trade_data, cls=DateTimeEncoder)

            # Save updated trade
            self._conn.execute(
                'UPDATE trades SET data = ? WHERE id = ?',
                (data_json, trade_id)
            )
            self._conn.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to update trade: {e}")
            return False

    async def delete_trade(self, trade_id: str) -> bool:
        """Delete trade record."""
        if self.testing:
            try:
                idx = int(trade_id) - 1
                if 0 <= idx < len(self._trades):
                    del self._trades[idx]
                    return True
            except ValueError:
                pass
            return False

        try:
            if not self._conn:
                self.connect()

            cursor = self._conn.execute('DELETE FROM trades WHERE id = ?', (trade_id,))
            self._conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to delete trade: {e}")
            return False

    async def get_metrics(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get historical metrics."""
        if self.testing:
            return []

        try:
            if not self._conn:
                self.connect()

            if query and 'timestamp' in query:
                # Convert datetime objects to ISO format strings
                if isinstance(query['timestamp'], dict):
                    if '$gte' in query['timestamp']:
                        query['timestamp']['$gte'] = query['timestamp']['$gte'].isoformat()
                    if '$lte' in query['timestamp']:
                        query['timestamp']['$lte'] = query['timestamp']['$lte'].isoformat()

            cursor = self._conn.execute('SELECT data FROM metrics')
            metrics = []
            for row in cursor:
                metric = json.loads(row['data'])
                if query:
                    # Apply query filters
                    if all(
                        k not in metric or metric[k] == v
                        for k, v in query.items()
                        if k != 'timestamp'
                    ):
                        if 'timestamp' in query:
                            ts = metric.get('timestamp')
                            if ts:
                                if '$gte' in query['timestamp'] and ts < query['timestamp']['$gte']:
                                    continue
                                if '$lte' in query['timestamp'] and ts > query['timestamp']['$lte']:
                                    continue
                        metrics.append(metric)
                else:
                    metrics.append(metric)
            return metrics

        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []

    async def save_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Save metrics snapshot."""
        if self.testing:
            return True

        try:
            if not self._conn:
                self.connect()

            # Add timestamp if not present
            if 'timestamp' not in metrics_data:
                metrics_data['timestamp'] = datetime.utcnow().isoformat()

            # Convert dict to JSON string using DateTimeEncoder
            try:
                # First convert to string to catch any serialization issues
                data_json = json.dumps(metrics_data, cls=DateTimeEncoder)
                # Then parse back to ensure valid JSON
                json.loads(data_json)
            except TypeError as e:
                # If serialization fails, try manual datetime conversion
                def convert_datetime(obj):
                    if isinstance(obj, dict):
                        return {k: convert_datetime(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_datetime(x) for x in obj]
                    elif isinstance(obj, datetime):
                        return obj.isoformat()
                    elif hasattr(obj, 'isoformat'):  # Handle other datetime-like objects
                        return obj.isoformat()
                    return obj

                metrics_data = convert_datetime(metrics_data)
                data_json = json.dumps(metrics_data)
            
            self._conn.execute(
                'INSERT INTO metrics (data, timestamp) VALUES (?, ?)',
                (data_json, metrics_data['timestamp'])
            )
            self._conn.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
            return False

    async def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Closed database connection")
