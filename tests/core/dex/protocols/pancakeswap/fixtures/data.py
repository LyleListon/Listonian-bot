"""Test data fixtures for PancakeSwap V3 testing."""

from decimal import Decimal
from typing import Dict, List, NamedTuple

from web3.types import ChecksumAddress

from src.core.dex.interfaces.types import Token, TokenAmount
from src.core.dex.protocols.pancakeswap.types import FeeTier, PoolState, Slot0

# Mock addresses
ADDRESSES: Dict[str, str] = {
    'factory': '0x1111111111111111111111111111111111111111',
    'router': '0x2222222222222222222222222222222222222222',
    'quoter': '0x3333333333333333333333333333333333333333',
    'weth': '0x4444444444444444444444444444444444444444',
    'usdc': '0x5555555555555555555555555555555555555555',
    'dai': '0x6666666666666666666666666666666666666666',
}

# Mock tokens
TOKENS = {
    'WETH': Token(
        address=ADDRESSES['weth'],
        symbol='WETH',
        name='Wrapped Ether',
        decimals=18
    ),
    'USDC': Token(
        address=ADDRESSES['usdc'],
        symbol='USDC',
        name='USD Coin',
        decimals=6
    ),
    'DAI': Token(
        address=ADDRESSES['dai'],
        symbol='DAI',
        name='Dai Stablecoin',
        decimals=18
    ),
}

# Mock amounts
AMOUNTS = {
    'WETH_1': TokenAmount(
        token=TOKENS['WETH'],
        amount=Decimal('1.0')
    ),
    'USDC_1000': TokenAmount(
        token=TOKENS['USDC'],
        amount=Decimal('1000.0')
    ),
    'DAI_1000': TokenAmount(
        token=TOKENS['DAI'],
        amount=Decimal('1000.0')
    ),
}

# Mock pool states
POOL_STATES = {
    'WETH_USDC': PoolState(
        liquidity=1_000_000,  # 1M units
        sqrt_price_x96=2 ** 96,  # 1:1 price
        tick=0,
        tick_spacing=60,  # For 0.3% fee tier
        fee=FeeTier.MEDIUM,
        token0=TOKENS['WETH'],
        token1=TOKENS['USDC'],
        observation_index=0,
        observation_cardinality=1,
        observation_cardinality_next=1,
        fee_protocol=0,
        unlocked=True
    ),
    'USDC_DAI': PoolState(
        liquidity=10_000_000,  # 10M units
        sqrt_price_x96=2 ** 96,  # 1:1 price
        tick=0,
        tick_spacing=10,  # For 0.05% fee tier
        fee=FeeTier.LOW,
        token0=TOKENS['USDC'],
        token1=TOKENS['DAI'],
        observation_index=0,
        observation_cardinality=1,
        observation_cardinality_next=1,
        fee_protocol=0,
        unlocked=True
    ),
}

# Test scenarios
class SwapScenario(NamedTuple):
    """Swap test scenario."""
    name: str
    input_amount: TokenAmount
    output_token: Token
    fee_tier: FeeTier
    expected_output: TokenAmount
    expected_price_impact: Decimal


SWAP_SCENARIOS = [
    SwapScenario(
        name="WETH to USDC (0.3% fee)",
        input_amount=AMOUNTS['WETH_1'],
        output_token=TOKENS['USDC'],
        fee_tier=FeeTier.MEDIUM,
        expected_output=TokenAmount(
            token=TOKENS['USDC'],
            amount=Decimal('1000.0')  # 1 ETH = 1000 USDC
        ),
        expected_price_impact=Decimal('0.3')  # 0.3%
    ),
    SwapScenario(
        name="USDC to DAI (0.05% fee)",
        input_amount=AMOUNTS['USDC_1000'],
        output_token=TOKENS['DAI'],
        fee_tier=FeeTier.LOW,
        expected_output=TokenAmount(
            token=TOKENS['DAI'],
            amount=Decimal('999.5')  # Almost 1:1 with small fee
        ),
        expected_price_impact=Decimal('0.05')  # 0.05%
    ),
]

# Error scenarios
class ErrorScenario(NamedTuple):
    """Error test scenario."""
    name: str
    input_amount: TokenAmount
    output_token: Token
    fee_tier: FeeTier
    expected_error: str


ERROR_SCENARIOS = [
    ErrorScenario(
        name="Non-existent pool",
        input_amount=AMOUNTS['WETH_1'],
        output_token=TOKENS['DAI'],
        fee_tier=FeeTier.HIGH,
        expected_error="Pool does not exist"
    ),
    ErrorScenario(
        name="Insufficient liquidity",
        input_amount=TokenAmount(
            token=TOKENS['WETH'],
            amount=Decimal('1000000.0')  # Very large amount
        ),
        output_token=TOKENS['USDC'],
        fee_tier=FeeTier.MEDIUM,
        expected_error="Insufficient liquidity"
    ),
]

# Price scenarios
class PriceScenario(NamedTuple):
    """Price test scenario."""
    name: str
    base_token: Token
    quote_token: Token
    fee_tier: FeeTier
    initial_price: Decimal
    price_updates: List[Decimal]


PRICE_SCENARIOS = [
    PriceScenario(
        name="WETH/USDC price movement",
        base_token=TOKENS['WETH'],
        quote_token=TOKENS['USDC'],
        fee_tier=FeeTier.MEDIUM,
        initial_price=Decimal('1000.0'),
        price_updates=[
            Decimal('1010.0'),  # +1%
            Decimal('990.0'),   # -2%
            Decimal('1005.0'),  # +1.5%
        ]
    ),
    PriceScenario(
        name="USDC/DAI stable price",
        base_token=TOKENS['USDC'],
        quote_token=TOKENS['DAI'],
        fee_tier=FeeTier.LOW,
        initial_price=Decimal('1.0'),
        price_updates=[
            Decimal('1.001'),  # +0.1%
            Decimal('0.999'),  # -0.2%
            Decimal('1.0'),    # +0.1%
        ]
    ),
]