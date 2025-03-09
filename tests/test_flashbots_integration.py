"""Tests for Flashbots integration with SwapBased DEX."""

import pytest
import asyncio
from typing import Dict, Any
from decimal import Decimal
from eth_typing import HexStr

from arbitrage_bot.core.utils.flashbots import (
    encode_bundle_data,
    simulate_bundle,
    submit_bundle,
    get_optimal_gas_params
)

from arbitrage_bot.core.dex.swapbased import SwapBasedDEX
from arbitrage_bot.core.web3.web3_manager import Web3Manager

# Test configuration
TEST_CONFIG = {
    "name": "SwapBased",
    "version": "v3",
    "factory": "0xb5620F90e803C7F957a9EF351B8DB3C746021BEa",
    "router": "0x756C6BbDd915202adac7beBB1c6C89aC0886503f",
    "quoter": "0x0BE808376Ecb75a5CF9bB6D237d16cd37893d904",
    "fee": 3000,
    "tick_spacing": 60,
    "enabled": True,
    "weth_address": "0x4200000000000000000000000000000000000006",
    "flashbots": {
        "enabled": True,
        "relay_url": "https://relay-base.flashbots.net",
        "auth_signer_key": "${FLASHBOTS_AUTH_KEY}",
        "max_bundle_size": 5,
        "max_blocks_ahead": 3,
        "min_priority_fee": "1.5",
        "max_priority_fee": "3",
        "sandwich_detection": True,
        "frontrun_detection": True,
        "adaptive_gas": True
    }
}

@pytest.fixture
async def web3_manager():
    """Create Web3Manager instance."""
    manager = Web3Manager(TEST_CONFIG)
    await manager.initialize()
    return manager

@pytest.fixture
async def swapbased_dex(web3_manager):
    """Create SwapBasedDEX instance."""
    dex = SwapBasedDEX(web3_manager, TEST_CONFIG)
    initialized = await dex.initialize()
    assert initialized
    return dex

@pytest.mark.asyncio
async def test_flashbots_initialization(swapbased_dex):
    """Test Flashbots initialization."""
    assert swapbased_dex.flashbots_enabled
    assert swapbased_dex.flashbots is not None
    assert swapbased_dex.max_bundle_size == 5
    assert swapbased_dex.max_blocks_ahead == 3
    assert swapbased_dex.min_priority_fee == 1.5
    assert swapbased_dex.max_priority_fee == 3.0
    assert swapbased_dex.sandwich_detection
    assert swapbased_dex.frontrun_detection
    assert swapbased_dex.adaptive_gas

@pytest.mark.asyncio
async def test_mev_protection(swapbased_dex):
    """Test MEV protection checks."""
    # Test with high-risk transaction
    quote = await swapbased_dex.get_quote_with_impact(
        amount_in=int(1e18),  # 1 WETH
        path=[
            "0x4200000000000000000000000000000000000006",  # WETH
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"   # USDC
        ]
    )
    
    # Should return None for high-risk transactions
    assert quote is None or quote.get('price_impact', 0) < 0.05

@pytest.mark.asyncio
async def test_adaptive_gas_pricing(swapbased_dex, web3_manager):
    """Test adaptive gas pricing."""
    gas_params = await get_optimal_gas_params(
        web3_manager,
        swapbased_dex.min_priority_fee,
        swapbased_dex.max_priority_fee
    )
    
    assert gas_params is not None
    assert 'maxFeePerGas' in gas_params
    assert 'maxPriorityFeePerGas' in gas_params
    assert gas_params['maxPriorityFeePerGas'] >= int(1.5 * 10**9)  # Min 1.5 GWEI
    assert gas_params['maxPriorityFeePerGas'] <= int(3.0 * 10**9)  # Max 3.0 GWEI

@pytest.mark.asyncio
async def test_bundle_submission(swapbased_dex):
    """Test Flashbots bundle submission."""
    # Create test swap
    amount_in = int(0.1 * 10**18)  # 0.1 WETH
    path = [
        "0x4200000000000000000000000000000000000006",  # WETH
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"   # USDC
    ]
    
    # Get quote
    quote = await swapbased_dex.get_quote_with_impact(amount_in, path)
    assert quote is not None
    
    # Execute swap
    tx_hash = await swapbased_dex.swap_exact_tokens_for_tokens(
        amount_in=amount_in,
        min_amount_out=int(float(quote['amount_out']) * 0.995),  # 0.5% slippage
        path=path,
        to=swapbased_dex.web3_manager.account.address,
        deadline=9999999999,  # Far future
    )
    
    assert tx_hash is not None
    assert isinstance(tx_hash, (str, HexStr))
    assert len(tx_hash) == 66  # "0x" + 64 hex chars

@pytest.mark.asyncio
async def test_bundle_simulation(swapbased_dex):
    """Test Flashbots bundle simulation."""
    # Create test transaction
    amount_in = int(0.1 * 10**18)  # 0.1 WETH
    path = [
        "0x4200000000000000000000000000000000000006",  # WETH
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"   # USDC
    ]
    
    # Get quote and build transaction
    quote = await swapbased_dex.get_quote_with_impact(amount_in, path)
    assert quote is not None
    
    params = {
        'tokenIn': path[0],
        'tokenOut': path[1],
        'fee': 3000,
        'recipient': swapbased_dex.web3_manager.account.address,
        'amountIn': amount_in,
        'amountOutMinimum': int(float(quote['amount_out']) * 0.995),
        'sqrtPriceLimitX96': 0
    }
    
    tx = await swapbased_dex.router.functions.exactInputSingle(params).build_transaction({
        'from': swapbased_dex.web3_manager.account.address,
        'gas': 300000,
        'maxFeePerGas': await swapbased_dex.web3_manager.get_max_fee(),
        'maxPriorityFeePerGas': await swapbased_dex.web3_manager.get_priority_fee(),
        'nonce': await swapbased_dex.web3_manager.get_nonce()
    })
    
    # Sign transaction
    signed_tx = swapbased_dex.web3_manager.account.sign_transaction(tx)
    
    # Create bundle
    bundle = [{
        'signed_transaction': signed_tx.rawTransaction
    }]
    
    # Get target block
    current_block = await swapbased_dex.web3_manager.eth.block_number
    target_block = current_block + 1
    
    # Simulate bundle
    simulation = await simulate_bundle(
        swapbased_dex.flashbots,
        bundle,
        target_block
    )
    
    assert simulation is not None
    assert simulation['success']
    assert 'results' in simulation

if __name__ == "__main__":
    """Run tests directly."""
    asyncio.run(pytest.main([__file__, '-v']))