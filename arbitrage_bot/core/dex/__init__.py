"""DEX module initialization."""

from .dex_manager import DexManager, create_dex_manager
from .base_dex import BaseDEX
from .base_dex_v2 import BaseDEXV2
from .base_dex_v3 import BaseDEXV3
from .baseswap import BaseSwap
from .rocketswap_v3 import RocketSwapV3
from .swapbased import SwapBased

__all__ = [
    'DexManager',
    'create_dex_manager',
    'BaseDEX',
    'BaseDEXV2',
    'BaseDEXV3',
    'BaseSwap',
    'RocketSwapV3',
    'SwapBased'
]

# Re-export for backward compatibility
DEXManager = DexManager
