"""
Test importing the distribution manager module.
"""

import os
import sys
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def check_package_structure():
    """Check if all required files exist."""
    required_files = [
        'arbitrage_bot/__init__.py',
        'arbitrage_bot/core/__init__.py',
        'arbitrage_bot/core/web3/__init__.py',
        'arbitrage_bot/core/web3/web3_manager.py',
        'arbitrage_bot/core/distribution/__init__.py',
        'arbitrage_bot/core/distribution/manager.py'
    ]
    
    logger.info("Checking package structure...")
    for file_path in required_files:
        if os.path.exists(file_path):
            logger.info(f"Found {file_path}")
        else:
            logger.error(f"Missing {file_path}")
            
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    logger.info("Python path:")
    for p in sys.path:
        logger.info(f"  {p}")

def main():
    """Run the import test."""
    try:
        check_package_structure()
        
        logger.info("Attempting to import Web3Manager...")
        from arbitrage_bot.core.web3.web3_manager import Web3Manager
        logger.info("Successfully imported Web3Manager")
        
        logger.info("Attempting to import DistributionManager...")
        from arbitrage_bot.core.distribution.manager import DistributionManager
        logger.info("Successfully imported DistributionManager")
        
        # Test creating instances
        logger.info("Testing class instantiation...")
        web3_manager = Web3Manager()
        dist_manager = DistributionManager(web3_manager)
        logger.info("Successfully created instances")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error(f"Error details:\n{traceback.format_exc()}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Error details:\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()