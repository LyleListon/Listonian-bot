"""
Entry point script that ensures proper async initialization with Python 3.12+
"""
import logging
import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Load config to get logging level
import json
import argparse # Import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Run the Listonian Arbitrage Bot.")
parser.add_argument('--env', default='production', help='Environment to run in (production, verification)')
args = parser.parse_args()

# Determine the .env file to load
env_file = f".env.{args.env}"

# Load environment variables
from scripts.load_env import load_env
if not load_env(env_file):
    logger.error(f"Failed to load environment variables from {env_file}")
    sys.exit(1)

# Load config to get logging level
with open('config.json') as f:
    config = json.load(f)
log_level = getattr(logging, config['logging']['level'].upper())

# Configure logging first
logging.basicConfig(
    level=log_level,
    force=True,  # Override any existing loggers
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/arbitrage.log'),
        logging.StreamHandler()
    ]
)

# Set higher logging level for noisy libraries
logging.getLogger("web3").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
async def init_and_run():
    """Initialize and run the bot with proper async handling."""
    bot = None
    try:
        # Import async manager first
        from arbitrage_bot.utils.async_manager import manager, run_with_async_context, async_init
        from arbitrage_bot.utils.config_loader import load_config
        from arbitrage_bot.core.arbitrage import (
            BaseArbitrageSystem,
            DiscoveryManager,
            EnhancedExecutionManager,
            AnalyticsManager
        )
        from arbitrage_bot.core.arbitrage.enhanced_market_data_provider import EnhancedMarketDataProvider
        
        # Initialize async manager with proper error handling
        try:
            await async_init()
            if not manager._initialized:
                raise RuntimeError("Failed to initialize async manager")
            logger.info("Successfully initialized async event loop")
        except Exception as e:
            logger.error("Failed to initialize async manager: %s", str(e), exc_info=True)
            raise
        
        # Initialize bot components
        try:
            # Load configuration
            config = load_config()
            
            # Initialize components
            logger.info("Initializing bot components...")
            
            # Create market data provider
            market_data_provider = EnhancedMarketDataProvider(config)
            await market_data_provider.initialize()
            logger.info("Market data provider initialized")
            
            # Create analytics manager
            analytics_manager = AnalyticsManager()
            await analytics_manager.initialize()
            logger.info("Analytics manager initialized")
            
            # Create discovery manager
            discovery_manager = DiscoveryManager()
            await discovery_manager.initialize()
            logger.info("Discovery manager initialized")
            
            # Create execution manager
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
            start_task = asyncio.create_task(bot.start())
            
            # Wait for shutdown signal
            try:
                while True:
                    await asyncio.sleep(1)
                    # Check if start_task failed
                    if start_task.done() and start_task.exception() is not None:
                        raise start_task.exception()
            except asyncio.CancelledError:
                logger.info("Received shutdown signal")
                # Cancel start_task if it's still running
                if not start_task.done():
                    start_task.cancel()
                    try:
                        await start_task
                    except asyncio.CancelledError:
                        pass
                raise
            
        except Exception as e:
            logger.error("Failed to start ArbitrageBot: %s", str(e), exc_info=True)
            raise

    except Exception as e:
        logger.error("Failed to start bot: %s", str(e), exc_info=True)
        raise
    finally:
        # Stop bot first if it was created
        if bot is not None:
            try:
                await bot.stop()
                logger.info("Successfully stopped ArbitrageBot")
            except Exception as e:
                logger.error("Error stopping bot: %s", str(e), exc_info=True)
        
        # Then cleanup async manager
        if 'manager' in locals() and manager is not None:
            try:
                await manager.async_cleanup()
                logger.info("Successfully cleaned up async manager")
            except Exception as e:
                logger.error("Failed to cleanup async manager: %s", str(e), exc_info=True)

def main():
    """Entry point that sets up and runs the async loop."""
    loop = None
    try:
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Only enable debug mode in development
        if os.getenv('ENV') == 'development':
            loop.set_debug(True)
            # Set a higher threshold for slow callback warnings
            loop.slow_callback_duration = 5.0  # 5 seconds
        
        # Create task for init_and_run
        task = loop.create_task(init_and_run())
        
        try:
            # Run until complete or interrupted
            loop.run_until_complete(task)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            # Cancel the task
            logger.info("Cancelling main task...")
            task.cancel()
            # Allow the main run_until_complete(task) call on line 177
            # to handle the cancelled task, which will trigger the
            # finally block in init_and_run for cleanup.
        
    except Exception as e:
        logger.error("Critical error: %s", str(e), exc_info=True)
        sys.exit(1)
    finally:
        # Ensure the loop is closed
        try:
            if loop is not None:
                pending = asyncio.all_tasks(loop)
                if pending:
                    logger.info("Cancelling %d pending tasks", len(pending))
                    for task in pending:
                        task.cancel()
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
                if loop.is_running():
                    loop.stop()
                if not loop.is_closed():
                    loop.close()
                logger.info("Successfully closed event loop")
        except Exception as e:
            logger.error("Error during cleanup: %s", str(e), exc_info=True)

if __name__ == "__main__":
    main()
