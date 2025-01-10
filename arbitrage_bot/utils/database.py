"""Database utilities."""

import logging
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


async def init_db(testing: bool = False) -> "Database":
    """Initialize database connection.

    Args:
        testing (bool, optional): Whether to use mock database for testing.

    Returns:
        Database: Database instance
    """
    db = Database(testing=testing)
    await db.connect()
    return db


class Database:
    """Database connection and operations."""

    def __init__(self, testing: bool = False):
        """
        Initialize database connection.

        Args:
            testing (bool, optional): Whether to use mock database for testing.
        """
        self.testing = testing
        self._client = None
        self._db = None
        self._trades = []  # In-memory storage for testing
        logger.info("Database connection initialized")

    async def connect(self):
        """Connect to database."""
        if not self.testing:
            try:
                # Connect to MongoDB
                self._client = AsyncIOMotorClient("mongodb://localhost:27017")
                self._db = self._client.arbitrage_bot
                await self._db.command("ping")
                logger.info("Connected to MongoDB")
            except ServerSelectionTimeoutError as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise

    async def save_trade(self, trade_data: Dict[str, Any]) -> str:
        """
        Save trade record.

        Args:
            trade_data (Dict[str, Any]): Trade data to save

        Returns:
            str: Trade ID
        """
        if self.testing:
            # Store in memory for testing
            self._trades.append(trade_data)
            return str(len(self._trades))

        try:
            if not self._db:
                await self.connect()

            result = await self._db.trades.insert_one(trade_data)
            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            raise

    async def get_trades(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get trade records.

        Args:
            query (Dict[str, Any]): Query parameters

        Returns:
            List[Dict[str, Any]]: Trade records
        """
        if self.testing:
            # Filter in-memory trades
            return [
                t for t in self._trades if all(t.get(k) == v for k, v in query.items())
            ]

        try:
            if not self._db:
                await self.connect()

            cursor = self._db.trades.find(query)
            return await cursor.to_list(length=None)

        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []

    async def update_trade(self, trade_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update trade record.

        Args:
            trade_id (str): Trade ID
            update_data (Dict[str, Any]): Data to update

        Returns:
            bool: True if successful
        """
        if self.testing:
            # Update in-memory trade
            try:
                idx = int(trade_id) - 1
                if 0 <= idx < len(self._trades):
                    self._trades[idx].update(update_data)
                    return True
            except ValueError:
                pass
            return False

        try:
            if not self._db:
                await self.connect()

            result = await self._db.trades.update_one(
                {"_id": trade_id}, {"$set": update_data}
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Failed to update trade: {e}")
            return False

    async def delete_trade(self, trade_id: str) -> bool:
        """
        Delete trade record.

        Args:
            trade_id (str): Trade ID

        Returns:
            bool: True if successful
        """
        if self.testing:
            # Delete from in-memory storage
            try:
                idx = int(trade_id) - 1
                if 0 <= idx < len(self._trades):
                    del self._trades[idx]
                    return True
            except ValueError:
                pass
            return False

        try:
            if not self._db:
                await self.connect()

            result = await self._db.trades.delete_one({"_id": trade_id})
            return result.deleted_count > 0

        except Exception as e:
            logger.error(f"Failed to delete trade: {e}")
            return False

    async def close(self):
        """Close database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Closed database connection")
