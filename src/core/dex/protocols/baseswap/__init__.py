"""BaseSwap protocol implementation."""

from decimal import Decimal
from typing import Dict

from .dex import BaseSwap

__all__ = ['BaseSwap']

# Protocol Constants
PROTOCOL_NAME = "BaseSwap"
DEFAULT_FEE = Decimal('0.003')  # 0.3%
MIN_LIQUIDITY = Decimal('1000')  # Minimum USD value for valid pools

# Contract Addresses (Base Network)
ADDRESSES: Dict[str, str] = {
    'factory': '0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB',
    'router': '0x327Df1E6de05895d2ab08513aaDD9313Fe505d86',
    'weth': '0x4200000000000000000000000000000000000006',
}

# Common Token Addresses
TOKENS: Dict[str, str] = {
    'WETH': '0x4200000000000000000000000000000000000006',
    'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    'DAI': '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb',
}

# Initialization helper
def create_baseswap(web3_manager) -> BaseSwap:
    """Create BaseSwap instance with default addresses.
    
    Args:
        web3_manager: Web3 manager instance
        
    Returns:
        Initialized BaseSwap instance
    """
    return BaseSwap(
        web3_manager=web3_manager,
        factory_address=ADDRESSES['factory'],
        router_address=ADDRESSES['router']
    )