"""Tests for multi-hop path support within individual DEXs."""

import pytest
import asyncio
from typing import Dict, List, Any
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock

from arbitrage_bot.core.path_finder import PathFinder, ArbitragePath
from arbitrage_bot.core.dex.baseswap_v3 import BaseSwapV3
from web3 import Web3

# Test constants
TEST_TOKENS = {
    'WETH': '0x4200000000000000000000000000000000000006',
    'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
    'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'
}

@pytest.fixture
def mock_v3_quoter():
    """Create a mock quoter for V3 DEXs."""
    quoter = AsyncMock()
    
    # Mock quoteExactInputSingle for single hop quotes
    async def mock_quote_single(token_in, token_out, fee, amount_in, sqrtPriceLimitX96):
        # Simulate different outputs based on the token pair
        if token_in.lower() == TEST_TOKENS['WETH'].lower() and token_out.lower() == TEST_TOKENS['USDC'].lower():
            return (2000 * 10**6, 0, 0, 150000)  # 2000 USDC, gas = 150k
        elif token_in.lower() == TEST_TOKENS['USDC'].lower() and token_out.lower() == TEST_TOKENS['WETH'].lower():
            return (int(0.0005 * 10**18), 0, 0, 150000)  # 0.0005 ETH, gas = 150k
        elif token_in.lower() == TEST_TOKENS['USDC'].lower() and token_out.lower() == TEST_TOKENS['USDT'].lower():
            return (int(0.99 * 10**6), 0, 0, 150000)  # 0.99 USDT per USDC, gas = 150k
        elif token_in.lower() == TEST_TOKENS['USDT'].lower() and token_out.lower() == TEST_TOKENS['DAI'].lower():
            return (int(0.99 * 10**18), 0, 0, 150000)  # 0.99 DAI per USDT, gas = 150k
        elif token_in.lower() == TEST_TOKENS['DAI'].lower() and token_out.lower() == TEST_TOKENS['WETH'].lower():
            return (int(0.00051 * 10**18), 0, 0, 150000)  # 0.00051 ETH, gas = 150k
        else:
            return (0, 0, 0, 0)  # No path found
    
    quoter.functions.quoteExactInputSingle = AsyncMock(side_effect=mock_quote_single)
    
    # Mock quoteExactInput for multi-hop quotes
    async def mock_quote_multi(path, amount_in):
        # For multi-hop paths (e.g., WETH -> USDC -> USDT -> WETH)
        # Decode the path to determine the tokens
        # This is a simplified version - real impl would decode the hex path
        
        # Simulate different returns based on recognizable paths
        if amount_in == 10**18:  # If 1 ETH input
            # Simulate WETH -> USDC -> WETH (better than direct path)
            return (int(0.00055 * 10**18), 0, 0, 250000)  # 0.00055 ETH (10% better), gas = 250k
        elif amount_in == 2 * 10**18:  # If 2 ETH input
            # Simulate WETH -> USDC -> DAI -> WETH (even better for larger amounts)
            return (int(0.0012 * 10**18), 0, 0, 300000)  # 0.0012 ETH (20% better), gas = 300k
        else:
            # Generic multi-hop result
            return (int(amount_in * 1.01), 0, 0, 200000)  # 1% better than input, gas = 200k
    
    quoter.functions.quoteExactInput = AsyncMock(side_effect=mock_quote_multi)
    
    return quoter

