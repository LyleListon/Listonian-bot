"""Mock contracts for PancakeSwap V3 testing."""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from web3.types import ChecksumAddress

from src.core.dex.protocols.pancakeswap.types import FeeTier, PoolState, Slot0


class MockPancakeV3Factory:
    """Mock PancakeSwap V3 factory contract."""

    def __init__(self):
        """Initialize mock factory."""
        self.pools: Dict[str, 'MockPancakeV3Pool'] = {}

    def create_pool(
        self,
        token0: ChecksumAddress,
        token1: ChecksumAddress,
        fee: FeeTier
    ) -> 'MockPancakeV3Pool':
        """Create new pool.
        
        Args:
            token0: First token address
            token1: Second token address
            fee: Fee tier
            
        Returns:
            Mock pool instance
        """
        key = f"{token0}-{token1}-{fee.value}"
        if key not in self.pools:
            self.pools[key] = MockPancakeV3Pool(token0, token1, fee)
        return self.pools[key]

    def get_pool(
        self,
        token0: ChecksumAddress,
        token1: ChecksumAddress,
        fee: FeeTier
    ) -> Optional[ChecksumAddress]:
        """Get pool address.
        
        Args:
            token0: First token address
            token1: Second token address
            fee: Fee tier
            
        Returns:
            Pool address if exists
        """
        key = f"{token0}-{token1}-{fee.value}"
        if key in self.pools:
            return f"0x{key}"  # Mock address
        return "0x0000000000000000000000000000000000000000"


class MockPancakeV3Pool:
    """Mock PancakeSwap V3 pool contract."""

    def __init__(
        self,
        token0: ChecksumAddress,
        token1: ChecksumAddress,
        fee: FeeTier
    ):
        """Initialize mock pool.
        
        Args:
            token0: First token address
            token1: Second token address
            fee: Fee tier
        """
        self.token0 = token0
        self.token1 = token1
        self.fee = fee
        
        # Initial state
        self.liquidity = 1_000_000  # 1M units
        self.sqrt_price_x96 = 2 ** 96  # 1:1 price
        self.tick = 0
        self.fee_growth_global0 = 0
        self.fee_growth_global1 = 0
        self.protocol_fees = (0, 0)
        
        # Observations
        self.observations: List[Tuple[int, int, int, bool]] = [
            (0, 0, 0, True)  # timestamp, tickCumulative, secondsPerLiquidityCumulative, initialized
        ]
        
        # Ticks
        self.ticks: Dict[int, Dict] = {}
        
        # Events
        self.events: List[Dict] = []

    def slot0(self) -> Slot0:
        """Get slot0 data.
        
        Returns:
            Current slot0 data
        """
        return Slot0(
            sqrt_price_x96=self.sqrt_price_x96,
            tick=self.tick,
            observation_index=0,
            observation_cardinality=1,
            observation_cardinality_next=1,
            fee_protocol=0,
            unlocked=True
        )

    def get_reserves(self) -> Tuple[int, int, int]:
        """Get current reserves.
        
        Returns:
            Tuple of (reserve0, reserve1, timestamp)
        """
        return (
            self.liquidity,
            self.liquidity,
            0  # timestamp
        )

    def observe(
        self,
        seconds_ago: List[int]
    ) -> Tuple[List[int], List[int]]:
        """Get observations.
        
        Args:
            seconds_ago: List of seconds ago to query
            
        Returns:
            Tuple of (tickCumulatives, secondsPerLiquidityCumulatives)
        """
        return (
            [0] * len(seconds_ago),  # tickCumulatives
            [0] * len(seconds_ago)   # secondsPerLiquidityCumulatives
        )

    def swap(
        self,
        recipient: ChecksumAddress,
        zero_for_one: bool,
        amount_specified: int,
        sqrt_price_limit_x96: int,
        data: bytes
    ) -> Tuple[int, int]:
        """Execute swap.
        
        Args:
            recipient: Recipient address
            zero_for_one: True if swapping token0 for token1
            amount_specified: Amount to swap
            sqrt_price_limit_x96: Price limit
            data: Callback data
            
        Returns:
            Tuple of (amount0, amount1)
        """
        # Calculate amounts
        amount0 = amount_specified if zero_for_one else 0
        amount1 = 0 if zero_for_one else amount_specified
        
        # Update state
        self.sqrt_price_x96 = sqrt_price_limit_x96
        
        # Emit event
        self.events.append({
            'event': 'Swap',
            'args': {
                'sender': "0x0000000000000000000000000000000000000000",
                'recipient': recipient,
                'amount0': amount0,
                'amount1': amount1,
                'sqrtPriceX96': sqrt_price_limit_x96,
                'liquidity': self.liquidity,
                'tick': self.tick
            }
        })
        
        return amount0, amount1


class MockPancakeV3Quoter:
    """Mock PancakeSwap V3 quoter contract."""

    def quote_exact_input_single(
        self,
        token_in: ChecksumAddress,
        token_out: ChecksumAddress,
        fee: int,
        amount_in: int,
        sqrt_price_limit_x96: int
    ) -> Tuple[int, int, int, int]:
        """Quote exact input swap.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            fee: Fee amount
            amount_in: Input amount
            sqrt_price_limit_x96: Price limit
            
        Returns:
            Tuple of (amountOut, sqrtPriceX96After, tickAfter, fee)
        """
        # Mock 1:1 price with 0.3% fee
        amount_out = int(amount_in * 0.997)
        return (
            amount_out,
            sqrt_price_limit_x96,
            0,  # tickAfter
            int(amount_in * 0.003)  # fee
        )

    def quote_exact_output_single(
        self,
        token_in: ChecksumAddress,
        token_out: ChecksumAddress,
        fee: int,
        amount_out: int,
        sqrt_price_limit_x96: int
    ) -> Tuple[int, int, int, int]:
        """Quote exact output swap.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            fee: Fee amount
            amount_out: Output amount
            sqrt_price_limit_x96: Price limit
            
        Returns:
            Tuple of (amountIn, sqrtPriceX96After, tickAfter, fee)
        """
        # Mock 1:1 price with 0.3% fee
        amount_in = int(amount_out / 0.997)
        return (
            amount_in,
            sqrt_price_limit_x96,
            0,  # tickAfter
            int(amount_in * 0.003)  # fee
        )