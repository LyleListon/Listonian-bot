import aiosqlite
from typing import List, Dict, Any

DB_PATH = "data/trades.db"

async def get_recent_opportunities() -> List[Dict[str, Any]]:
    query = "SELECT * FROM opportunities ORDER BY timestamp DESC LIMIT 10"
    results = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append(dict(row))
    return results

async def get_trade_history() -> List[Dict[str, Any]]:
    query = "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 100"
    results = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append(dict(row))
    return results