"""Initialize memory bank."""

import asyncio
import json
import logging
import os
from datetime import datetime

from arbitrage_bot.core.memory.bank import create_memory_bank

logger = logging.getLogger(__name__)

async def init_memory():
    """Initialize memory bank with production configuration."""
    logger.info("Initializing memory bank...")
    
    # Load memory config
    config_path = os.path.join('configs', 'memory_config.json')
    with open(config_path) as f:
        config = json.load(f)
    
    # Create and initialize memory bank
    memory_bank = await create_memory_bank(config)
    
    # Initialize market data status
    market_data = {
        'status': {
            'last_update': datetime.now().timestamp(),
            'active_pairs': 0,
            'total_volume_24h': 0.0,
            'total_opportunities': 0,
            'average_profit': 0.0
        }
    }
    await memory_bank.store('status', market_data, 'market_data')
    logger.info("Initialized market_data status")
    
    # Initialize transactions status
    transactions = {
        'status': {
            'last_update': datetime.now().timestamp(),
            'total_trades': 0,
            'successful_trades': 0,
            'total_profit': 0.0,
            'average_gas': 0
        }
    }
    await memory_bank.store('status', transactions, 'transactions')
    logger.info("Initialized transactions status")
    
    # Initialize analytics status
    analytics = {
        'status': {
            'last_update': datetime.now().timestamp(),
            'success_rate': 0.0,
            'profit_per_trade': 0.0,
            'gas_efficiency': 0.0,
            'opportunity_hit_rate': 0.0
        }
    }
    await memory_bank.store('status', analytics, 'analytics')
    logger.info("Initialized analytics status")
    
    # Initialize storage status
    storage = {
        'status': {
            'last_update': datetime.now().timestamp(),
            'total_size': 0,
            'item_count': 0,
            'last_backup': datetime.now().timestamp()
        }
    }
    await memory_bank.store('storage_status', storage, 'storage')
    logger.info("Initialized storage status")
    
    # Log initialization stats
    stats = await memory_bank.get_memory_stats()
    logger.info("Memory bank initialized with statistics:")
    logger.info(f"- Total entries: {stats.total_entries}")
    logger.info(f"- Total size: {stats.total_size_bytes} bytes")
    logger.info(f"- Categories: {list(stats.categories.keys())}")
    
    logger.info("Memory bank initialization complete")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_memory())
