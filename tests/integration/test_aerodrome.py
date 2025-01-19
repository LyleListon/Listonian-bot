"""Integration tests for Aerodrome V2/V3."""

import pytest
from decimal import Decimal
from typing import Dict, Any
from web3 import Web3
from arbitrage_bot.dex.aerodrome_v2 import AerodromeV2
from arbitrage_bot.dex.aerodrome_v3 import AerodromeV3

# Test constants
TEST_AMOUNT = Decimal("1.0")

@pytest.fixture
async def v2_dex(mock_web3: Web3, config: Dict[str, Any]) -> AerodromeV2:
    """Initialize Aerodrome V2."""
    return AerodromeV2(mock_web3, config)

@pytest.fixture
async def v3_dex(mock_web3: Web3, config: Dict[str, Any]) -> AerodromeV3:
    """Initialize Aerodrome V3."""
    return AerodromeV3(mock_web3, config)

@pytest.mark.asyncio
class TestAerodromeV2:
    """Test Aerodrome V2 functionality."""
    
    async def test_get_pool_address(self, v2_dex: AerodromeV2, config: Dict[str, Any]):
        """Test getting pool address."""
        # Test stable pool
        pool = await v2_dex.get_pool_address(
            config["tokens"]["WETH"],
            config["tokens"]["USDC"],
            True
        )
        pool_key = f"{config['tokens']['WETH']}/{config['tokens']['USDC']}"
        assert pool == config["dexes"]["aerodrome"]["pools"][pool_key]["stable"]
        
        # Test volatile pool
        pool = await v2_dex.get_pool_address(
            config["tokens"]["WETH"],
            config["tokens"]["USDC"],
            False
        )
        pool_key = f"{config['tokens']['WETH']}/{config['tokens']['USDC']}"
        assert pool == config["dexes"]["aerodrome"]["pools"][pool_key]["volatile"]
        
    async def test_get_reserves(self, v2_dex: AerodromeV2, config: Dict[str, Any]):
        """Test getting pool reserves."""
        # Get pool
        pool = await v2_dex.get_pool_address(
            config["tokens"]["WETH"],
            config["tokens"]["USDC"],
            False
        )
        
        # Get reserves
        reserve0, reserve1 = await v2_dex.get_reserves(pool)
        assert reserve0 == Decimal("1000")  # 1000 WETH
        assert reserve1 == Decimal("2000000")  # 2M USDC
        
    async def test_get_amounts_out(self, v2_dex: AerodromeV2, config: Dict[str, Any]):
        """Test calculating output amounts."""
        # Test WETH -> USDC
        amounts = await v2_dex.get_amounts_out(
            TEST_AMOUNT,
            [config["tokens"]["WETH"], config["tokens"]["USDC"]]
        )
        assert len(amounts) == 2
        assert amounts[0] == TEST_AMOUNT
        assert amounts[1] == TEST_AMOUNT * 2000  # 1 WETH = 2000 USDC
        
    async def test_get_pool_fee(self, v2_dex: AerodromeV2, config: Dict[str, Any]):
        """Test getting pool fee."""
        # Get volatile pool
        pool = await v2_dex.get_pool_address(
            config["tokens"]["WETH"],
            config["tokens"]["USDC"],
            False
        )
        print(f"V2 volatile pool address: {pool}")
        
        # Get fee
        fee = await v2_dex.get_pool_fee(pool)
        print(f"V2 volatile pool fee: {fee}")
        expected_fee = (Decimal("500") / Decimal("1000000")).quantize(Decimal("0.000001"))
        assert fee == expected_fee  # 0.05% = 500 bps for volatile pools
        
        # Get stable pool
        pool = await v2_dex.get_pool_address(
            config["tokens"]["WETH"],
            config["tokens"]["USDC"],
            True
        )
        print(f"V2 stable pool address: {pool}")
        
        fee = await v2_dex.get_pool_fee(pool)
        print(f"V2 stable pool fee: {fee}")
        expected_fee = (Decimal("100") / Decimal("1000000")).quantize(Decimal("0.000001"))
        assert fee == expected_fee  # 0.01% = 100 bps for stable pools
        
    async def test_validate_pool(self, v2_dex: AerodromeV2, config: Dict[str, Any]):
        """Test pool validation."""
        # Get pool
        pool = await v2_dex.get_pool_address(
            config["tokens"]["WETH"],
            config["tokens"]["USDC"],
            False
        )
        
        # Validate
        is_valid = await v2_dex.validate_pool(pool)
        assert is_valid is True

@pytest.mark.asyncio
class TestAerodromeV3:
    """Test Aerodrome V3 functionality."""
    
    async def test_get_pool_address(self, v3_dex: AerodromeV3, config: Dict[str, Any]):
        """Test getting pool address."""
        # Test with different fee tiers
        for fee in [100, 500, 3000]:
            pool = await v3_dex.get_pool_address(
                config["tokens"]["WETH"],
                config["tokens"]["USDC"],
                fee
            )
            pool_key = f"{config['tokens']['WETH']}/{config['tokens']['USDC']}"
            assert pool == config["dexes"]["aerodrome_v3"]["pools"][pool_key][f"fee_{fee}"]
            
    async def test_get_reserves(self, v3_dex: AerodromeV3, config: Dict[str, Any]):
        """Test getting pool reserves."""
        # Get pool
        pool = await v3_dex.get_pool_address(
            config["tokens"]["WETH"],
            config["tokens"]["USDC"],
            3000
        )
        
        # Get reserves
        reserve0, reserve1 = await v3_dex.get_reserves(pool)
        assert reserve0 > 0
        assert reserve1 > 0
        
    async def test_get_amounts_out(self, v3_dex: AerodromeV3, config: Dict[str, Any]):
        """Test calculating output amounts."""
        # Test WETH -> USDC
        amounts = await v3_dex.get_amounts_out(
            TEST_AMOUNT,
            [config["tokens"]["WETH"], config["tokens"]["USDC"]],
            3000
        )
        assert len(amounts) == 2
        assert amounts[0] == TEST_AMOUNT
        assert amounts[1] == TEST_AMOUNT * 2000  # 1 WETH = 2000 USDC
        
    async def test_get_pool_fee(self, v3_dex: AerodromeV3, config: Dict[str, Any]):
        """Test getting pool fee."""
        # Test different fee tiers
        for fee_bps in [100, 500, 3000]:
            pool = await v3_dex.get_pool_address(
                config["tokens"]["WETH"],
                config["tokens"]["USDC"],
                fee_bps
            )
            print(f"V3 pool address for {fee_bps} bps: {pool}")
            
            fee = await v3_dex.get_pool_fee(pool)
            print(f"V3 pool fee for {fee_bps} bps: {fee}")
            expected_fee = (Decimal(str(fee_bps)) / Decimal("1000000")).quantize(Decimal("0.000001"))
            assert fee == expected_fee
            
    async def test_validate_pool(self, v3_dex: AerodromeV3, config: Dict[str, Any]):
        """Test pool validation."""
        # Get pool
        pool = await v3_dex.get_pool_address(
            config["tokens"]["WETH"],
            config["tokens"]["USDC"],
            3000
        )
        
        # Validate
        is_valid = await v3_dex.validate_pool(pool)
        assert is_valid is True
