"""
Main entry point for the arbitrage bot.
"""

import asyncio
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/arbitrage.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in os.sys.path:
    os.sys.path.insert(0, project_root)

from arbitrage_bot import (
    BaseArbitrageSystem,
    DiscoveryManager,
    EnhancedExecutionManager,
    AnalyticsManager,
    MarketDataProvider,
    MemoryManager,
    MLSystem,
    Web3Manager,
    FlashbotsProvider,
    async_manager,
    run_with_async_context,
    async_init
)

from arbitrage_bot.utils.config_loader import load_config

async def init_and_run():
    """Initialize and run the bot with proper async handling."""
    try:
        # Initialize async manager
        try:
            await async_init()
            if not async_manager._initialized:
                raise RuntimeError("Failed to initialize async manager")
            logger.info("Successfully initialized async event loop")
        except Exception as e:
            logger.error("Failed to initialize async manager: %s", str(e), exc_info=True)
            raise

        # Initialize bot components
        try:
            # Load configuration
            config = load_config()
            
            # Create required directories
            Path("logs").mkdir(exist_ok=True)
            Path("memory-bank/trades").mkdir(parents=True, exist_ok=True)
            Path("memory-bank/metrics").mkdir(parents=True, exist_ok=True)
            Path("memory-bank/state").mkdir(parents=True, exist_ok=True)
            
            logger.info("Initializing bot components...")
            
            # Initialize memory manager first
            memory_manager = MemoryManager(
                storage_path="memory-bank",
                max_trade_history=config["memory_bank"]["max_trade_history"],
                backup_interval_hours=config["memory_bank"]["backup_interval_hours"]
            )
            await memory_manager.initialize()
            logger.info("Memory manager initialized")
            
            # Initialize market data provider
            market_data_provider = MarketDataProvider()
            await market_data_provider.initialize()
            logger.info("Market data provider initialized")
            
            # Initialize ML system
            ml_system = await create_ml_system(config["ml"])
            logger.info("ML system initialized")
            
            # Initialize Web3 and Flashbots
            web3_manager = await create_web3_manager(config["web3"])
            flashbots_provider = await create_flashbots_provider(
                web3_manager,
                config["flashbots"]
            )
            logger.info("Web3 and Flashbots initialized")
            
            # Initialize analytics manager
            analytics_manager = AnalyticsManager()
            await analytics_manager.initialize()
            logger.info("Analytics manager initialized")
            
            # Initialize discovery manager
            discovery_manager = DiscoveryManager()
            await discovery_manager.initialize()
            logger.info("Discovery manager initialized")
            
            # Initialize execution manager
            execution_manager = EnhancedExecutionManager()
            await execution_manager.initialize()
            logger.info("Execution manager initialized")
            
            # Create bot instance
            bot = BaseArbitrageSystem(
                discovery_manager=discovery_manager,
                execution_manager=execution_manager,
                analytics_manager=analytics_manager,
                market_data_provider=market_data_provider,
                config=config
            )
            
            logger.info("Successfully created ArbitrageBot")
            
            # Start the bot
            await run_with_async_context(bot.start())
            
            # Wait for shutdown signal
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                await bot.stop()
            
        except Exception as e:
            logger.error("Failed to start ArbitrageBot: %s", str(e), exc_info=True)
            raise

    except Exception as e:
        logger.error("Failed to start bot: %s", str(e), exc_info=True)
        raise
    finally:
        if 'async_manager' in locals() and async_manager is not None:
            try:
                await async_manager.async_cleanup()
                logger.info("Successfully cleaned up async manager")
            except Exception as e:
                logger.error("Failed to cleanup async manager: %s", str(e), exc_info=True)

def main():
    """Entry point that sets up and runs the async loop."""
    try:
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Only enable debug mode in development
        if os.getenv('ENV') == 'development':
            loop.set_debug(True)
            # Set a higher threshold for slow callback warnings
            loop.slow_callback_duration = 5.0  # 5 seconds
        
        # Run the async initialization and main loop
        loop.run_until_complete(init_and_run())
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error("Critical error: %s", str(e), exc_info=True)
        raise
    finally:
        # Ensure the loop is closed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.stop()
            if not loop.is_closed():
                loop.close()
            logger.info("Successfully closed event loop")
        except Exception as e:
            logger.error("Error during cleanup: %s", str(e), exc_info=True)

if __name__ == "__main__":
    main()
