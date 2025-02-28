"""Test suite for Flashbots and Flash Loan integration."""

import os
import json
import asyncio
import pytest
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import patch, MagicMock, AsyncMock

# Pytest marks
pytestmark = pytest.mark.asyncio

# Import modules to test
try:
    from arbitrage_bot.utils.config_loader import load_config
    from arbitrage_bot.core.web3.web3_manager import create_web3_manager
    from arbitrage_bot.core.flash_loan_manager_async import AsyncFlashLoanManager, create_flash_loan_manager
    from arbitrage_bot.integration.flashbots_integration import (
        setup_flashbots_rpc,
        test_flashbots_connection,
        create_and_simulate_bundle,
        optimize_and_submit_bundle
    )
except ImportError:
    # For when running tests directly without package installation
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from arbitrage_bot.utils.config_loader import load_config
    from arbitrage_bot.core.web3.web3_manager import create_web3_manager
    from arbitrage_bot.core.flash_loan_manager_async import AsyncFlashLoanManager, create_flash_loan_manager
    from arbitrage_bot.integration.flashbots_integration import (
        setup_flashbots_rpc,
        test_flashbots_connection,
        create_and_simulate_bundle,
        optimize_and_submit_bundle
    )

# Test configurations
TEST_CONFIG = {
    "provider_url": "http://localhost:8545",  # Local node for testing
    "chain_id": 1337,  # Local chain ID
    "private_key": "0x0000000000000000000000000000000000000000000000000000000000000001",
    "wallet_address": "0x0000000000000000000000000000000000000001",
    "tokens": {
        "WETH": {"address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "decimals": 18},
        "USDC": {"address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 6}
    },
    "flash_loans": {
        "enabled": True,
        "use_flashbots": True,
        "min_profit_basis_points": 200,
        "max_trade_size": "1",
        "slippage_tolerance": 50,
        "transaction_timeout": 10,
        "balancer_vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
        "contract_address": {
            "mainnet": "0x0000000000000000000000000000000000000000",
            "testnet": "0xa111E81d1F6F8bF648d1405ADf45aAC92602BcA8"
        }
    },
    "flashbots": {
        "relay_url": "https://relay.flashbots.net",
        "auth_signer_key": "0x0000000000000000000000000000000000000000000000000000000000000002",
        "min_profit_threshold": 1000000000000000
    }
}

# Test fixtures

@pytest.fixture
async def mock_web3_manager():
    """Create a mock Web3Manager for testing."""
    mock_manager = MagicMock()
    mock_manager.w3 = MagicMock()
    mock_manager.w3.eth = AsyncMock()
    mock_manager.w3.eth.get_transaction_count = AsyncMock(return_value=0)
    mock_manager.w3.eth.gas_price = AsyncMock(return_value=20000000000)  # 20 gwei
    mock_manager.w3.eth.block_number = AsyncMock(return_value=10000000)
    mock_manager.w3.to_wei = lambda amount, unit: int(amount * (10 ** 18 if unit == 'ether' else 1))
    mock_manager.w3.from_wei = lambda amount, unit: amount / (10 ** 18 if unit == 'ether' else 1)
    mock_manager.w3.codec = MagicMock()
    mock_manager.w3.codec.encode_abi = MagicMock(return_value=b'encoded_data')
    
    mock_manager.wallet_address = "0x0000000000000000000000000000000000000001"
    mock_manager.provider_url = "http://localhost:8545"
    mock_manager.account = MagicMock()
    mock_manager.account.address = "0x0000000000000000000000000000000000000001"
    mock_manager.account.sign_transaction = MagicMock(return_value=MagicMock(rawTransaction=b'0x123456'))
    mock_manager.get_weth_address = MagicMock(return_value="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    mock_manager._load_abi = AsyncMock(return_value=[{"name": "test", "type": "function"}])
    mock_manager.get_token_contract = AsyncMock()
    mock_manager.wait_for_transaction = AsyncMock()
    
    return mock_manager

@pytest.fixture
async def mock_config():
    """Create a test configuration."""
    return TEST_CONFIG.copy()

@pytest.fixture
async def mock_flashbots_manager():
    """Create a mock FlashbotsManager for testing."""
    mock_manager = MagicMock()
    mock_manager.relay_url = "https://relay.flashbots.net"
    mock_manager.create_bundle = AsyncMock(return_value="test-bundle-id")
    mock_manager.simulate_bundle = AsyncMock(return_value={
        "success": True,
        "bundle_id": "test-bundle-id",
        "target_block": 10000001,
        "simulation_result": {"success": True},
        "profit": {"net_profit_wei": 1000000000000000}
    })
    mock_manager.optimize_bundle_gas = AsyncMock(return_value={
        "success": True,
        "max_fee_per_gas": 30000000000,
        "max_priority_fee_per_gas": 2000000000
    })
    mock_manager.submit_bundle = AsyncMock(return_value={
        "success": True,
        "bundle_id": "test-bundle-id",
        "target_block": 10000001
    })
    
    return mock_manager

@pytest.fixture
async def mock_balance_validator():
    """Create a mock BundleBalanceValidator for testing."""
    mock_validator = MagicMock()
    mock_validator.validate_bundle_balance = AsyncMock(return_value={
        "success": True,
        "token_balances": {
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": {
                "before": 10000000000000000000,
                "after": 10100000000000000000,
                "change": 100000000000000000
            }
        },
        "profit_wei": 100000000000000000,
        "expected_profit_met": True
    })
    
    return mock_validator

@pytest.fixture
async def mock_token_contracts(mock_web3_manager):
    """Create mock token contracts for testing."""
    # Mock WETH contract
    weth_contract = MagicMock()
    weth_contract.functions = MagicMock()
    weth_contract.functions.symbol = MagicMock(return_value=MagicMock(call=AsyncMock(return_value="WETH")))
    weth_contract.functions.decimals = MagicMock(return_value=MagicMock(call=AsyncMock(return_value=18)))
    
    # Mock USDC contract
    usdc_contract = MagicMock()
    usdc_contract.functions = MagicMock()
    usdc_contract.functions.symbol = MagicMock(return_value=MagicMock(call=AsyncMock(return_value="USDC")))
    usdc_contract.functions.decimals = MagicMock(return_value=MagicMock(call=AsyncMock(return_value=6)))
    
    # Set up the mock token contract returns
    async def get_token_contract(address):
        if address.lower() == "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2".lower():
            return weth_contract
        elif address.lower() == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48".lower():
            return usdc_contract
        return None
    
    mock_web3_manager.get_token_contract = AsyncMock(side_effect=get_token_contract)
    
    return {
        "WETH": weth_contract,
        "USDC": usdc_contract
    }

@pytest.fixture
async def mock_flashbots_components(mock_web3_manager, mock_flashbots_manager, mock_balance_validator, mock_config):
    """Create mock Flashbots components."""
    return {
        "web3_manager": mock_web3_manager,
        "flashbots_manager": mock_flashbots_manager,
        "balance_validator": mock_balance_validator,
        "config": mock_config
    }

@pytest.fixture
async def mock_flash_loan_manager(
    mock_web3_manager, 
    mock_config, 
    mock_flashbots_manager, 
    mock_balance_validator,
    mock_token_contracts
):
    """Create a mock AsyncFlashLoanManager for testing."""
    # Mock contract creation
    arbitrage_contract = MagicMock()
    arbitrage_contract.address = "0xa111E81d1F6F8bF648d1405ADf45aAC92602BcA8"
    arbitrage_contract.functions = MagicMock()
    arbitrage_contract.functions.executeArbitrage = MagicMock(return_value=MagicMock(
        build_transaction=AsyncMock(return_value={
            "from": "0x0000000000000000000000000000000000000001",
            "to": "0xa111E81d1F6F8bF648d1405ADf45aAC92602BcA8",
            "data": "0x123456",
            "gas": 500000,
            "gasPrice": 20000000000
        })
    ))
    
    mock_web3_manager.w3.eth.contract = MagicMock(return_value=arbitrage_contract)
    
    # Create manager
    manager = AsyncFlashLoanManager(
        web3_manager=mock_web3_manager,
        config=mock_config,
        flashbots_manager=mock_flashbots_manager,
        balance_validator=mock_balance_validator
    )
    
    # Mock initialization
    manager.initialized = True
    manager.arbitrage_contract = arbitrage_contract
    manager.arbitrage_contract_address = "0xa111E81d1F6F8bF648d1405ADf45aAC92602BcA8"
    manager.supported_tokens = {
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": {
            "symbol": "WETH",
            "decimals": 18,
            "flash_loan_enabled": True
        },
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": {
            "symbol": "USDC",
            "decimals": 6,
            "flash_loan_enabled": True
        }
    }
    
    return manager

