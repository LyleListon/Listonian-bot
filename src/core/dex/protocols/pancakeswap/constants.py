"""Constants for PancakeSwap V3."""

from decimal import Decimal
from typing import Dict

from .types import FeeTier

# Protocol name
PROTOCOL_NAME = "PancakeSwap V3"

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

# Fee Tiers
FEE_TIERS = [
    FeeTier.LOWEST,   # 0.01%
    FeeTier.LOW,      # 0.05%
    FeeTier.MEDIUM,   # 0.3%
    FeeTier.HIGH,     # 1%
]

# Fee amounts in basis points
FEE_AMOUNTS = {
    FeeTier.LOWEST: 100,   # 0.01%
    FeeTier.LOW: 500,      # 0.05%
    FeeTier.MEDIUM: 3000,  # 0.3%
    FeeTier.HIGH: 10000,   # 1%
}

# Tick spacing by fee tier
TICK_SPACINGS = {
    FeeTier.LOWEST: 1,
    FeeTier.LOW: 10,
    FeeTier.MEDIUM: 60,
    FeeTier.HIGH: 200,
}

# Price limits
MIN_PRICE = Decimal("0.00001")
MAX_PRICE = Decimal("100000")

# Pool constants
MIN_LIQUIDITY = 100  # Minimum liquidity to consider pool active
MAX_TICK_TRAVEL = 2000  # Maximum tick travel in a single swap

# Cache settings
POOL_CACHE_SIZE = 100  # Maximum number of pools to cache
OBSERVATION_CACHE_SIZE = 4  # Price observations per pool to cache

# Gas limits
GAS_LIMITS = {
    'create_pool': 5000000,
    'add_liquidity': 1000000,
    'remove_liquidity': 800000,
    'swap': 300000,
    'collect_fees': 200000,
}

# Default settings
DEFAULT_SLIPPAGE = Decimal("0.005")  # 0.5%
DEFAULT_DEADLINE = 60  # 1 minute
DEFAULT_FEE_TIER = FeeTier.MEDIUM

# Event signatures
EVENTS = {
    'pool_created': '0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118',
    'swap': '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67',
    'increase_liquidity': '0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f',
    'decrease_liquidity': '0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4',
    'collect': '0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0',
}

# Error messages
ERRORS = {
    'invalid_fee_tier': 'Invalid fee tier',
    'invalid_price_limit': 'Price outside allowed range',
    'insufficient_liquidity': 'Insufficient liquidity',
    'price_impact_high': 'Price impact too high',
    'pool_not_found': 'Pool does not exist',
    'tick_not_initialized': 'Tick not initialized',
    'zero_liquidity': 'Zero liquidity position',
}