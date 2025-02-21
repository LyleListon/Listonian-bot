"""
Entry point script that ensures proper async initialization with Python 3.12+
"""
import logging
import asyncio
import sys
import os
from pathlib import Path

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def init_and_run():
    """Initialize and run the bot with proper async handling."""
    try:
        # Import eventlet patch first
        from arbitrage_bot.utils.eventlet_patch import manager, run_with_eventlet, async_init
        
        # Initialize eventlet with proper error handling
        try:
            await async_init()
            if not manager._initialized:
                raise RuntimeError("Failed to initialize eventlet manager")
            logger.info("Successfully initialized eventlet")
        except Exception as e:
            logger.error("Failed to initialize eventlet: %s", str(e), exc_info=True)
            raise

        # Import main after eventlet setup
        try:
            import main
            logger.info("Successfully imported main module")
        except Exception as e:
            logger.error("Failed to import main module: %s", str(e), exc_info=True)
            raise
        
        # Run main with proper async context
        try:
            if hasattr(main, 'async_main'):
                logger.info("Running async main")
                await run_with_eventlet(main.async_main())
            else:
                # Fallback to running sync main in executor
                logger.info("Running sync main in executor")
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, main.main)
        except Exception as e:
            logger.error("Failed to run main: %s", str(e), exc_info=True)
            raise

    except Exception as e:
        logger.error("Failed to start bot: %s", str(e), exc_info=True)
        raise
    finally:
        if 'manager' in locals() and manager is not None:
            try:
                await manager.async_cleanup()
                logger.info("Successfully cleaned up eventlet manager")
            except Exception as e:
                logger.error("Failed to cleanup eventlet manager: %s", str(e), exc_info=True)

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
