"""Test configuration and shared fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from web3 import Web3
from arbitrage_bot.core.web3.web3_manager import Web3Manager

@pytest.fixture
def mock_eth():
    """Create mock eth object."""
    eth = AsyncMock()
    eth.chain_id = 8453
    eth.get_block = AsyncMock(return_value={'baseFeePerGas': 1000000000})
    eth.max_priority_fee = 100000000
    eth.get_contract = AsyncMock()
    eth.call_contract_function = AsyncMock()
    return eth

@pytest.fixture
def mock_w3(mock_eth):
    """Create mock Web3 instance."""
    w3 = MagicMock()
    w3.eth = mock_eth
    w3.to_checksum_address = Web3.to_checksum_address
    w3.to_wei = Web3.to_wei
    return w3

@pytest.fixture
def web3_config():
    """Create test Web3 configuration."""
    return {
        'web3': {
            'chain_id': 8453,  # Base chain ID
            'wallet_key': '0x' + '1' * 64,  # Mock private key
            'providers': {
                'primary': 'http://localhost:8545',  # Mock RPC endpoint
                'backup': []
            }
        }
    }

@pytest.fixture
async def web3_manager(web3_config, mock_w3):
    """Create Web3Manager instance for testing."""
    manager = Web3Manager(web3_config)
    manager.w3 = mock_w3
    manager.initialized = True
    
    # Mock contract loading
    async def mock_get_contract(*args, **kwargs):
        contract = AsyncMock()
        contract.functions = MagicMock()
        contract.functions.getReserves = AsyncMock(return_value=[10**18, 10**6, 0])  # Mock liquidity
        contract.functions.token0 = AsyncMock(return_value="0x4200000000000000000000000000000000000006")
        contract.functions.getPair = AsyncMock(return_value="0x1234567890123456789012345678901234567890")
        return contract
    
    manager.get_contract = mock_get_contract
    manager._load_abi = AsyncMock(return_value={})
    
    return manager

@pytest.fixture
def weth_address():
    """WETH token address on Base."""
    return "0x4200000000000000000000000000000000000006"

@pytest.fixture
def usdc_address():
    """USDC token address on Base."""
    return "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

@pytest.fixture
def test_addresses():
    """Common test addresses."""
    return {
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "USDT": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
    }

@pytest.fixture
def sushiswap_config():
    """Create test configuration for Sushiswap."""
    return {
        "name": "Sushiswap",
        "version": "v2",
        "factory": "0x71524B4f93c58fcbF659783284E38825f0622859",
        "router": "0x6BDED42c6DA8FD5E8147f8E45D437fBf146A3999",
        "fee": 3000,
        "enabled": True,
        "min_liquidity_usd": 10000,
        "weth_address": "0x4200000000000000000000000000000000000006"
    }