# Flashbots integration tests

@pytest.mark.asyncio
async def test_setup_flashbots_rpc(mock_web3_manager, mock_config):
    """Test Flashbots RPC setup."""
    with patch('arbitrage_bot.integration.flashbots_integration.setup_flashbots_rpc', new_callable=AsyncMock) as mock_setup:
        mock_setup.return_value = {
            "web3_manager": mock_web3_manager,
            "flashbots_manager": MagicMock(),
            "balance_validator": MagicMock(),
            "config": mock_config
        }
        
        result = await setup_flashbots_rpc(mock_web3_manager, mock_config)
        
        assert result is not None
        assert "web3_manager" in result
        assert "flashbots_manager" in result
        assert "balance_validator" in result
        
        # Verify the setup was called with correct parameters
        mock_setup.assert_called_once_with(mock_web3_manager, mock_config)

@pytest.mark.asyncio
async def test_flashbots_connection(mock_web3_manager):
    """Test Flashbots connection testing."""
    with patch('arbitrage_bot.integration.flashbots_integration.test_flashbots_connection', new_callable=AsyncMock) as mock_test:
        mock_test.return_value = {
            "success": True,
            "stats": {
                "is_high_priority": True,
                "all_time_miner_payments": "0.5 ETH",
                "all_time_gas_simulated": "10000"
            }
        }
        
        result = await test_flashbots_connection(mock_web3_manager)
        
        assert result["success"] is True
        assert "stats" in result
        
        # Verify the test was called with correct parameters
        mock_test.assert_called_once_with(mock_web3_manager)

