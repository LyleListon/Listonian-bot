"""Integration tests for Flash Loan and Flashbots combined functionality."""

# Standard library imports
import asyncio
import pytest
from decimal import Decimal
from typing import Dict, Any
from web3 import Web3

from arbitrage_bot.core.web3.web3_manager import Web3Manager
from arbitrage_bot.core.web3.flashbots_manager import FlashbotsManager
from arbitrage_bot.core.dex.dex_manager import DexManager
from arbitrage_bot.core.flash_loan_manager import FlashLoanManager, create_flash_loan_manager

# Mark test file with pytest markers
pytestmark = [pytest.mark.integration, pytest.mark.flashbots, pytest.mark.flash_loan]

# Test configuration
TEST_CONFIG = {
    'use_flashbots': True,
    'flash_loans': {
        'enabled': True,
        'min_profit_basis_points': 100,  # 1% minimum profit
        'max_trade_size': '0.5'  # 0.5 ETH max trade size
    },
    'dexes': {
        'baseswap': {
            'enabled': True,
            'version': 'v2',
            'router_address': '0x327Df1E6de05895d2ab08513aaDD9313Fe505F36',
            'factory_address': '0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB'
        },
        'pancakeswap': {
            'enabled': True,
            'version': 'v3',
            'router_address': '0x678Aa4bF4E210cf2166753e054d5b7c31cc7fa86',
            'factory_address': '0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865'
        }
    },
    'tokens': {
        'WETH': {
            'address': '0x4200000000000000000000000000000000000006',
            'decimals': 18
        },
        'USDC': {
            'address': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
            'decimals': 6
        }
    }
}

@pytest.fixture
async def web3_manager():
    """Create Web3Manager instance."""
    manager = Web3Manager(
        provider_url="https://base.llamarpc.com",
        chain_id=8453,               # Base chain ID
        private_key="0x1234...",     # Test private key, will be replaced in CI/CD
        wallet_address="0x1234...",  # Test wallet address, will be replaced in CI/CD
        flashbots_enabled=True,
        flashbots_relay_url="https://relay.flashbots.net"
    )
    await manager.connect()
    return manager

@pytest.fixture
async def dex_manager(web3_manager):
    """Create DexManager instance."""
    manager = DexManager(web3_manager, TEST_CONFIG)
    await manager.initialize()
    return manager

@pytest.fixture
async def flash_loan_manager(web3_manager):
    """Create FlashLoanManager instance."""
    manager = await create_flash_loan_manager(
        web3_manager=web3_manager,
        config=TEST_CONFIG
    )
    return manager

@pytest.mark.asyncio
async def test_flash_loan_manager_initialization(flash_loan_manager):
    """Test flash loan manager initialization."""
    assert flash_loan_manager is not None
    assert flash_loan_manager.web3_manager is not None
    assert flash_loan_manager.config is not None
    
    # Check config values
    assert flash_loan_manager.min_profit_bps == 100
    assert flash_loan_manager.max_trade_size > 0
    
    # Optional test, might not be initialized in test environment
    if flash_loan_manager.initialized:
        assert flash_loan_manager.arbitrage_contract is not None

@pytest.mark.asyncio
async def test_flashbots_arbitrage_integration(web3_manager, flash_loan_manager):
    """Test flash loan arbitrage via Flashbots."""
    # Skip if either component is not initialized
    if not flash_loan_manager.initialized or not hasattr(web3_manager, 'flashbots_manager'):
        pytest.skip("Flash loan manager or Flashbots manager not initialized")
        
    # Parameters for flash loan arbitrage
    weth_address = TEST_CONFIG['tokens']['WETH']['address']
    amount = Web3.to_wei(0.1, 'ether')  # 0.1 ETH
    min_profit = Web3.to_wei(0.001, 'ether')  # 0.001 ETH min profit
    
    # Execute flash loan arbitrage via Flashbots
    result = await flash_loan_manager.execute_flashbots_arbitrage(
        token_in=weth_address,
        token_out=weth_address,
        amount=amount,
        buy_dex='baseswap',
        sell_dex='pancakeswap',
        min_profit=min_profit
    )
    
    # Verify result
    assert result is not None
    # May be skipped due to insufficient profit or other constraints
    if result.get('status') == 'submitted':
        assert 'bundle_id' in result
    else:
        assert 'reason' in result

@pytest.mark.asyncio
async def test_integrated_arbitrage_execution(dex_manager):
    """Test integrated arbitrage execution with flash loans and Flashbots."""
    # Parameters for arbitrage
    weth_address = TEST_CONFIG['tokens']['WETH']['address']
    amount = Web3.to_wei(0.1, 'ether')  # 0.1 ETH
    min_profit = Web3.to_wei(0.001, 'ether')  # 0.001 ETH min profit
    
    # Execute arbitrage (should use flash loans and Flashbots if both enabled)
    result = await dex_manager.execute_arbitrage(
        token_address=weth_address,
        amount=amount,
        buy_dex='baseswap',
        sell_dex='pancakeswap',
        min_profit=min_profit
    )
    
    # Verify result
    assert result is not None
    assert 'status' in result
    
    # Check if flash loans were used (depends on config)
    if dex_manager.use_flash_loans and dex_manager.use_flashbots:
        if result['status'] == 'submitted':
            assert 'bundle_id' in result
        elif result['status'] == 'error':
            assert 'reason' in result