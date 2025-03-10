"""
Production Runner

This script runs the arbitrage bot in production mode with:
- Live blockchain data
- Real flash loan execution
- Flashbots MEV protection
- Multi-path optimization
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, Optional
import signal
import sys

from .core.arbitrage_executor import create_arbitrage_executor
from .utils.config_loader import load_production_config
from .utils.async_manager import AsyncLock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('arbitrage.log')
    ]
)
logger = logging.getLogger(__name__)

class ProductionRunner:
    """Runs the arbitrage bot in production."""

    def __init__(self):
        """Initialize the production runner."""
        self.executor = None
        self.config = None
        self.running = False
        self._stop_lock = AsyncLock()
        self._stats_lock = AsyncLock()

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.stop())

    async def initialize(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the production system.

        Args:
            config: Optional configuration dictionary
        """
        try:
            logger.info("Initializing production system...")

            # Load configuration
            self.config = config or load_production_config()

            # Set default intervals if not provided
            self.config.setdefault('scan_interval', 5.0)  # 5 seconds between scans
            self.config.setdefault('stats_interval', 30.0)  # 30 seconds between stats

            # Create executor
            self.executor = await create_arbitrage_executor(config=self.config)

            # Log initialization
            logger.info(
                "Production system initialized:\n"
                f"- Min profit: {self.executor.min_profit_wei} wei\n"
                f"- Max paths: {self.executor.path_finder.max_paths_to_check}\n"
                f"- Max path length: {self.executor.path_finder.max_path_length}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize production system: {e}")
            raise

    async def start(self):
        """Start the production system."""
        if self.running:
            logger.warning("Production system already running")
            return

        if not self.executor:
            raise RuntimeError("System not initialized. Call initialize() first.")

        try:
            logger.info("Starting production system...")
            self.running = True

            # Start monitoring task
            asyncio.create_task(self._monitor_stats())

            # Discover pools for each DEX
            token_addresses = [info['address'] for info in self.config['tokens'].values()]
            for dex_name in self.executor.path_finder.dex_manager.dexes:
                logger.info(f"Discovering pools for {dex_name}...")
                await self.executor.path_finder.dex_manager.discover_pools(
                    dex_name=dex_name,
                    token_addresses=token_addresses
                )

            # Get initial token list
            tokens = await self.executor.path_finder.dex_manager.get_supported_tokens()
            logger.info(f"Monitoring {len(tokens)} tokens for arbitrage opportunities")

            # Main arbitrage loop
            while self.running:
                try:
                    # Check each token as entry point
                    for token in tokens:
                        if not self.running:
                            break

                        # Find and execute arbitrage
                        result = await self.executor.find_and_execute_arbitrage(
                            token_address=token,
                            amount_wei=self.config.get('scan_amount_wei', 1000000000000000000),  # 1 ETH default
                            max_paths=self.config.get('max_paths', 5)
                        )

                        if result['success']:
                            profit = result['net_profit']
                            logger.info(
                                f"Successfully executed arbitrage:\n"
                                f"- Token: {token}\n"
                                f"- Profit: {profit} wei\n"
                                f"- Gas used: {result['gas_used']}\n"
                                f"- Gas price: {result['gas_price']} wei"
                            )

                    # Brief delay between scans
                    await asyncio.sleep(self.config['scan_interval'])

                except Exception as e:
                    logger.error(f"Error in arbitrage loop: {e}")
                    await asyncio.sleep(5.0)  # Longer delay after error

        except Exception as e:
            logger.error(f"Critical error in production system: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop the production system."""
        async with self._stop_lock:
            if not self.running:
                return

            logger.info("Stopping production system...")
            self.running = False

            if self.executor:
                # Log final statistics
                stats = self.executor.get_statistics()
                logger.info(
                    "Final statistics:\n"
                    f"- Total executions: {stats['total_executions']}\n"
                    f"- Successful executions: {stats['successful_executions']}\n"
                    f"- Success rate: {stats['success_rate']:.2%}\n"
                    f"- Total profit: {stats['total_profit_wei']} wei\n"
                    f"- Max profit: {stats['max_profit_wei']} wei"
                )

            logger.info("Production system stopped")

    async def _monitor_stats(self):
        """Monitor and log system statistics."""
        while self.running:
            try:
                async with self._stats_lock:
                    stats = self.executor.get_statistics()
                    logger.info(
                        "System statistics:\n"
                        f"- Success rate: {stats['success_rate']:.2%}\n"
                        f"- Total profit: {stats['total_profit_wei']} wei\n"
                        f"- Paths analyzed: {stats['path_finder_stats']['total_paths_analyzed']}"
                    )

                await asyncio.sleep(self.config['stats_interval'])

            except Exception as e:
                logger.error(f"Error monitoring stats: {e}")
                await asyncio.sleep(60)  # 1 minute delay after error

async def main():
    """Main entry point for production system."""
    runner = ProductionRunner()
    
    try:
        await runner.initialize()
        await runner.start()
    
    except Exception as e:
        logger.error(f"Production system failed: {e}")
        sys.exit(1)
    
    finally:
        await runner.stop()

if __name__ == "__main__":
    asyncio.run(main())