@pytest.mark.asyncio
async def test_create_and_simulate_bundle(mock_web3_manager, mock_flashbots_components):
    """Test bundle creation and simulation."""
    with patch('arbitrage_bot.integration.flashbots_integration.create_and_simulate_bundle', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {
            "success": True,
            "bundle_id": "test-bundle-id",
            "target_block": 10000001,
            "profit": {
                "net_profit_wei": 1000000000000000,
                "tokens": {
                    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": 1000000000000000
                }
            }
        }
        
        transactions = [{
            "from": "0x0000000000000000000000000000000000000001",
            "to": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "data": "0x123456",
            "gas": 500000,
            "gasPrice": 20000000000
        }]
        
        token_addresses = ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]
        
        with patch('arbitrage_bot.integration.flashbots_integration.setup_flashbots_rpc', new_callable=AsyncMock) as mock_setup:
            mock_setup.return_value = mock_flashbots_components
            
            result = await create_and_simulate_bundle(
                web3_manager=mock_web3_manager,
                transactions=transactions,
                token_addresses=token_addresses
            )
            
            assert result["success"] is True
            assert result["bundle_id"] == "test-bundle-id"
            assert "profit" in result
            assert result["profit"]["net_profit_wei"] == 1000000000000000

@pytest.mark.asyncio
async def test_optimize_and_submit_bundle(mock_web3_manager, mock_flashbots_components):
    """Test bundle optimization and submission."""
    with patch('arbitrage_bot.integration.flashbots_integration.optimize_and_submit_bundle', new_callable=AsyncMock) as mock_optimize:
        mock_optimize.return_value = {
            "success": True,
            "bundle_id": "test-bundle-id",
            "target_block": 10000001,
            "gas_settings": {
                "max_fee_per_gas": 30000000000,
                "max_priority_fee_per_gas": 2000000000
            }
        }
        
        with patch('arbitrage_bot.integration.flashbots_integration.setup_flashbots_rpc', new_callable=AsyncMock) as mock_setup:
            mock_setup.return_value = mock_flashbots_components
            
            result = await optimize_and_submit_bundle(
                web3_manager=mock_web3_manager,
                bundle_id="test-bundle-id",
                min_profit=1000000000000000
            )
            
            assert result["success"] is True
            assert result["bundle_id"] == "test-bundle-id"
            assert "gas_settings" in result

# Flash loan manager tests