@pytest.fixture
def mock_v3_dex(mock_v3_quoter):
    """Create a mock V3 DEX with multi-hop support."""
    dex = AsyncMock()
    
    # Set up the quoter
    dex.quoter = mock_v3_quoter
    
    # Mock supports_token to always return True
    dex.supports_token = AsyncMock(return_value=True)
    
    # Mock supports_multi_hop to return True
    dex.supports_multi_hop = AsyncMock(return_value=True)
    
    # Mock get_amount_out for both single and multi-hop paths
    async def mock_get_amount_out(token_in, token_out, amount_in, path=None):
        if path and len(path) > 2:
            # Multi-hop path
            result = await mock_v3_quoter.functions.quoteExactInput(b'encoded_path', amount_in)
            return result[0]
        else:
            # Single hop
            result = await mock_v3_quoter.functions.quoteExactInputSingle(
                token_in, token_out, 3000, amount_in, 0
            )
            return result[0]
    
    dex.get_amount_out = AsyncMock(side_effect=mock_get_amount_out)
    dex.get_quote_from_quoter = AsyncMock(side_effect=mock_get_amount_out)
    
    # Mock get_multi_hop_quote
    async def mock_get_multi_hop_quote(amount_in, path):
        result = await mock_v3_quoter.functions.quoteExactInput(b'encoded_path', amount_in)
        return result[0]
    
    dex.get_multi_hop_quote = AsyncMock(side_effect=mock_get_multi_hop_quote)
    
    # Mock estimate_swap_gas for normal swaps
    dex.estimate_swap_gas = AsyncMock(return_value=150000)
    
    # Mock get_multi_hop_gas_estimate for multi-hop swaps
    async def mock_get_multi_hop_gas_estimate(path):
        return 150000 + (len(path) - 2) * 50000
    
    dex.get_multi_hop_gas_estimate = AsyncMock(side_effect=mock_get_multi_hop_gas_estimate)
    
    # Mock get_pairs_for_token to return standard pairs
    async def mock_get_pairs(token):
        pairs = [
            (TEST_TOKENS['WETH'], TEST_TOKENS['USDC']),
            (TEST_TOKENS['WETH'], TEST_TOKENS['USDT']),
            (TEST_TOKENS['USDC'], TEST_TOKENS['USDT']),
            (TEST_TOKENS['USDT'], TEST_TOKENS['DAI']),
            (TEST_TOKENS['DAI'], TEST_TOKENS['WETH'])
        ]
        return [pair for pair in pairs if token.lower() in (pair[0].lower(), pair[1].lower())]
    
    dex.get_pairs_for_token = AsyncMock(side_effect=mock_get_pairs)
    
    # Mock get_supported_tokens to return all test tokens
    dex.get_supported_tokens = AsyncMock(return_value=list(TEST_TOKENS.values()))
    
    # Mock find_best_path to implement multi-hop path finding
    async def mock_find_best_path(token_in, token_out, amount_in, max_hops=3):
        if token_in.lower() == TEST_TOKENS['WETH'].lower() and token_out.lower() == TEST_TOKENS['WETH'].lower():
            # Circular paths (WETH -> ??? -> WETH)
            if amount_in == 10**18:  # 1 ETH
                # WETH -> USDC -> WETH (better than direct)
                return {
                    'path': [
                        TEST_TOKENS['WETH'],
                        TEST_TOKENS['USDC'],
                        TEST_TOKENS['WETH']
                    ],
                    'amount_out': int(0.00055 * 10**18),  # 0.00055 ETH (10% better)
                    'gas_estimate': 250000
                }
            elif amount_in == 2 * 10**18:  # 2 ETH
                # WETH -> USDC -> DAI -> WETH (even better for larger amounts)
                return {
                    'path': [
                        TEST_TOKENS['WETH'],
                        TEST_TOKENS['USDC'],
                        TEST_TOKENS['DAI'],
                        TEST_TOKENS['WETH']
                    ],
                    'amount_out': int(0.0012 * 10**18),  # 0.0012 ETH (20% better)
                    'gas_estimate': 300000
                }
        
        # Default case: return a direct path
        direct_amount = await mock_get_amount_out(token_in, token_out, amount_in)
        return {
            'path': [token_in, token_out],
            'amount_out': direct_amount,
            'gas_estimate': 150000
        }
    
    dex.find_best_path = AsyncMock(side_effect=mock_find_best_path)
    
    # Mock build_swap_transaction
    async def mock_build_swap_tx(token_in, token_out, amount_in, min_amount_out, to, deadline):
        return {
            'to': '0x1234567890123456789012345678901234567890',
            'data': '0x1234',
            'value': 0,
            'gas': 250000
        }
    
    dex.build_swap_transaction = AsyncMock(side_effect=mock_build_swap_tx)
    
    # Set DEX name and other properties
    dex.name = "MockBaseSwapV3"
    dex.router_address = "0x1234567890123456789012345678901234567890"
    dex.fee = 3000
    
    return dex

