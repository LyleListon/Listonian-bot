"""Pytest fixtures for PancakeSwap V3 testing."""

import pytest
from unittest.mock import MagicMock

from src.core.blockchain import Web3Manager
from src.core.dex.interfaces.types import Token, TokenAmount
from src.core.dex.protocols.pancakeswap import PancakeSwapV3
from src.core.dex.protocols.pancakeswap.types import FeeTier, PoolState, Slot0

from .fixtures.contracts import (
    MockPancakeV3Factory,
    MockPancakeV3Pool,
    MockPancakeV3Quoter,
)
from .fixtures.data import (
    ADDRESSES,
    AMOUNTS,
    ERROR_SCENARIOS,
    POOL_STATES,
    PRICE_SCENARIOS,
    SWAP_SCENARIOS,
    TOKENS,
)


@pytest.fixture
def web3():
    """Mock Web3 manager."""
    mock = MagicMock(spec=Web3Manager)
    mock.provider.web3.eth.default_account = (
        "0x7777777777777777777777777777777777777777"
    )
    return mock


@pytest.fixture
def factory():
    """Mock factory contract."""
    return MockPancakeV3Factory()


@pytest.fixture
def quoter():
    """Mock quoter contract."""
    return MockPancakeV3Quoter()


@pytest.fixture
def dex(web3, factory, quoter):
    """PancakeSwap V3 instance with mock contracts."""
    dex = PancakeSwapV3(
        web3_manager=web3,
        factory_address=ADDRESSES['factory'],
        router_address=ADDRESSES['router'],
        quoter_address=ADDRESSES['quoter']
    )
    
    # Replace contract instances with mocks
    dex._factory = factory
    dex._router = MagicMock()
    dex.quoter._quoter = quoter
    
    return dex


@pytest.fixture
def tokens():
    """Test tokens."""
    return TOKENS


@pytest.fixture
def amounts():
    """Test amounts."""
    return AMOUNTS


@pytest.fixture
def pool_states():
    """Test pool states."""
    return POOL_STATES


@pytest.fixture
def weth_usdc_pool(factory, tokens):
    """WETH/USDC pool."""
    return factory.create_pool(
        tokens['WETH'].address,
        tokens['USDC'].address,
        FeeTier.MEDIUM
    )


@pytest.fixture
def usdc_dai_pool(factory, tokens):
    """USDC/DAI pool."""
    return factory.create_pool(
        tokens['USDC'].address,
        tokens['DAI'].address,
        FeeTier.LOW
    )


@pytest.fixture
def swap_scenarios():
    """Swap test scenarios."""
    return SWAP_SCENARIOS


@pytest.fixture
def error_scenarios():
    """Error test scenarios."""
    return ERROR_SCENARIOS


@pytest.fixture
def price_scenarios():
    """Price test scenarios."""
    return PRICE_SCENARIOS


@pytest.fixture
def mock_pool():
    """Create mock pool with custom parameters."""
    def _create_pool(
        token0: Token,
        token1: Token,
        fee: FeeTier,
        liquidity: int = 1_000_000,
        sqrt_price_x96: int = 2 ** 96,
        tick: int = 0
    ) -> MockPancakeV3Pool:
        pool = MockPancakeV3Pool(token0.address, token1.address, fee)
        pool.liquidity = liquidity
        pool.sqrt_price_x96 = sqrt_price_x96
        pool.tick = tick
        return pool
        
    return _create_pool


@pytest.fixture
def mock_price_update():
    """Create mock price update event."""
    def _create_event(
        pool: MockPancakeV3Pool,
        new_sqrt_price_x96: int,
        new_tick: int
    ) -> None:
        pool.sqrt_price_x96 = new_sqrt_price_x96
        pool.tick = new_tick
        pool.events.append({
            'event': 'Swap',
            'args': {
                'sqrtPriceX96': new_sqrt_price_x96,
                'tick': new_tick,
                'liquidity': pool.liquidity
            }
        })
        
    return _create_event