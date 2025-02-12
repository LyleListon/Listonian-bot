"""SwapBased protocol implementation."""

from decimal import Decimal
from typing import Dict

from .dex import SwapBased

__all__ = ['SwapBased']

# Protocol Constants
PROTOCOL_NAME = "SwapBased"
DEFAULT_FEE = Decimal('0.003')  # 0.3%
MIN_LIQUIDITY = Decimal('1000')  # Minimum USD value for valid pools

# Contract Addresses (Base Network)
ADDRESSES: Dict[str, str] = {
    'factory': '0x36218F2455Ae5dE2c3FC2952f6c9544C8D419D91',
    'router': '0x8c1A3cF8f83074169FE5D7aD50B978e1cD6b37c7',
    'weth': '0x4200000000000000000000000000000000000006',
}

# Common Token Addresses
TOKENS: Dict[str, str] = {
    'WETH': '0x4200000000000000000000000000000000000006',
    'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    'DAI': '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb',
    'USDbC': '0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA',
}

# Initialization helper
def create_swapbased(web3_manager) -> SwapBased:
    """Create SwapBased instance with default addresses.
    
    Args:
        web3_manager: Web3 manager instance
        
    Returns:
        Initialized SwapBased instance
    """
    return SwapBased(
        web3_manager=web3_manager,
        factory_address=ADDRESSES['factory'],
        router_address=ADDRESSES['router']
    )