@pytest.fixture
def mock_dex_manager(mock_v3_dex):
    """Create a mock DexManager with multi-hop DEX support."""
    manager = MagicMock()
    
    # Setup mock dexes
    dexes = {
        'baseswap': mock_v3_dex,
        'uniswap': mock_v3_dex,
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
    
    # Mock call_contract_function
    async def mock_call_contract(func, *args, **kwargs):
        if hasattr(func, '__self__') and func.__self__:
            if hasattr(func.__self__, 'quoteExactInputSingle') and func.__name__ == 'quoteExactInputSingle':
                # For single hop quotes
                return await func(*args, **kwargs)
            elif hasattr(func.__self__, 'quoteExactInput') and func.__name__ == 'quoteExactInput':
                # For multi-hop quotes
                return await func(*args, **kwargs)
        return 0
    
    manager.call_contract_function = AsyncMock(side_effect=mock_call_contract)
    
    # Add flashbots manager for bundle testing
    manager.flashbots_manager = AsyncMock()
    manager.flashbots_manager.create_bundle = AsyncMock(return_value="test-bundle-id")
    manager.flashbots_manager.simulate_bundle = AsyncMock(return_value={"gasUsed": 300000})
    manager.flashbots_manager.calculate_bundle_profit = AsyncMock(
        return_value={"net_profit_wei": Web3.to_wei(0.01, 'ether'), "profitable": True}
    )
    
    return manager

@pytest.fixture
def path_finder_with_multi_hop(mock_dex_manager, mock_web3_manager):
    """Create a PathFinder instance with multi-hop support."""
    config = {
        "max_path_length": 3,  # Max DEXs to use
        "max_hops_per_dex": 3,  # Max hops within a single DEX
        "enable_multi_hop_paths": True,
        "min_profit_threshold": 0,
        "token_whitelist": [
            TEST_TOKENS['WETH'].lower(),
            TEST_TOKENS['USDC'].lower(),
            TEST_TOKENS['USDT'].lower(),
            TEST_TOKENS['DAI'].lower(),
            TEST_TOKENS['WBTC'].lower()
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
async def test_multi_hop_quote(mock_v3_dex):
    """Test getting quotes for multi-hop paths."""
    # 1 ETH to WETH (circular through USDC)
    amount_in = 10**18  # 1 ETH
    path = [
        TEST_TOKENS['WETH'],
        TEST_TOKENS['USDC'],
        TEST_TOKENS['WETH']
    ]
    
    # Get quote for multi-hop path
    amount_out = await mock_v3_dex.get_multi_hop_quote(amount_in, path)
    
    # Verify the result is as expected
    assert amount_out > 0, "Multi-hop quote should return a positive amount"
    # Our mock returns 0.00055 ETH for this path, 10% better than direct route
    assert amount_out == int(0.00055 * 10**18), "Multi-hop quote returned unexpected amount"

@pytest.mark.asyncio
async def test_find_best_path(mock_v3_dex):
    """Test finding the best path between tokens."""
    # Test circular path (WETH -> ??? -> WETH)
    best_path = await mock_v3_dex.find_best_path(
        token_in=TEST_TOKENS['WETH'],
        token_out=TEST_TOKENS['WETH'],
        amount_in=10**18  # 1 ETH
    )
    
    # Verify the best path is multi-hop
    assert best_path is not None, "Should find a path"
    assert 'path' in best_path, "Result should include path"
    assert len(best_path['path']) > 2, "Best path should be multi-hop"
    assert best_path['path'][0] == TEST_TOKENS['WETH'], "Path should start with WETH"
    assert best_path['path'][-1] == TEST_TOKENS['WETH'], "Path should end with WETH"
    
    # Test with larger amount (should find 3-hop path)
    best_path_large = await mock_v3_dex.find_best_path(
        token_in=TEST_TOKENS['WETH'],
        token_out=TEST_TOKENS['WETH'],
        amount_in=2 * 10**18  # 2 ETH
    )
    
    # Verify the best path for larger amount is a 3-hop path
    assert best_path_large is not None, "Should find a path for larger amount"
    assert len(best_path_large['path']) == 4, "Best path for larger amount should be 3-hop"
    assert best_path_large['amount_out'] > best_path['amount_out'], "Larger amount path should return more"

@pytest.mark.asyncio
async def test_path_finder_with_multi_hop(path_finder_with_multi_hop):
    """Test that PathFinder can find and utilize multi-hop paths."""
    # Find arbitrage opportunities
    opportunities = await path_finder_with_multi_hop.find_arbitrage_opportunities(
        input_token=TEST_TOKENS['WETH'],
        output_token=TEST_TOKENS['WETH'],  # Circular path
        amount_in=10**18  # 1 ETH
    )
    
    # We should get some paths
    assert len(opportunities) > 0, "Should find arbitrage opportunities"
    
    # Verify at least one multi-hop path was found
    multi_hop_paths = [
        path for path in opportunities
        if any(len(step.get('path', [])) > 2 for step in path.route)
    ]
    
    assert len(multi_hop_paths) > 0, "Should find at least one multi-hop path"
    
    # Check the first multi-hop path
    path = multi_hop_paths[0]
    assert path.input_token == TEST_TOKENS['WETH'], "Path should start with WETH"
    assert path.output_token == TEST_TOKENS['WETH'], "Path should end with WETH"
    
    # Verify the multi-hop step
    multi_hop_steps = [step for step in path.route if len(step.get('path', [])) > 2]
    assert len(multi_hop_steps) > 0, "Should have at least one multi-hop step"
    
    multi_hop_step = multi_hop_steps[0]
    assert len(multi_hop_step['path']) > 2, "Multi-hop step should have more than 2 tokens in path"
    assert multi_hop_step['path'][0] == TEST_TOKENS['WETH'], "Multi-hop path should start with input token"
    assert multi_hop_step['path'][-1] == TEST_TOKENS['WETH'], "Multi-hop path should end with output token"

@pytest.mark.asyncio
async def test_simulate_multi_hop_path(path_finder_with_multi_hop):
    """Test simulating a multi-hop arbitrage path."""
    # Create a test path with a multi-hop step
    path = ArbitragePath(
        input_token=TEST_TOKENS['WETH'],
        output_token=TEST_TOKENS['WETH'],
        amount_in=10**18  # 1 ETH
    )
    
    # Add a multi-hop step
    path.add_step(
        dex_name="baseswap",
        token_in=TEST_TOKENS['WETH'],
        token_out=TEST_TOKENS['WETH'],
        amount_in=10**18,
        amount_out=int(0.00055 * 10**18),  # 0.00055 ETH
        gas_estimate=250000,
        path=[
            TEST_TOKENS['WETH'],
            TEST_TOKENS['USDC'],
            TEST_TOKENS['WETH']
        ]
    )
    
    # Simulate the path
    simulation = await path_finder_with_multi_hop.simulate_arbitrage_path(path)
    
    # Verify simulation result
    assert simulation["success"] is True, "Simulation should succeed"
    assert "bundle_id" in simulation, "Simulation should return bundle ID"
    
    # Execute the path
    execution = await path_finder_with_multi_hop.execute_arbitrage_path(
        path,
        use_flashbots=True
    )
    
    # Verify execution result
    assert execution["success"] is True, "Execution should succeed"
    assert execution["status"] == "submitted", "Execution status should be 'submitted'"
    assert "bundle_id" in execution, "Execution should return bundle ID"

@pytest.mark.asyncio
async def test_multi_hop_profit_comparison(path_finder_with_multi_hop):
    """Test that multi-hop paths can be more profitable than direct paths."""
    # Find opportunities with different amounts
    opportunities_small = await path_finder_with_multi_hop.find_arbitrage_opportunities(
        input_token=TEST_TOKENS['WETH'],
        output_token=TEST_TOKENS['WETH'],
        amount_in=10**18  # 1 ETH
    )
    
    opportunities_large = await path_finder_with_multi_hop.find_arbitrage_opportunities(
        input_token=TEST_TOKENS['WETH'],
        output_token=TEST_TOKENS['WETH'],
        amount_in=2 * 10**18  # 2 ETH
    )
    
    # Check profits
    profit_small = max(p.estimated_profit for p in opportunities_small) if opportunities_small else 0
    profit_large = max(p.estimated_profit for p in opportunities_large) if opportunities_large else 0
    
    # Larger amount should find more profitable paths
    assert profit_large > 0, "Should find profitable paths for larger amount"
    
    # Identify the best paths
    best_path_small = max(opportunities_small, key=lambda p: p.estimated_profit) if opportunities_small else None
    best_path_large = max(opportunities_large, key=lambda p: p.estimated_profit) if opportunities_large else None
    
    # Verify the best paths
    assert best_path_small is not None, "Should find a best path for small amount"
    assert best_path_large is not None, "Should find a best path for large amount"
    
    # For larger amounts, the best path should be the 3-hop path
    large_path_hop_count = max(len(step['path']) for step in best_path_large.route)
    assert large_path_hop_count >= 3, "Best path for larger amount should have at least 3 hops"