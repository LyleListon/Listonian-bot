"""
Core DEX interaction module.

This module provides:
1. DEX interface implementations
2. Pool data retrieval
3. Price calculations
4. Liquidity validation
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from web3.contract import Contract

logger = logging.getLogger(__name__)


def get_token_symbol(address: str, token_map: Dict[str, str]) -> str:
    """Get token symbol from address using case-insensitive matching."""
    return next((k for k, v in token_map.items() if v.lower() == address.lower()), "")


def generate_pool_key(
    dex_name: str, pool_address: str, token0: str, token1: str
) -> str:
    """Generate unique pool key."""
    return f"{dex_name}_{pool_address}_{token0}_{token1}".lower()


async def get_pool_data(contract: Contract, dex_name: str) -> Dict[str, Any]:
    """Get pool data based on DEX type."""
    if not contract:
        raise Exception("Invalid contract")

    if dex_name not in ["baseswap", "pancakeswap", "sushiswap", "swapbased"]:
        raise ValueError(f"Unsupported DEX: {dex_name}")

    try:
        if dex_name == "swapbased":
            current_state = await contract.functions.currentState().call()
            return {
                "sqrtPriceX96": current_state[0],
                "tick": current_state[1],
                "liquidity": current_state[2],
            }
        else:
            # Standard V3 pool interface
            slot0 = await contract.functions.slot0().call()
            liquidity = await contract.functions.liquidity().call()
            return {
                "sqrtPriceX96": slot0[0],
                "tick": slot0[1],
                "liquidity": str(liquidity),
            }
    except Exception as e:
        logger.error(f"Error getting pool data: {e}")
        raise


def calculate_price(
    pool_data: Dict[str, Any], decimals0: int, decimals1: int
) -> Decimal:
    """Calculate token price from pool data."""
    try:
        sqrt_price_x96 = Decimal(pool_data["sqrtPriceX96"])
        # Convert Q64.96 fixed point to decimal
        price = (sqrt_price_x96 * sqrt_price_x96) / (Decimal(2) ** Decimal(192))

        # Adjust for decimals
        decimal_adjustment = Decimal(10) ** Decimal(decimals1 - decimals0)
        price = price * decimal_adjustment

        return price
    except Exception as e:
        logger.error(f"Error calculating price: {e}")
        raise


def validate_liquidity(pool_data: Dict[str, Any], min_liquidity: Decimal) -> bool:
    """Validate pool has sufficient liquidity."""
    try:
        liquidity = Decimal(pool_data["liquidity"])
        return liquidity >= min_liquidity
    except Exception as e:
        logger.error(f"Error validating liquidity: {e}")
        return False


class BaseDEX:
    """Base DEX implementation."""

    def __init__(self, name: str, version: int = 3):
        self.name = name
        self.version = version
        self._lock = asyncio.Lock()

    async def get_pool_data(
        self, contract: Contract, validate: bool = True
    ) -> Dict[str, Any]:
        """Get pool data with validation."""
        async with self._lock:
            data = await get_pool_data(contract, self.name)
            if validate:
                if not validate_liquidity(data, Decimal("0")):
                    raise ValueError("Invalid pool liquidity")
            return data

    async def calculate_amounts(
        self, pool_data: Dict[str, Any], amount_in: Decimal, swap_direction: bool
    ) -> Dict[str, Decimal]:
        """Calculate swap amounts."""
        raise NotImplementedError("Must be implemented by DEX class")


class SwapBasedV3(BaseDEX):
    """SwapBased V3 implementation."""

    def __init__(self):
        super().__init__("swapbased", 3)

    async def calculate_amounts(
        self, pool_data: Dict[str, Any], amount_in: Decimal, swap_direction: bool
    ) -> Dict[str, Decimal]:
        """Calculate amounts for SwapBased V3."""
        # SwapBased specific implementation
        sqrt_price = Decimal(pool_data["sqrtPriceX96"])
        liquidity = Decimal(pool_data["liquidity"])
        tick = int(pool_data["tick"])

        # TODO: Implement SwapBased V3 specific calculations
        raise NotImplementedError("SwapBased V3 calculations not implemented")
