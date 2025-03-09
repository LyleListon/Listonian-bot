"""Tests for the multi-path arbitrage path finder."""

import pytest
import asyncio
from typing import Dict, List, Any
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock

from arbitrage_bot.core.path_finder import PathFinder, ArbitragePath, create_path_finder
from web3 import Web3

# Test constants
TEST_TOKENS = {
    'WETH': '0x4200000000000000000000000000000000000006',
    'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F'
}

@pytest.fixture
def mock_dex():
    """Create a mock DEX instance."""
    dex = AsyncMock()
    
    # Mock supports_token to always return True
    dex.supports_token = AsyncMock(return_value=True)
    
    # Mock get_amount_out to return a reasonable amount
    async def mock_get_amount_out(token_in, token_out, amount_in):
        # Simulate 0.3% fee and random price movement
        return int(amount_in * 0.997)
    
    dex.get_amount_out = AsyncMock(side_effect=mock_get_amount_out)
    
    # Mock estimate_swap_gas to return a standard gas amount
    dex.estimate_swap_gas = AsyncMock(return_value=150000)
    
    # Mock get_pairs_for_token to return some standard pairs
    async def mock_get_pairs(token):
        pairs = [
            (TEST_TOKENS['WETH'], TEST_TOKENS['USDC']),
            (TEST_TOKENS['WETH'], TEST_TOKENS['USDT']),
            (TEST_TOKENS['USDC'], TEST_TOKENS['DAI']),
            (TEST_TOKENS['USDT'], TEST_TOKENS['DAI'])
        ]
        return [pair for pair in pairs if token.lower() in (pair[0].lower(), pair[1].lower())]
    
    dex.get_pairs_for_token = AsyncMock(side_effect=mock_get_pairs)
    
    # Mock build_swap_transaction
    dex.build_swap_transaction = AsyncMock(return_value={
        'to': '0x1234567890123456789012345678901234567890',
        'data': '0x1234',
        'value': 0,
        'gas': 300000
    })
    
    return dex

@pytest.fixture
def mock_dex_manager(mock_dex):
    """Create a mock DexManager instance."""
    manager = MagicMock()
    
    # Setup mock dexes
    dexes = {
        'baseswap': mock_dex,
        'rocketswap': mock_dex,
        'pancakeswap': mock_dex
    }
    
    # Mock get_enabled_dexes to return our mock dexes
    manager.get_enabled_dexes = MagicMock(return_value=dexes)
    
    # Mock get_dex to return a specific mock dex
    manager.get_dex = MagicMock(side_effect=lambda name: dexes.get(name))
    
    return manager

@pytest.fixture
def mock_web3_manager():
    """Create a mock Web3Manager instance."""
    manager = MagicMock()
    
    # Mock wallet address
    manager.wallet_address = '0x1234567890123456789012345678901234567890'
    
    # Mock w3 object with eth module
    manager.w3 = MagicMock()
    manager.w3.eth = MagicMock()
    manager.w3.eth.block_number = 1000000
    
    # Mock get_block method
    async def mock_get_block(block_identifier):
        return {
            "baseFeePerGas": 10**9,  # 1 GWEI
            "gasLimit": 30000000
        }
    
    manager.get_block = AsyncMock(side_effect=mock_get_block)
    
    return manager

@pytest.fixture
def path_finder(mock_dex_manager, mock_web3_manager):
    """Create a PathFinder instance with mocks."""
    config = {
        "max_path_length": 3,
        "max_hops_per_dex": 2,
        "max_paths_to_check": 10,
        "min_profit_threshold": 0,
        "token_whitelist": [
            TEST_TOKENS['WETH'].lower(),
            TEST_TOKENS['USDC'].lower(),
            TEST_TOKENS['USDT'].lower(),
            TEST_TOKENS['DAI'].lower()
        ],
        "common_tokens": [
            TEST_TOKENS['WETH'].lower(),
            TEST_TOKENS['USDC'].lower()
        ]
    }
    
    finder = PathFinder(
        dex_manager=mock_dex_manager,
        web3_manager=mock_web3_manager,
        config=config
    )
    
    return finder

