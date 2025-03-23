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

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/arbitrage.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def init_and_run():
    """Initialize and run the bot with proper async handling."""
    try:
        # Import async manager first
        from arbitrage_bot.utils.async_manager import manager, run_with_async_context, async_init
        from arbitrage_bot.utils.config_loader import load_config
        from arbitrage_bot.core.arbitrage import (
            BaseArbitrageSystem,
            DiscoveryManager,
            EnhancedExecutionManager,
            AnalyticsManager,
            MarketDataProvider
        )
        
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
            market_data_provider = MarketDataProvider()
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
            await run_with_async_context(bot.start())
            
        except Exception as e:
            logger.error("Failed to start ArbitrageBot: %s", str(e), exc_info=True)
            raise

    except Exception as e:
        logger.error("Failed to start bot: %s", str(e), exc_info=True)
        raise
    finally:
        if 'manager' in locals() and manager is not None:
            try:
                await manager.async_cleanup()
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
        sys.exit(1)
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