@pytest.mark.asyncio
async def test_flash_loan_manager_initialization(mock_web3_manager, mock_config, mock_flashbots_manager):
    """Test AsyncFlashLoanManager initialization."""
    with patch('arbitrage_bot.core.flash_loan_manager_async.create_flash_loan_manager', new_callable=AsyncMock) as mock_create:
        manager = AsyncFlashLoanManager(
            web3_manager=mock_web3_manager,
            config=mock_config,
            flashbots_manager=mock_flashbots_manager
        )
        
        # Set manager properties for testing
        manager.initialized = True
        manager.arbitrage_contract = MagicMock()
        manager.arbitrage_contract_address = "0xa111E81d1F6F8bF648d1405ADf45aAC92602BcA8"
        
        assert manager.enabled == mock_config["flash_loans"]["enabled"]
        assert manager.use_flashbots == mock_config["flash_loans"]["use_flashbots"]
        assert manager.min_profit_bps == mock_config["flash_loans"]["min_profit_basis_points"]
        assert manager.transaction_timeout == mock_config["flash_loans"]["transaction_timeout"]

@pytest.mark.asyncio
async def test_token_support_detection(mock_flash_loan_manager):
    """Test token support detection."""
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    random_address = "0x0000000000000000000000000000000000000123"
    
    # Check supported tokens
    is_weth_supported = await mock_flash_loan_manager.is_token_supported(weth_address)
    is_usdc_supported = await mock_flash_loan_manager.is_token_supported(usdc_address)
    
    assert is_weth_supported is True
    assert is_usdc_supported is True
    
    # Set up mock for random token check
    mock_flash_loan_manager._get_token_contract = AsyncMock(return_value=None)
    is_random_supported = await mock_flash_loan_manager.is_token_supported(random_address)
    
    assert is_random_supported is False

@pytest.mark.asyncio
async def test_flash_loan_cost_estimation(mock_flash_loan_manager):
    """Test flash loan cost estimation."""
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    amount = 1000000000000000000  # 1 WETH
    
    # Mock token price
    mock_flash_loan_manager._get_token_price = AsyncMock(return_value=Decimal('1.0'))
    
    cost_estimate = await mock_flash_loan_manager.estimate_flash_loan_cost(weth_address, amount)
    
    assert cost_estimate["success"] is True
    assert cost_estimate["token"] == weth_address
    assert cost_estimate["amount"] == amount
    assert cost_estimate["protocol_fee"] == int(amount * Decimal('0.0009'))  # 0.09%
    assert "gas_cost_wei" in cost_estimate
    assert "total_cost" in cost_estimate
    assert "min_profit_required" in cost_estimate
    assert cost_estimate["min_profit_required"] == int(amount * mock_flash_loan_manager.min_profit_bps / 10000)

@pytest.mark.asyncio
async def test_arbitrage_opportunity_validation(mock_flash_loan_manager):
    """Test arbitrage opportunity validation."""
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    
    amount_in = 1000000000000000000  # 1 WETH
    expected_output = 1030000000000000000  # 1.03 WETH (3% profit)
    
    # Mock cost estimation
    mock_flash_loan_manager.estimate_flash_loan_cost = AsyncMock(return_value={
        "success": True,
        "token": weth_address,
        "amount": amount_in,
        "protocol_fee": 900000000000000,  # 0.0009 WETH
        "gas_cost_wei": 1000000000000000,  # 0.001 WETH
        "gas_cost_token": 1000000000000000,  # 0.001 WETH
        "total_cost": 1900000000000000,  # 0.0019 WETH
        "min_profit_required": 20000000000000000,  # 0.02 WETH (2%)
        "min_output_needed": 1021900000000000000  # 1.0219 WETH
    })
    
    # Sample route
    route = [
        {
            "dex_id": 1,
            "dex": "baseswap",
            "token_in": weth_address,
            "token_out": usdc_address,
            "amount_in": amount_in,
            "amount_out": 1800000000  # 1800 USDC
        },
        {
            "dex_id": 2,
            "dex": "pancakeswap",
            "token_in": usdc_address,
            "token_out": weth_address,
            "amount_in": 1800000000,
            "amount_out": expected_output
        }
    ]
    
    validation = await mock_flash_loan_manager.validate_arbitrage_opportunity(
        input_token=weth_address,
        output_token=weth_address,  # Circular arbitrage
        input_amount=amount_in,
        expected_output=expected_output,
        route=route
    )
    
    assert validation["success"] is True
    assert validation["is_circular"] is True
    assert validation["gross_profit"] == expected_output - amount_in
    assert validation["net_profit"] == validation["gross_profit"] - validation["total_cost"]
    assert validation["is_profitable"] is True
    assert "profit_margin" in validation
    assert "route_details" in validation

