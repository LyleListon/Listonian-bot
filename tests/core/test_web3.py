"""
Test Web3 interaction layer.

This module tests:
1. Provider connections
2. Contract interactions
3. Transaction handling
4. Gas estimation
"""

import pytest
import asyncio
import logging
from typing import Dict, Any
from decimal import Decimal
from web3 import Web3
from web3.contract import Contract

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
async def web3_config(test_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get Web3 configuration."""
    return {
        'network': test_config['test_environment']['network'],
        'rpc_url': test_config['test_environment']['rpc_url'],
        'chain_id': test_config['test_environment']['chain_id']
    }

@pytest.mark.asyncio
async def test_provider_connection(mock_web3_provider):
    """Test Web3 provider connection."""
    # Test block number retrieval
    block_number = await mock_web3_provider.eth_get_block_number()
    assert block_number == 12345678, "Failed to get block number"
    
    # Test balance check
    balance = await mock_web3_provider.eth_get_balance("0x0000000000000000000000000000000000000000")
    assert balance.startswith("0x"), "Invalid balance format"

@pytest.mark.asyncio
async def test_contract_loading(mock_contract, test_config):
    """Test contract loading and validation."""
    from arbitrage_bot.core.web3 import load_contract
    
    # Test with valid ABI
    contract = await load_contract(
        address=test_config['test_pools']['baseswap_weth_usdc']['address'],
        abi_name="baseswap_v3_pool"
    )
    assert isinstance(contract, Contract), "Failed to load contract"
    
    # Test with invalid address
    with pytest.raises(ValueError):
        await load_contract(
            address="invalid_address",
            abi_name="baseswap_v3_pool"
        )

@pytest.mark.asyncio
async def test_transaction_building(mock_web3_provider, test_config):
    """Test transaction building and signing."""
    from arbitrage_bot.core.web3 import build_transaction
    
    tx_params = {
        'from': test_config['test_accounts']['trader']['address'],
        'to': test_config['test_pools']['baseswap_weth_usdc']['address'],
        'value': 0,
        'gas': 300000,
        'maxFeePerGas': Web3.to_wei(20, 'gwei'),
        'maxPriorityFeePerGas': Web3.to_wei(2, 'gwei')
    }
    
    tx = await build_transaction(tx_params)
    assert 'chainId' in tx, "Missing chainId"
    assert 'nonce' in tx, "Missing nonce"
    assert tx['type'] == '0x2', "Invalid transaction type"

@pytest.mark.asyncio
async def test_gas_estimation(mock_contract, test_config):
    """Test gas estimation."""
    from arbitrage_bot.core.web3 import estimate_gas
    
    # Mock transaction data
    tx_data = {
        'from': test_config['test_accounts']['trader']['address'],
        'to': test_config['test_pools']['baseswap_weth_usdc']['address'],
        'data': "0x" + "00" * 32,
        'value': 0
    }
    
    gas = await estimate_gas(tx_data)
    assert isinstance(gas, int), "Invalid gas estimate type"
    assert gas > 0, "Invalid gas estimate value"

@pytest.mark.asyncio
async def test_event_handling(mock_contract):
    """Test event handling and filtering."""
    from arbitrage_bot.core.web3 import setup_event_filter
    
    # Test Swap event filter
    swap_filter = await setup_event_filter(
        mock_contract,
        "Swap",
        from_block="latest"
    )
    assert swap_filter is not None, "Failed to create event filter"
    
    # Test event processing
    events = await swap_filter.get_new_entries()
    assert isinstance(events, list), "Invalid events format"

@pytest.mark.asyncio
async def test_multicall(mock_web3_provider, test_config):
    """Test multicall functionality."""
    from arbitrage_bot.core.web3 import batch_call
    
    calls = [
        {
            'target': test_config['test_pools']['baseswap_weth_usdc']['address'],
            'call_data': "0x" + "00" * 32
        },
        {
            'target': test_config['test_pools']['pancake_weth_usdc']['address'],
            'call_data': "0x" + "00" * 32
        }
    ]
    
    results = await batch_call(calls)
    assert len(results) == 2, "Invalid number of results"
    assert all(isinstance(r, bytes) for r in results), "Invalid result format"

@pytest.mark.asyncio
async def test_error_handling():
    """Test Web3 error handling."""
    from arbitrage_bot.core.web3 import handle_web3_error
    
    # Test revert error
    revert_error = {
        'code': 3,
        'message': 'execution reverted: Insufficient balance'
    }
    error_info = handle_web3_error(revert_error)
    assert 'Insufficient balance' in error_info['message']
    
    # Test network error
    network_error = {
        'code': -32005,
        'message': 'Request failed'
    }
    error_info = handle_web3_error(network_error)
    assert 'network' in error_info['type'].lower()

@pytest.mark.asyncio
async def test_checksummed_addresses(test_config):
    """Test address checksum validation."""
    from arbitrage_bot.core.web3 import validate_address
    
    # Test valid checksummed address
    address = test_config['test_tokens']['WETH']['address']
    assert validate_address(address), "Failed to validate checksummed address"
    
    # Test non-checksummed address
    with pytest.raises(ValueError):
        validate_address(address.lower())

if __name__ == "__main__":
    pytest.main([__file__, "-v"])