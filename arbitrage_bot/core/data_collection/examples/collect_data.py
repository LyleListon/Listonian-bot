"""Example script demonstrating data collection system usage."""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import Dict, Any

from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.core.dex.dex_manager import create_dex_manager
from arbitrage_bot.core.data_collection.coordinator import DataCollectionCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_path = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
    with open(config_path) as f:
        return yaml.safe_load(f)

async def main():
    """Run data collection example."""
    try:
        # Load configuration
        config = await load_config()
        logger.info("Configuration loaded")
        
        # Initialize managers
        web3_manager = await create_web3_manager()
        await web3_manager.connect()
        logger.info("Web3 manager initialized")
        
        dex_manager = await create_dex_manager(web3_manager)
        logger.info("DEX manager initialized")
        
        # Create data collection coordinator
        coordinator = DataCollectionCoordinator(config)
        success = await coordinator.initialize(web3_manager, dex_manager)
        if not success:
            raise RuntimeError("Failed to initialize data collection system")
        logger.info("Data collection system initialized")
        
        # Start collection
        await coordinator.start()
        logger.info("Data collection started")
        
        # Monitor system status
        try:
            while True:
                # Get and log system status
                status = await coordinator.get_status()
                logger.info("System Status:")
                logger.info(f"  Collectors: {status['collectors']}")
                logger.info(f"  Storage: {status['storage']}")
                
                # Get recent data
                network_data = await coordinator.get_recent_data('network', minutes=1)
                pool_data = await coordinator.get_recent_data('pool', minutes=1)
                
                logger.info(f"Recent Data Points:")
                logger.info(f"  Network: {len(network_data)} points")
                logger.info(f"  Pool: {len(pool_data)} points")
                
                # Wait before next status check
                await asyncio.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("Stopping data collection...")
            await coordinator.stop()
            logger.info("Data collection stopped")
            
    except Exception as e:
        logger.error(f"Error in data collection example: {e}")
        raise
    finally:
        # Cleanup
        if 'web3_manager' in locals():
            await web3_manager.disconnect()
        logger.info("Example completed")

def run_example():
    """Run the example."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Example interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise

if __name__ == '__main__':
    run_example()

"""
Example Usage:

1. Basic usage:
   ```python
   python -m arbitrage_bot.core.data_collection.examples.collect_data
   ```

2. With custom config:
   ```python
   import yaml
   from arbitrage_bot.core.data_collection.coordinator import DataCollectionCoordinator
   
   # Load custom config
   with open('my_config.yaml') as f:
       config = yaml.safe_load(f)
   
   # Initialize system
   coordinator = DataCollectionCoordinator(config)
   await coordinator.initialize(web3_manager, dex_manager)
   
   # Start collection
   await coordinator.start()
   
   # Get recent data
   data = await coordinator.get_recent_data(minutes=5)
   print(f"Collected {len(data)} data points")
   ```

3. With custom processing:
   ```python
   from arbitrage_bot.core.data_collection.processors.normalizer import DataNormalizer
   
   # Create custom processor
   class MyProcessor(DataNormalizer):
       async def process(self, data):
           # Custom processing logic
           processed = await super().process(data)
           processed['my_feature'] = calculate_feature(processed)
           return processed
   
   # Add to pipeline
   coordinator.processors['my_processor'] = MyProcessor(config)
   ```

4. With monitoring:
   ```python
   # Monitor system status
   while True:
       status = await coordinator.get_status()
       if status['storage']['errors'] > 0:
           print("Storage errors detected!")
       await asyncio.sleep(60)
   ```
"""