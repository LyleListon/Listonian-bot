"""DEX type definitions."""

from enum import Enum, auto


class DEXType(Enum):
    """Supported DEX types."""

    UNISWAP_V2 = auto()
    UNISWAP_V3 = auto()
    BASESWAP = auto()
    PANCAKESWAP = auto()
    AERODROME_V2 = auto()
    AERODROME_V3 = auto()
    SWAPBASED = auto()