@pytest.mark.asyncio
async def test_arbitrage_path_creation():
    """Test creating an ArbitragePath."""
    path = ArbitragePath(
        input_token=TEST_TOKENS['WETH'],
        output_token=TEST_TOKENS['WETH'],  # Circular path
        amount_in=Web3.to_wei(1, 'ether')
    )
    
    # Add steps to the path
    path.add_step(
        dex_name="baseswap",
        token_in=TEST_TOKENS['WETH'],
        token_out=TEST_TOKENS['USDC'],
        amount_in=Web3.to_wei(1, 'ether'),
        amount_out=2000 * 10**6,  # 2000 USDC
        gas_estimate=150000
    )
    
    path.add_step(
        dex_name="pancakeswap",
        token_in=TEST_TOKENS['USDC'],
        token_out=TEST_TOKENS['WETH'],
        amount_in=2000 * 10**6,
        amount_out=Web3.to_wei(1.02, 'ether'),  # 1.02 WETH (profit)
        gas_estimate=150000
    )
    
    # Calculate profit with gas price of 10 GWEI
    profit = path.calculate_profit(gas_price=10**10)
    
    # 1.02 ETH - 1 ETH - gas cost
    expected_profit = Web3.to_wei(0.02, 'ether') - (300000 * 10**10)
    
    assert path.estimated_output == Web3.to_wei(1.02, 'ether')
    assert path.estimated_gas_cost == 300000
    assert profit == expected_profit
    assert path.estimated_profit == expected_profit
    
    # Check path dictionary representation
    path_dict = path.to_dict()
    assert path_dict["input_token"] == TEST_TOKENS['WETH']
    assert path_dict["output_token"] == TEST_TOKENS['WETH']
    assert path_dict["amount_in"] == Web3.to_wei(1, 'ether')
    assert len(path_dict["route"]) == 2
    assert path_dict["route"][0]["dex"] == "baseswap"
    assert path_dict["route"][1]["dex"] == "pancakeswap"

@pytest.mark.asyncio
async def test_find_arbitrage_opportunities(path_finder):
    """Test finding arbitrage opportunities."""
    # Setup Flashbots manager mock
    path_finder.web3_manager.flashbots_manager = AsyncMock()
    
    # Find opportunities
    opportunities = await path_finder.find_arbitrage_opportunities(
        input_token=TEST_TOKENS['WETH'],
        output_token=TEST_TOKENS['WETH'],  # Circular path
        amount_in=Web3.to_wei(1, 'ether')
    )
    
    # We should get some paths
    assert len(opportunities) > 0
    
    # Verify each path is properly formed
    for path in opportunities:
        # Each path should have at least one step
        assert len(path.route) > 0
        
        # Path should start with WETH and end with WETH
        assert path.input_token == TEST_TOKENS['WETH']
        assert path.output_token == TEST_TOKENS['WETH']
        
        # Check route consistency
        prev_token_out = None
        for step in path.route:
            # First step should start with input token
            if prev_token_out is None:
                assert step["token_in"] == TEST_TOKENS['WETH']
            else:
                # Subsequent steps should connect tokens
                assert step["token_in"] == prev_token_out
            
            prev_token_out = step["token_out"]
            
        # Last step should end with output token
        assert path.route[-1]["token_out"] == TEST_TOKENS['WETH']

@pytest.mark.asyncio
async def test_simulate_arbitrage_path(path_finder):
    """Test simulating an arbitrage path."""
    # Create a test path
    path = ArbitragePath(
        input_token=TEST_TOKENS['WETH'],
        output_token=TEST_TOKENS['WETH'],
        amount_in=Web3.to_wei(1, 'ether')
    )
    
    # Add steps to the path
    path.add_step(
        dex_name="baseswap",
        token_in=TEST_TOKENS['WETH'],
        token_out=TEST_TOKENS['USDC'],
        amount_in=Web3.to_wei(1, 'ether'),
        amount_out=2000 * 10**6,
        gas_estimate=150000
    )
    
    path.add_step(
        dex_name="pancakeswap",
        token_in=TEST_TOKENS['USDC'],
        token_out=TEST_TOKENS['WETH'],
        amount_in=2000 * 10**6,
        amount_out=Web3.to_wei(1.02, 'ether'),
        gas_estimate=150000
    )
    
    # Mock Flashbots manager methods
    path_finder.web3_manager.flashbots_manager = AsyncMock()
    path_finder.web3_manager.flashbots_manager.create_bundle = AsyncMock(return_value="bundle-id-123")
    path_finder.web3_manager.flashbots_manager.simulate_bundle = AsyncMock(return_value={"gasUsed": 300000})
    path_finder.web3_manager.flashbots_manager.calculate_bundle_profit = AsyncMock(
        return_value={"net_profit_wei": Web3.to_wei(0.01, 'ether'), "profitable": True}
    )
    
    # Simulate the path
    simulation = await path_finder.simulate_arbitrage_path(path)
    
    # Verify simulation result
    assert simulation["success"] is True
    assert "bundle_id" in simulation
    assert "simulation" in simulation
    assert "profit" in simulation
    assert simulation["bundle_id"] == "bundle-id-123"

