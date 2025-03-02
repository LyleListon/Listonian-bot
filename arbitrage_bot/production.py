#!/usr/bin/env python
"""
Listonian Arbitrage Bot Production System

This is the main entry point for the production arbitrage system.
It initializes all components and starts the arbitrage processes.
"""

import os
import sys
import asyncio
import logging
import argparse
import time
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/production.log")
    ]
)

logger = logging.getLogger("production")


async def run_legacy_system(config_path: str):
    """Run the legacy arbitrage system."""
    from arbitrage_bot.core.arbitrage_monitor import ArbitrageMonitor
    from arbitrage_bot.utils.config_loader import load_config
    from arbitrage_bot.core.web3.web3_manager import create_web3_manager
    from arbitrage_bot.core.dex.dex_manager import create_dex_manager
    
    logger.info("Starting legacy arbitrage system")
    
    # Load configuration
    config = load_config(config_path)
    
    # Create web3 manager
    web3_manager = await create_web3_manager(config)
    
    # Create dex manager
    dex_manager = await create_dex_manager(web3_manager, config)
    
    # Create arbitrage monitor
    arbitrage_monitor = ArbitrageMonitor(
        dex_manager=dex_manager,
        web3_manager=web3_manager,
        config=config
    )
    
    logger.info("Starting arbitrage monitor")
    await arbitrage_monitor.start()
    
    try:
        # Run forever
        while True:
            await asyncio.sleep(60)
            logger.info("Arbitrage system running...")
    except KeyboardInterrupt:
        logger.info("Stopping arbitrage system")
        await arbitrage_monitor.stop()
    except Exception as e:
        logger.error(f"Error in arbitrage system: {e}")
        await arbitrage_monitor.stop()
        raise


async def run_new_system(config_path: str):
    """Run the new refactored arbitrage system."""
    from arbitrage_bot.core.arbitrage.factory import create_arbitrage_system_from_config
    
    logger.info("Starting new arbitrage system")
    
    # Create arbitrage system from config
    arbitrage_system = await create_arbitrage_system_from_config(config_path)
    
    logger.info("Starting arbitrage system")
    await arbitrage_system.start()
    
    try:
        # Run forever
        while True:
            await asyncio.sleep(60)
            # Every hour, get and log performance metrics
            if (int(time.time()) % 3600) < 60:  # Within first minute of the hour
                metrics = await arbitrage_system.get_performance_metrics()
                logger.info(f"Performance metrics: {json.dumps(metrics, indent=2)}")
            else:
                logger.info("Arbitrage system running...")
    except KeyboardInterrupt:
        logger.info("Stopping arbitrage system")
        await arbitrage_system.stop()
    except Exception as e:
        logger.error(f"Error in arbitrage system: {e}")
        await arbitrage_system.stop()
        raise


def create_directories():
    """Create necessary directories if they don't exist."""
    directories = ["logs", "data", "data/analytics"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)


async def main():
    """Main entry point for the arbitrage system."""
    parser = argparse.ArgumentParser(description="Listonian Arbitrage Bot")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/production_config.json",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Run legacy arbitrage system"
    )
    args = parser.parse_args()
    
    create_directories()
    
    logger.info("Listonian Arbitrage Bot starting")
    logger.info(f"Using configuration: {args.config}")
    
    if args.legacy:
        await run_legacy_system(args.config)
    else:
        await run_new_system(args.config)


if __name__ == "__main__":
    # Required for asyncio on Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arbitrage Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error in Arbitrage Bot: {e}", exc_info=True)
        sys.exit(1)