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
    EnhancedMarketDataProvider,
    MemoryManager,
    MLSystem,
    Web3Manager,
    FlashbotsProvider,
    async_manager,
    run_with_async_context,
    async_init
)

from arbitrage_bot.utils.config_loader import load_config

async def create_ml_system(config):
    """Create and initialize the ML system."""
    try:
        ml_system = MLSystem(
            model_path=config.get("model_path", "models/default"),
            confidence_threshold=config.get("confidence_threshold", 0.85),
            update_interval=config.get("update_interval", 3600)
        )
        await ml_system.initialize()
        return ml_system
    except Exception as e:
        logger.error("Failed to create ML system: %s", str(e), exc_info=True)
        raise

async def create_web3_manager(config):
    """Create and initialize the Web3 manager."""
    try:
        web3_manager = Web3Manager(
            config)
        await web3_manager.initialize()
        return web3_manager
    except Exception as e:
        logger.error("Failed to create Web3 manager: %s", str(e), exc_info=True)
        raise

async def create_flashbots_provider(web3_manager, config):
    """Create and initialize the Flashbots provider."""
    try:
        # Get Web3 instance and create account
        web3 = web3_manager.w3
        account = web3.eth.account.from_key(config.get("private_key"))
        
        flashbots_provider = FlashbotsProvider(
            web3=web3,
            config=config,
            account=account
        )
        await flashbots_provider.initialize()
        return flashbots_provider
    except Exception as e:
        logger.error("Failed to create Flashbots provider: %s", str(e), exc_info=True)
        raise

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
            market_data_provider = EnhancedMarketDataProvider()
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
                logger.info("Received shutdown signal, cleaning up...")
                try:
                    # Stop the bot first
                    await bot.stop()
                    
                    # Cancel all pending tasks
                    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
                    for task in tasks:
                        task.cancel()
                    
                    # Wait for all tasks to complete
                    await asyncio.gather(*tasks, return_exceptions=True)
                    logger.info("Successfully cleaned up all tasks")
                except Exception as e:
                    logger.error("Error during task cleanup: %s", str(e), exc_info=True)
            
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
                # Cancel all pending tasks
                tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
                for task in tasks:
                    task.cancel()
                
                # Wait for tasks to complete with a timeout
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                
                loop.stop()
            if not loop.is_closed():
                loop.close()
            logger.info("Successfully closed event loop")
        except Exception as e:
            logger.error("Error during cleanup: %s", str(e), exc_info=True)

if __name__ == "__main__":
    main()
