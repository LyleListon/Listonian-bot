# PancakeSwap V3 Math

## Overview
Mathematical utilities for PancakeSwap V3's concentrated liquidity implementation. These utilities handle tick math, liquidity calculations, and swap computations.

## Components

### 1. Tick Math
Handles tick-based price calculations:
```python
from src.core.dex.protocols.pancakeswap.math import (
    price_to_tick,
    tick_to_price,
    get_sqrt_ratio_at_tick
)

# Convert price to tick
tick = price_to_tick(Decimal("2000.0"))

# Convert tick to price
price = tick_to_price(tick)

# Get sqrt price for tick
sqrt_price = get_sqrt_ratio_at_tick(tick)
```

### 2. Liquidity Math
Handles concentrated liquidity calculations:
```python
from src.core.dex.protocols.pancakeswap.math import (
    get_liquidity_for_amounts,
    get_amounts_for_liquidity
)

# Calculate liquidity from amounts
liquidity = get_liquidity_for_amounts(
    sqrt_ratio_current,
    sqrt_ratio_lower,
    sqrt_ratio_upper,
    amount0,
    amount1
)

# Calculate amounts from liquidity
amount0, amount1 = get_amounts_for_liquidity(
    sqrt_ratio_current,
    sqrt_ratio_lower,
    sqrt_ratio_upper,
    liquidity
)
```

### 3. Swap Math
Handles swap calculations and price impact:
```python
from src.core.dex.protocols.pancakeswap.math import (
    compute_swap_step,
    estimate_swap
)

# Compute single swap step
sqrt_ratio_next, amount_in, amount_out, fee = compute_swap_step(
    sqrt_ratio_current,
    sqrt_ratio_target,
    liquidity,
    amount_remaining,
    fee_pips=3000,  # 0.3%
    exact_in=True,
    zero_for_one=True
)

# Estimate full swap
amount_in, amount_out, sqrt_ratio_next = estimate_swap(
    sqrt_ratio_current,
    liquidity,
    amount,
    fee_pips=3000,
    exact_in=True,
    zero_for_one=True
)
```

## Constants

### Price Range
```python
MIN_TICK = -887272  # Minimum tick
MAX_TICK = 887272   # Maximum tick
Q96 = 2 ** 96      # Q96 precision

MIN_SQRT_RATIO = 4295128739  # Minimum sqrt price
MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342  # Maximum
```

### Fee Tiers
```python
FEE_LOW = 500      # 0.05%
FEE_MEDIUM = 3000  # 0.3%
FEE_HIGH = 10000   # 1%
```

## Implementation Details

### 1. Price Representation
- Prices are stored as Q96.96 fixed-point numbers
- Square root prices are used for better precision
- Tick spacing ensures price points are evenly distributed

### 2. Liquidity Calculation
- Uses virtual reserves concept
- Handles concentrated liquidity ranges
- Supports single-sided deposits
- Accounts for price range overlaps

### 3. Swap Computation
- Step-by-step swap execution
- Handles exact input/output swaps
- Includes fee calculations
- Supports multi-pool routes

## Best Practices

1. Price Handling
```python
# Always use Decimal for price calculations
price = Decimal("2000.0")

# Convert to sqrt price before operations
sqrt_price = price_to_sqrt_price_x96(price)
```

2. Tick Management
```python
# Ensure ticks are within bounds
tick = min(max(tick, MIN_TICK), MAX_TICK)

# Use proper tick spacing
TICK_SPACING = 60  # For 0.3% fee tier
tick = (tick // TICK_SPACING) * TICK_SPACING
```

3. Liquidity Safety
```python
# Validate liquidity is non-zero
if liquidity <= 0:
    raise ValueError("Invalid liquidity")

# Check price range is valid
if sqrt_ratio_a > sqrt_ratio_b:
    sqrt_ratio_a, sqrt_ratio_b = sqrt_ratio_b, sqrt_ratio_a
```

4. Swap Safety
```python
# Add slippage protection
min_out = amount_out * Decimal("0.995")  # 0.5% slippage

# Check price impact
if price_impact > Decimal("0.01"):  # 1%
    logger.warning("High price impact")
```

## References
- [Uniswap V3 Whitepaper](https://uniswap.org/whitepaper-v3.pdf)
- [Uniswap V3 Math](https://github.com/Uniswap/v3-core/blob/main/contracts/libraries)
- [PancakeSwap V3 Docs](https://docs.pancakeswap.finance/code/v3)

Last Updated: 2025-02-10