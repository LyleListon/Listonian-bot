"""
Test using asyncio test utilities.
"""

import os
import sys
import pytest
import logging
import asyncio
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def web3_manager():
    """Create a mock Web3Manager instance."""
    from arbitrage_bot.core.web3.web3_manager import Web3Manager
    
    # Create mock
    manager = Mock(spec=Web3Manager)
    manager.get_balance = AsyncMock(return_value=Decimal('1.0'))
    manager.wallet_address = "0x1234567890123456789012345678901234567890"
    manager.w3 = Mock()
    manager.w3.to_wei = lambda x, _: int(float(x) * 10**18)
    manager.send_transaction = AsyncMock(return_value="0xmocked_tx_hash")
    
    return manager

@pytest.fixture
async def distribution_manager(web3_manager):
    """Create a DistributionManager instance."""
    from arbitrage_bot.core.distribution.manager import DistributionManager
    
    # Create instance
    manager = DistributionManager(web3_manager)
    success = await manager.initialize()
    assert success, "Failed to initialize distribution manager"
    
    yield manager
    
    await manager.cleanup()

@pytest.mark.asyncio
async def test_web3_manager_balance(web3_manager):
    """Test Web3Manager balance retrieval."""
    balance = await web3_manager.get_balance()
    assert balance == Decimal('1.0')
    logger.info(f"Got balance: {balance}")

@pytest.mark.asyncio
async def test_web3_manager_transaction(web3_manager):
    """Test Web3Manager transaction sending."""
    tx_hash = await web3_manager.send_transaction({})
    assert tx_hash == "0xmocked_tx_hash"
    logger.info(f"Got transaction hash: {tx_hash}")

@pytest.mark.asyncio
async def test_distribution_manager_initialization(distribution_manager):
    """Test DistributionManager initialization."""
    assert distribution_manager is not None
    assert distribution_manager.initialized
    logger.info("Distribution manager initialized")

@pytest.mark.asyncio
async def test_distribution_manager_balance(distribution_manager):
    """Test DistributionManager balance check."""
    balance = await distribution_manager.get_balance()
    assert balance == Decimal('1.0')
    logger.info(f"Got balance: {balance}")

@pytest.mark.asyncio
async def test_distribution_manager_profit(distribution_manager):
    """Test DistributionManager profit distribution."""
    success = await distribution_manager.distribute_profits(Decimal('0.5'))
    assert success
    logger.info("Distributed profits successfully")

@pytest.mark.asyncio
async def test_distribution_manager_cleanup(distribution_manager):
    """Test DistributionManager cleanup."""
    await distribution_manager.cleanup()
    assert not distribution_manager.initialized
    logger.info("Distribution manager cleaned up")

if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=DEBUG", __file__])