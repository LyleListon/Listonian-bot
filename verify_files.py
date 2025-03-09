"""
Verify package files and their contents.
"""

import os
import sys
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def read_file(path):
    """Read and return file contents."""
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def verify_package():
    """Verify package structure and contents."""
    cwd = os.getcwd()
    logger.info(f"Current working directory: {cwd}")
    
    required_files = [
        'arbitrage_bot/__init__.py',
        'arbitrage_bot/core/__init__.py',
        'arbitrage_bot/core/web3/__init__.py',
        'arbitrage_bot/core/web3/web3_manager.py',
        'arbitrage_bot/core/distribution/__init__.py',
        'arbitrage_bot/core/distribution/manager.py',
    ]
    
    logger.info("\nChecking package structure:")
    all_exist = True
    for filepath in required_files:
        full_path = os.path.join(cwd, filepath)
        if os.path.exists(full_path):
            logger.info(f"\nFound {filepath}")
            logger.info("Contents:")
            logger.info("-" * 40)
            logger.info(read_file(full_path))
            logger.info("-" * 40)
        else:
            logger.error(f"Missing {filepath}")
            all_exist = False
    
    if all_exist:
        logger.info("\nAll required files exist!")
    else:
        logger.error("\nSome files are missing!")
        
    logger.info("\nPYTHONPATH:")
    python_path = os.environ.get('PYTHONPATH', 'Not set')
    logger.info(python_path)
    
    logger.info("\nPython sys.path:")
    for p in sys.path:
        logger.info(f"  {p}")

if __name__ == "__main__":
    verify_package()