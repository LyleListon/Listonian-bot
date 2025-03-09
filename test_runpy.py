"""
Test running modules directly using runpy.
"""

import os
import sys
import runpy
import pytest
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def run_module(module_path):
    """Run a module directly."""
    logger.info(f"Running module: {module_path}")
    try:
        # Add project root to Python path
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            
        # Run module
        namespace = runpy.run_path(module_path)
        logger.info(f"Module namespace keys: {list(namespace.keys())}")
        return namespace
    except Exception as e:
        logger.error(f"Failed to run module {module_path}: {e}")
        raise

def test_web3_manager():
    """Test running web3_manager module."""
    module_path = os.path.join(
        'arbitrage_bot', 'core', 'web3', 'web3_manager.py'
    )
    namespace = run_module(module_path)
    
    # Verify module contents
    assert 'Web3Manager' in namespace
    Web3Manager = namespace['Web3Manager']
    
    # Create instance
    manager = Web3Manager()
    assert manager is not None
    logger.info("Created Web3Manager instance")

def test_distribution_manager():
    """Test running distribution manager module."""
    module_path = os.path.join(
        'arbitrage_bot', 'core', 'distribution', 'manager.py'
    )
    namespace = run_module(module_path)
    
    # Verify module contents
    assert 'DistributionManager' in namespace
    DistributionManager = namespace['DistributionManager']
    
    # Get Web3Manager
    web3_path = os.path.join(
        'arbitrage_bot', 'core', 'web3', 'web3_manager.py'
    )
    web3_namespace = run_module(web3_path)
    Web3Manager = web3_namespace['Web3Manager']
    
    # Create instances
    web3_manager = Web3Manager()
    dist_manager = DistributionManager(web3_manager)
    assert dist_manager is not None
    assert dist_manager.web3_manager is web3_manager
    logger.info("Created DistributionManager instance")

if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=DEBUG", __file__])