@pytest.mark.asyncio
async def test_flash_loan_transaction_preparation(mock_flash_loan_manager):
    """Test flash loan transaction preparation."""
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    
    amount = 1000000000000000000  # 1 WETH
    min_profit = 20000000000000000  # 0.02 WETH
    
    # Sample route
    route = [
        {
            "dex_id": 1,
            "dex": "baseswap",
            "token_in": weth_address,
            "token_out": usdc_address,
            "amount_in": amount,
            "amount_out": 1800000000  # 1800 USDC
        },
        {
            "dex_id": 2,
            "dex": "pancakeswap",
            "token_in": usdc_address,
            "token_out": weth_address,
            "amount_in": 1800000000,
            "amount_out": 1030000000000000000  # 1.03 WETH
        }
    ]
    
    # Mock route encoding
    mock_flash_loan_manager._encode_route = AsyncMock(return_value=b'encoded_route')
    
    # Mock max amount check
    mock_flash_loan_manager.get_max_flash_loan_amount = AsyncMock(return_value=10000000000000000000)  # 10 WETH
    
    tx_preparation = await mock_flash_loan_manager.prepare_flash_loan_transaction(
        token_address=weth_address,
        amount=amount,
        route=route,
        min_profit=min_profit
    )
    
    assert tx_preparation["success"] is True
    assert tx_preparation["token"] == weth_address
    assert tx_preparation["amount"] == amount
    assert tx_preparation["min_profit"] == min_profit
    assert "transaction" in tx_preparation
    assert "encoded_route" in tx_preparation

@pytest.mark.asyncio
async def test_flash_loan_execution_via_flashbots(mock_flash_loan_manager):
    """Test flash loan execution via Flashbots."""
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    amount = 1000000000000000000  # 1 WETH
    min_profit = 20000000000000000  # 0.02 WETH
    
    # Sample route
    route = [
        {
            "dex_id": 1,
            "token_in": weth_address,
            "token_out": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "amount_in": amount,
            "amount_out": 1800000000
        },
        {
            "dex_id": 2,
            "token_in": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "token_out": weth_address,
            "amount_in": 1800000000,
            "amount_out": 1030000000000000000
        }
    ]
    
    # Mock transaction preparation
    mock_flash_loan_manager.prepare_flash_loan_transaction = AsyncMock(return_value={
        "success": True,
        "token": weth_address,
        "amount": amount,
        "min_profit": min_profit,
        "encoded_route": b'encoded_route',
        "transaction": {
            "from": "0x0000000000000000000000000000000000000001",
            "to": "0xa111E81d1F6F8bF648d1405ADf45aAC92602BcA8",
            "data": "0x123456",
            "gas": 500000,
            "gasPrice": 20000000000
        }
    })
    
    # Mock Flashbots execution
    mock_flash_loan_manager._execute_via_flashbots = AsyncMock(return_value={
        "success": True,
        "status": "submitted",
        "bundle_id": "test-bundle-id",
        "target_block": 10000001,
        "validation": {"success": True},
        "simulation": {"success": True}
    })
    
    result = await mock_flash_loan_manager.execute_flash_loan_arbitrage(
        token_address=weth_address,
        amount=amount,
        route=route,
        min_profit=min_profit,
        use_flashbots=True
    )
    
    assert result["success"] is True
    assert result["status"] == "submitted"
    assert result["bundle_id"] == "test-bundle-id"
    assert "validation" in result
    assert "simulation" in result

