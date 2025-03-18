"""
Test environment validation and configuration.

This module verifies:
1. Python version and environment
2. Required package installations
3. Core module imports
4. Async runtime configuration
"""

import sys
import pytest
import logging
import asyncio
from typing import Dict, Any, List
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_python_environment() -> None:
    """Test Python version and environment configuration."""
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python path: {sys.path}")
    
    # Verify Python version meets requirements
    assert sys.version_info >= (3, 12), "Python 3.12+ is required"
    
    # Verify pytest installation
    pytest_version = pytest.__version__
    logger.info(f"Pytest version: {pytest_version}")
    major, minor = map(int, pytest_version.split('.')[:2])
    assert (major, minor) >= (7, 0), "Pytest 7.0+ is required"

def test_required_packages() -> None:
    """Test required package installations."""
    required_packages = [
        'web3',
        'fastapi',
        'uvicorn',
        'pydantic',
        'python-dotenv',
        'aiohttp'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"Successfully imported {package}")
        except ImportError as e:
            pytest.fail(f"Failed to import {package}: {e}")

def test_core_imports() -> None:
    """Test core module imports."""
    try:
        import arbitrage_bot
        logger.info("Successfully imported arbitrage_bot package")
        
        # Test critical module imports
        from arbitrage_bot.core.distribution.manager import DistributionManager
        from arbitrage_bot.core.web3.web3_manager import Web3Manager
        from arbitrage_bot.core.dex.dex_manager import DexManager
        
        logger.info("Successfully imported core modules")
    except ImportError as e:
        pytest.fail(f"Failed to import core module: {e}")

@pytest.mark.asyncio
async def test_async_runtime() -> None:
    """Test async runtime configuration."""
    try:
        # Verify event loop
        loop = asyncio.get_running_loop()
        assert loop.is_running(), "Event loop is not running"
        
        # Test basic async operation
        async def async_test() -> str:
            await asyncio.sleep(0.1)
            return "success"
        
        result = await async_test()
        assert result == "success", "Async runtime test failed"
        
        logger.info("Async runtime test passed")
    except Exception as e:
        pytest.fail(f"Async runtime test failed: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])