@pytest.mark.asyncio
async def test_execute_arbitrage_path(path_finder):
    """Test executing an arbitrage path."""
    # Create a test path
    path = ArbitragePath(
        input_token=TEST_TOKENS['WETH'],
        output_token=TEST_TOKENS['WETH'],
        amount_in=Web3.to_wei(1, 'ether')
    )
    
    # Add steps to the path
    path.add_step(
        dex_name="baseswap",
        token_in=TEST_TOKENS['WETH'],
        token_out=TEST_TOKENS['USDC'],
        amount_in=Web3.to_wei(1, 'ether'),
        amount_out=2000 * 10**6,
        gas_estimate=150000
    )
    
    path.add_step(
        dex_name="pancakeswap",
        token_in=TEST_TOKENS['USDC'],
        token_out=TEST_TOKENS['WETH'],
        amount_in=2000 * 10**6,
        amount_out=Web3.to_wei(1.02, 'ether'),
        gas_estimate=150000
    )
    
    # Mock Flashbots manager methods
    path_finder.web3_manager.flashbots_manager = AsyncMock()
    path_finder.web3_manager.flashbots_manager.create_bundle = AsyncMock(return_value="bundle-id-123")
    path_finder.web3_manager.flashbots_manager.simulate_bundle = AsyncMock(return_value={"gasUsed": 300000})
    path_finder.web3_manager.flashbots_manager.calculate_bundle_profit = AsyncMock(
        return_value={"net_profit_wei": Web3.to_wei(0.01, 'ether'), "profitable": True}
    )
    path_finder.web3_manager.flashbots_manager.submit_bundle = AsyncMock(
        return_value={"submit_result": "success"}
    )
    path_finder.web3_manager.flashbots_manager.validate_and_submit_bundle = AsyncMock(
        return_value={"validation": {"success": True}, "submit_result": "success"}
    )
    
    # Execute the path
    result = await path_finder.execute_arbitrage_path(
        path,
        use_flashbots=True,
        min_profit=Web3.to_wei(0.005, 'ether')  # 0.005 ETH profit required
    )
    
    # Verify execution result
    assert result["success"] is True
    assert result["status"] == "submitted"
    assert "bundle_id" in result
    assert "profit" in result
    assert result["bundle_id"] == "bundle-id-123"

@pytest.mark.asyncio
async def test_create_path_finder():
    """Test creating a PathFinder using the factory function."""
    # Mock dependencies
    with patch('arbitrage_bot.core.path_finder.DexManager') as mock_dex_manager_class, \
         patch('arbitrage_bot.core.path_finder.Web3Manager') as mock_web3_manager_class, \
         patch('arbitrage_bot.core.path_finder.load_config') as mock_load_config:
        
        # Setup mock returns
        mock_dex_manager = AsyncMock()
        mock_dex_manager_class.return_value = mock_dex_manager
        mock_web3_manager = AsyncMock()
        mock_web3_manager_class.return_value = mock_web3_manager
        mock_load_config.return_value = {
            "provider_url": "https://base.llamarpc.com",
            "chain_id": 8453,
            "private_key": "0x1234...",
            "wallet_address": "0x1234...",
            "path_finding": {
                "max_path_length": 3,
                "token_whitelist": [TEST_TOKENS['WETH'], TEST_TOKENS['USDC']]
            }
        }
        
        # Create PathFinder using factory function
        path_finder = await create_path_finder()
        
        # Verify PathFinder was created
        assert isinstance(path_finder, PathFinder)
        assert path_finder.dex_manager == mock_dex_manager
        assert path_finder.web3_manager == mock_web3_manager
        assert path_finder.max_path_length == 3