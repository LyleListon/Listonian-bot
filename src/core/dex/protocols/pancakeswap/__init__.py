"""PancakeSwap V3 protocol implementation."""

from decimal import Decimal
from typing import Dict

from .constants import ADDRESSES, DEFAULT_FEE_TIER
from .dex import PancakeSwapV3
from .types import FeeTier

__all__ = [
    'PancakeSwapV3',
    'FeeTier',
    'create_pancakeswap',
]

# Protocol Constants
PROTOCOL_NAME = "PancakeSwap V3"
DEFAULT_FEE = Decimal('0.003')  # 0.3%
MIN_LIQUIDITY = Decimal('1000')  # Minimum USD value for valid pools

# Contract Addresses (Base Network)
ADDRESSES: Dict[str, str] = {
    'factory': '0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865',
    'router': '0x1b81D678ffb9C0263b24A97847620C99d213eB14',
    'quoter': '0xB048Bbc1Ee6b733FFfCFb9e9CeF7375518e25997',
    'position_manager': '0x46A15B0b27311cedF172AB29E4f4766fbE7F4364',
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
def create_pancakeswap(web3_manager) -> PancakeSwapV3:
    """Create PancakeSwap V3 instance with default addresses.
    
    Args:
        web3_manager: Web3 manager instance
        
    Returns:
        Initialized PancakeSwap V3 instance
    """
    return PancakeSwapV3(
        web3_manager=web3_manager,
        factory_address=ADDRESSES['factory'],
        router_address=ADDRESSES['router'],
        quoter_address=ADDRESSES['quoter']
    )