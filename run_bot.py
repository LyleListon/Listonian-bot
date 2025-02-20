"""
Entry point script that ensures proper async initialization with Python 3.12+
"""
import logging
import asyncio
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
        # Import and initialize eventlet patch first
        from arbitrage_bot.utils.eventlet_patch import manager, run_with_eventlet
        await manager.initialize()

        # Import main after eventlet setup
        import main
        
        # Run main with proper async context
        if hasattr(main, 'async_main'):
            await run_with_eventlet(main.async_main())
        else:
            # Fallback to running sync main in executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, main.main)

    except Exception as e:
        logger.error("Failed to start bot", exc_info=True)
        raise
    finally:
        await manager.cleanup()

def main():
    """Entry point that sets up and runs the async loop."""
    try:
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Enable debug mode
        loop.set_debug(True)
        
        # Run the async initialization and main loop
        loop.run_until_complete(init_and_run())
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error("Critical error", exc_info=True)
        raise
    finally:
        # Ensure the loop is closed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.stop()
            loop.close()
        except Exception as e:
            logger.error("Error during cleanup", exc_info=True)

if __name__ == "__main__":
    main()
