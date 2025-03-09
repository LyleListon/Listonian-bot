"""
Integration tests for arbitrage system components.
Tests the interaction between PathFinder, FlashLoanManager, and Flashbots.
"""

import pytest
import asyncio
from decimal import Decimal
from typing import List
from eth_typing import ChecksumAddress
from web3 import Web3

from ..core.path_finder import PathFinder, ArbitragePath
from ..core.unified_flash_loan_manager import UnifiedFlashLoanManager
from ..core.web3.flashbots.flashbots_provider import FlashbotsProvider
from ..core.dex.dex_manager import DexManager
from ..core.web3.balance_validator import BalanceValidator

# Test configuration
TEST_CONFIG = {
    'flash_loan': {
        'min_profit': '0.01',  # 0.01 ETH minimum profit
        'balancer_vault': '0x1234...', # Test vault address
        'max_parallel_pools': 5,
        'min_liquidity_ratio': 1.5
    },
    'path_finder': {
        'max_paths_to_check': 50,
        'min_profit_threshold': 0.001,
        'max_path_length': 4,
        'max_parallel_requests': 5
    }
}

@pytest.fixture
async def setup_components(web3_manager, dex_manager):
    """Set up test components."""
    # Initialize balance validator
    balance_validator = BalanceValidator(web3_manager)

    # Initialize Flashbots provider
    flashbots_provider = FlashbotsProvider(
        w3=web3_manager.w3,
        relay_url="http://test-relay",
        auth_key="test_key",
        chain_id=8453
    )

    # Initialize flash loan manager
    flash_loan_manager = await UnifiedFlashLoanManager(
        web3_manager=web3_manager,
        dex_manager=dex_manager,
        balance_validator=balance_validator,
        flashbots_provider=flashbots_provider,
        balancer_vault=TEST_CONFIG['flash_loan']['balancer_vault'],
        min_profit=Web3.to_wei(0.01, 'ether'),
        max_parallel_pools=5
    )

    # Initialize path finder
    path_finder = PathFinder(
        dex_manager=dex_manager,
        config=TEST_CONFIG,
        web3_manager=web3_manager
    )

    return flash_loan_manager, path_finder, flashbots_provider

@pytest.mark.asyncio
async def test_multi_path_arbitrage(setup_components):
    """Test multi-path arbitrage discovery and execution."""
    flash_loan_manager, path_finder, flashbots_provider = setup_components

    # Test token addresses
    token_addresses = [
        Web3.to_checksum_address("0x1234..."),  # USDC
        Web3.to_checksum_address("0x5678..."),  # WETH
        Web3.to_checksum_address("0x9abc..."),  # WBTC
        Web3.to_checksum_address("0xdef0...")   # DAI
    ]

    # Find arbitrage paths
    paths = await path_finder.find_arbitrage_paths(
        start_token_address=token_addresses[0],  # Start with USDC
        amount_in=Web3.to_wei(1000, 'ether'),   # 1000 USDC
        max_paths=5
    )

    assert len(paths) > 0, "No arbitrage paths found"

    # Verify path properties
    best_path = paths[0]
    assert isinstance(best_path, ArbitragePath)
    assert best_path.path_length >= 2, "Path too short"
    assert best_path.profit > 0, "Path not profitable"

    # Validate path steps
    for step in best_path.steps:
        assert Web3.is_checksum_address(step.token_in)
        assert Web3.is_checksum_address(step.token_out)
        assert step.amount_in > 0
        assert step.amount_out > 0
        assert step.fee >= 0

    # Test flash loan validation
    is_valid = await flash_loan_manager.validate_flash_loan(
        token_address=best_path.input_token,
        amount=best_path.amount_in,
        expected_profit=best_path.profit,
        path=best_path
    )

    assert is_valid, "Flash loan validation failed"

    # Test bundle simulation
    callback_data = Web3.keccak(text="test_callback")
    result = await flash_loan_manager.execute_flash_loan(
        token_address=best_path.input_token,
        amount=best_path.amount_in,
        target_contract=Web3.to_checksum_address("0x1234..."),
        callback_data=callback_data,
        path=best_path
    )

    assert result['success'], f"Flash loan execution failed: {result.get('error')}"
    assert 'bundle_hash' in result, "No bundle hash returned"
    assert result['profit'] >= best_path.profit, "Actual profit less than expected"

@pytest.mark.asyncio
async def test_parallel_pool_scanning(setup_components):
    """Test parallel pool scanning and price fetching."""
    flash_loan_manager, path_finder, _ = setup_components

    # Generate test pool addresses
    pool_addresses = [
        Web3.to_checksum_address(f"0x{i:040x}")
        for i in range(10)
    ]

    # Test parallel liquidity fetching
    liquidity_results = await flash_loan_manager._get_pool_liquidity(set(pool_addresses))

    assert len(liquidity_results) == len(pool_addresses), "Not all pools scanned"
    assert all(isinstance(v, int) for v in liquidity_results.values()), "Invalid liquidity values"

    # Test cache functionality
    cached_results = await flash_loan_manager._get_pool_liquidity(set(pool_addresses))
    assert cached_results == liquidity_results, "Cache not working correctly"

@pytest.mark.asyncio
async def test_flashbots_bundle_optimization(setup_components):
    """Test Flashbots bundle optimization and MEV protection."""
    _, _, flashbots_provider = setup_components

    # Create test transactions
    transactions = [
        {
            'to': Web3.to_checksum_address("0x1234..."),
            'value': 0,
            'data': b'test_data'
        }
    ]

    # Test bundle simulation
    simulation = await flashbots_provider.simulate_bundle(transactions)
    assert simulation['success'], "Bundle simulation failed"
    assert 'gasUsed' in simulation, "No gas estimation"
    assert 'profitability' in simulation, "No profitability calculation"

    # Test bundle optimization
    optimized_txs, sim_results = await flashbots_provider._optimize_bundle(transactions)
    assert len(optimized_txs) == len(transactions), "Transaction count changed"
    assert sim_results['profitability'] >= simulation['profitability'], "Optimization didn't improve profitability"

@pytest.mark.asyncio
async def test_error_handling(setup_components):
    """Test error handling and retry mechanisms."""
    flash_loan_manager, path_finder, flashbots_provider = setup_components

    # Test invalid token address
    with pytest.raises(ValueError):
        await flash_loan_manager.validate_flash_loan(
            token_address="invalid_address",
            amount=1000,
            expected_profit=100
        )

    # Test insufficient liquidity
    result = await flash_loan_manager.validate_flash_loan(
        token_address=Web3.to_checksum_address("0x1234..."),
        amount=Web3.to_wei(1000000, 'ether'),  # Very large amount
        expected_profit=100
    )
    assert not result, "Should fail with insufficient liquidity"

    # Test invalid path
    paths = await path_finder.find_arbitrage_paths(
        start_token_address=Web3.to_checksum_address("0x1234..."),
        amount_in=0,  # Invalid amount
        max_paths=1
    )
    assert len(paths) == 0, "Should return no paths for invalid input"
