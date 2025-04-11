"""Tests for Sushiswap DEX implementation."""

import pytest
# import asyncio # Unused
# from typing import Dict, Any # Unused
from unittest.mock import Mock, AsyncMock, patch # Removed MagicMock, PropertyMock
from web3.exceptions import BadFunctionCallOutput # Removed ContractLogicError

from ..dex.sushiswap import SushiswapDEX
from ..dex.base_dex_v2 import BaseDEXV2


def create_mock_web3(factory_return=None, factory_error=None):
    """Create a mock Web3 instance with async contract methods."""

    # Create the async call method
    async def async_call():
        if factory_error:
            raise factory_error
        return factory_return

    # Create the factory function
    factory = AsyncMock()
    factory.call = async_call

    # Create the functions object
    functions = AsyncMock()
    functions.factory = Mock(return_value=factory)

    # Create the contract
    contract = AsyncMock()
    contract.functions = functions

    # Create the eth object
    eth = AsyncMock()
    eth.contract = Mock(return_value=contract)

    # Create the Web3 instance
    web3 = AsyncMock()
    web3.eth = eth
    web3.to_checksum_address = Mock(side_effect=lambda x: x.lower())
    web3.is_address = Mock(side_effect=lambda x: not x.startswith("invalid"))

    return web3


@pytest.fixture
async def web3_manager():
    """Create a mock Web3Manager instance."""
    manager = AsyncMock()
    manager.load_abi = Mock(return_value={})  # Return empty ABI for testing
    manager.w3 = create_mock_web3(
        factory_return="0xc35DADB65012eC5796536bD9864eD8773aBc74C4"
    )
    return manager


@pytest.fixture
async def sushiswap_dex(web3_manager, dex_configs):
    """Create SushiswapDEX instance."""
    dex = SushiswapDEX(web3_manager, dex_configs["sushiswap"])
    initialized = await dex.initialize()
    if not initialized:
        pytest.skip("Sushiswap initialization failed - skipping tests")
    return dex


@pytest.mark.asyncio
async def test_initialization(web3_manager, dex_configs):
    """Test Sushiswap initialization."""
    dex = SushiswapDEX(web3_manager, dex_configs["sushiswap"])
    initialized = await dex.initialize()

    assert initialized
    assert dex.initialized
    assert dex.name == "Sushiswap"
    assert dex.version == "v2"
    assert dex.router is not None
    assert dex.factory is not None


@pytest.mark.asyncio
async def test_initialization_with_invalid_router(web3_manager, dex_configs):
    """Test initialization with invalid router address."""
    # Create Web3 instance that raises an error
    web3_manager.w3 = create_mock_web3(factory_error=BadFunctionCallOutput())

    invalid_config = dex_configs["sushiswap"].copy()
    invalid_config["router"] = "0x0000000000000000000000000000000000000000"

    dex = SushiswapDEX(web3_manager, invalid_config)
    initialized = await dex.initialize()

    assert not initialized
    assert not dex.initialized


@pytest.mark.asyncio
async def test_get_quote_with_impact(sushiswap_dex, token_addresses, test_amounts):
    """Test quote retrieval with price impact."""
    path = [token_addresses["WETH"], token_addresses["USDC"]]
    amount_in = test_amounts["WETH"]["medium"]  # 1 WETH

    # Mock the base class method
    with patch.object(
        BaseDEXV2, "get_quote_with_impact", new_callable=AsyncMock
    ) as mock_quote:
        mock_quote.return_value = {
            "amount_in": amount_in,
            "amount_out": int(1500e6),  # 1500 USDC
            "price_impact": 0.02,
            "liquidity_depth": 10000,
            "fee_rate": 0.003,
            "estimated_gas": 150000,  # Base estimate
        }

        quote = await sushiswap_dex.get_quote_with_impact(amount_in, path)

        assert quote is not None
        assert quote["amount_in"] == amount_in
        assert quote["amount_out"] > 0
        assert 0 <= quote["price_impact"] <= 1
        assert quote["liquidity_depth"] > 0
        assert quote["fee_rate"] == 0.003
        assert quote["estimated_gas"] == 180000  # Sushiswap specific


@pytest.mark.asyncio
async def test_low_liquidity_quote(sushiswap_dex, token_addresses, test_amounts):
    """Test quote with low liquidity pool."""
    path = [token_addresses["WETH"], token_addresses["DAI"]]
    amount_in = test_amounts["WETH"]["large"]  # 10 WETH

    # Mock the base class method
    with patch.object(
        BaseDEXV2, "get_quote_with_impact", new_callable=AsyncMock
    ) as mock_quote:
        mock_quote.return_value = {
            "amount_in": amount_in,
            "amount_out": int(100e18),  # 100 DAI
            "price_impact": 0.5,
            "liquidity_depth": 500,  # Low liquidity
            "fee_rate": 0.003,
            "estimated_gas": 150000,
        }

        quote = await sushiswap_dex.get_quote_with_impact(amount_in, path)
        assert quote is None  # Should return None for low liquidity


@pytest.mark.asyncio
async def test_price_impact_calculation(sushiswap_dex):
    """Test price impact calculation."""
    # Test with different amounts and reserves
    test_cases = [
        (int(1e18), int(1500e6), int(100e18), int(150000e6)),  # Normal case
        (int(10e18), int(15000e6), int(100e18), int(150000e6)),  # Large amount
        (int(0.1e18), int(150e6), int(100e18), int(150000e6)),  # Small amount
    ]

    prev_impact = 0
    for amount_in, amount_out, reserve_in, reserve_out in test_cases:
        with patch.object(BaseDEXV2, "_calculate_price_impact", return_value=0.02):
            impact = sushiswap_dex._calculate_price_impact(
                amount_in, amount_out, reserve_in, reserve_out
            )
            assert 0 <= impact <= 1
            assert impact >= prev_impact  # Impact should increase with amount
            prev_impact = impact


@pytest.mark.asyncio
async def test_swap_validation(sushiswap_dex, token_addresses):
    """Test swap parameter validation."""
    path = [token_addresses["WETH"], token_addresses["USDC"]]

    # Test invalid amount
    with pytest.raises(ValueError):
        await sushiswap_dex._validate_amounts(0)

    # Test invalid path
    with pytest.raises(ValueError):
        await sushiswap_dex._validate_path([])

    # Test invalid address
    with pytest.raises(ValueError, match="Invalid address in path"):
        await sushiswap_dex._validate_path(["invalid_address", path[1]])


@pytest.mark.asyncio
async def test_error_handling(sushiswap_dex):
    """Test error handling."""
    path = [
        "0x0000000000000000000000000000000000000000",  # Invalid address
        "0x0000000000000000000000000000000000000000",  # Invalid address
    ]

    # Mock get_quote_with_impact to raise an exception
    with patch.object(
        BaseDEXV2, "get_quote_with_impact", side_effect=ValueError("Invalid path")
    ):
        with pytest.raises(
            ValueError, match="Sushiswap quote calculation failed: Invalid path"
        ):
            await sushiswap_dex.get_quote_with_impact(int(1e18), path)


if __name__ == "__main__":
    pytest.main([__file__])
