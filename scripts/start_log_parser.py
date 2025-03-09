"""
Start Log Parser Bridge

Script to start the Log Parser Bridge that connects log files to the dashboard.
"""

import asyncio
import logging
from pathlib import Path

from arbitrage_bot.core import (
    LogParserBridge,
    ConfigLoader,
    OpportunityTracker
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point."""
    try:
        # Load configuration
        config_path = Path('configs/log_parser_config.yaml')
        config = await ConfigLoader.load_config(config_path)
        
        # Create OpportunityTracker
        opportunity_tracker = OpportunityTracker()
        
        # Create and start Log Parser Bridge
        parser = LogParserBridge(
            log_dir=Path(config.watch_directory),
            opportunity_tracker=opportunity_tracker,
            update_frequency=config.update_frequency,
            max_batch_size=config.max_batch_size
        )
        
        logger.info(
            f"Starting Log Parser Bridge\n"
            f"Watching directory: {config.watch_directory}\n"
            f"Update frequency: {config.update_frequency}s\n"
            f"Max batch size: {config.max_batch_size}"
        )
        
        await parser.start()
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
                
                # Log some stats periodically
                stats = opportunity_tracker.get_stats()
                logger.info(
                    f"Stats: {stats['total_opportunities']} opportunities, "
                    f"{stats['successful_executions']} successful, "
                    f"${stats['total_profit']:.2f} total profit"
                )
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await parser.stop()
            
    except Exception as e:
        logger.error(f"Error running Log Parser Bridge: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Clean exit on Ctrl+C
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        exit(1)