@pytest.mark.asyncio
async def test_flash_loan_execution_standard(mock_flash_loan_manager):
    """Test flash loan execution via standard transaction."""
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    amount = 1000000000000000000  # 1 WETH
    min_profit = 20000000000000000  # 0.02 WETH
    
    # Sample route
    route = [
        {
            "dex_id": 1,
            "token_in": weth_address,
            "token_out": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "amount_in": amount,
            "amount_out": 1800000000
        },
        {
            "dex_id": 2,
            "token_in": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "token_out": weth_address,
            "amount_in": 1800000000,
            "amount_out": 1030000000000000000
        }
    ]
    
    # Mock transaction preparation
    mock_flash_loan_manager.prepare_flash_loan_transaction = AsyncMock(return_value={
        "success": True,
        "token": weth_address,
        "amount": amount,
        "min_profit": min_profit,
        "encoded_route": b'encoded_route',
        "transaction": {
            "from": "0x0000000000000000000000000000000000000001",
            "to": "0xa111E81d1F6F8bF648d1405ADf45aAC92602BcA8",
            "data": "0x123456",
            "gas": 500000,
            "gasPrice": 20000000000
        }
    })
    
    # Mock standard execution
    mock_flash_loan_manager._execute_standard_transaction = AsyncMock(return_value={
        "success": True,
        "status": "confirmed",
        "tx_hash": "0x123456789abcdef",
        "receipt": {
            "transactionHash": "0x123456789abcdef",
            "blockNumber": 10000001,
            "status": 1
        }
    })
    
    result = await mock_flash_loan_manager.execute_flash_loan_arbitrage(
        token_address=weth_address,
        amount=amount,
        route=route,
        min_profit=min_profit,
        use_flashbots=False
    )
    
    assert result["success"] is True
    assert result["status"] == "confirmed"
    assert result["tx_hash"] == "0x123456789abcdef"
    assert "receipt" in result

# Integration test that combines both Flashbots and Flash Loans

@pytest.mark.asyncio
async def test_integrated_flash_loan_with_flashbots(
    mock_web3_manager, 
    mock_config, 
    mock_flashbots_components, 
    mock_flash_loan_manager
):
    """Test integrated Flash Loan with Flashbots workflow."""
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    
    amount = 1000000000000000000  # 1 WETH
    expected_output = 1030000000000000000  # 1.03 WETH
    
    # Sample route
    route = [
        {
            "dex_id": 1,
            "dex": "baseswap",
            "token_in": weth_address,
            "token_out": usdc_address,
            "amount_in": amount,
            "amount_out": 1800000000  # 1800 USDC
        },
        {
            "dex_id": 2,
            "dex": "pancakeswap",
            "token_in": usdc_address,
            "token_out": weth_address,
            "amount_in": 1800000000,
            "amount_out": expected_output
        }
    ]
    
    # Mock create_flash_loan_manager
    with patch('arbitrage_bot.core.flash_loan_manager_async.create_flash_loan_manager', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_flash_loan_manager
        
        # Mock setup_flashbots_rpc
        with patch('arbitrage_bot.integration.flashbots_integration.setup_flashbots_rpc', new_callable=AsyncMock) as mock_setup:
            mock_setup.return_value = mock_flashbots_components
            
            # Mock the validation and execution functions
            mock_flash_loan_manager.validate_arbitrage_opportunity = AsyncMock(return_value={
                "success": True,
                "is_circular": True,
                "gross_profit": 30000000000000000,  # 0.03 WETH
                "total_cost": 1900000000000000,  # 0.0019 WETH
                "net_profit": 28100000000000000,  # 0.0281 WETH
                "min_profit_required": 20000000000000000,  # 0.02 WETH
                "is_profitable": True,
                "profit_margin": 0.0281
            })
            
            mock_flash_loan_manager.execute_flash_loan_arbitrage = AsyncMock(return_value={
                "success": True,
                "status": "submitted",
                "bundle_id": "test-bundle-id",
                "target_block": 10000001
            })
            
            # Create the flash loan manager with Flashbots integration
            manager = await create_flash_loan_manager(
                web3_manager=mock_web3_manager,
                config=mock_config
            )
            
            # Validate the arbitrage opportunity
            validation = await manager.validate_arbitrage_opportunity(
                input_token=weth_address,
                output_token=weth_address,
                input_amount=amount,
                expected_output=expected_output,
                route=route
            )
            
            assert validation["success"] is True
            assert validation["is_profitable"] is True
            
            # Execute the arbitrage if profitable
            if validation["is_profitable"]:
                result = await manager.execute_flash_loan_arbitrage(
                    token_address=weth_address,
                    amount=amount,
                    route=route,
                    min_profit=validation["net_profit"],
                    use_flashbots=True
                )
                
                assert result["success"] is True
                assert result["status"] == "submitted"
                assert "bundle_id" in result

if __name__ == "__main__":
    # Can be run directly with pytest
    pytest.main(["-xvs", __file__])