"""
Verify package structure.
"""

import os
import sys
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def verify_file(path):
    """Verify file exists and print its contents."""
    if os.path.exists(path):
        logger.info(f"Found {path}")
        try:
            with open(path, 'r') as f:
                logger.info("Contents:")
                logger.info("-" * 40)
                logger.info(f.read())
                logger.info("-" * 40)
        except Exception as e:
            logger.error(f"Error reading {path}: {e}")
    else:
        logger.error(f"Missing {path}")

def main():
    """Main verification function."""
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    logger.info("Python path:")
    for p in sys.path:
        logger.info(f"  {p}")

    # Verify package structure
    files_to_check = [
        'arbitrage_bot/__init__.py',
        'arbitrage_bot/core/__init__.py',
        'arbitrage_bot/core/web3/__init__.py',
        'arbitrage_bot/core/web3/web3_manager.py',
        'arbitrage_bot/core/distribution/__init__.py',
        'arbitrage_bot/core/distribution/manager.py'
    ]

    logger.info("\nVerifying package structure:")
    for file_path in files_to_check:
        verify_file(file_path)

if __name__ == "__main__":
    main()