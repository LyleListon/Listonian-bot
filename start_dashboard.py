"""
Start the dashboard application with proper async initialization.
"""

# Import essential modules first
import sys
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

try:
    # Import and initialize async manager
    from arbitrage_bot.utils.async_manager import manager, async_init
    logger.info("Initializing async event loop...")
    
    # Now import other modules
    import os
    import json
    from pathlib import Path
    from arbitrage_bot.dashboard.run import async_main

    async def init_and_run():
        """Initialize and run the dashboard."""
        try:
            # Initialize async manager
            await async_init()
            if not manager._initialized:
                raise RuntimeError("Failed to initialize async manager")
            logger.info("Successfully initialized async event loop")

            # Load config
            config_path = Path(__file__).parent / 'configs' / 'config.json'
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    if 'dashboard' in config:
                        port = config['dashboard'].get('port', 5001)
                        os.environ['DASHBOARD_PORT'] = str(port)

            # Start dashboard
            logger.info("Starting dashboard...")
            await async_main()

        except Exception as e:
            logger.error("Failed to start dashboard: %s", str(e))
            raise
        finally:
            if manager._initialized:
                await manager.async_cleanup()
                logger.info("Successfully cleaned up async manager")

    if __name__ == "__main__":
        try:
            # Create and configure event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Enable debug mode in development
            if os.getenv('ENV') == 'development':
                loop.set_debug(True)
                loop.slow_callback_duration = 5.0  # 5 seconds
            
            # Run the dashboard
            loop.run_until_complete(init_and_run())
            
        except KeyboardInterrupt:
            logger.info("Dashboard stopped by user")
        except Exception as e:
            logger.error("Critical error: %s", str(e))
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
                logger.error("Error during cleanup: %s", str(e))
                sys.exit(1)

except Exception as e:
    logger.error("Critical initialization error: %s", str(e))
    sys.exit(1)
