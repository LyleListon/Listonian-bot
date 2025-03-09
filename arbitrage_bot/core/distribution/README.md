# Distribution System

The Distribution system manages trade execution across multiple DEXes with intelligent allocation and risk management.

## Features

- Dynamic trade allocation across DEXes
- Risk-based exposure management
- Automatic rebalancing
- Performance-based scoring
- Real-time monitoring
- Integration with storage and memory systems

## Components

### DistributionConfig

Configuration for the distribution system:

```python
from decimal import Decimal
from arbitrage_bot.core.distribution import DistributionConfig

config = DistributionConfig(
    max_exposure_per_dex=Decimal("100000"),  # Maximum exposure per DEX
    max_exposure_per_pair=Decimal("50000"),   # Maximum exposure per trading pair
    min_liquidity_threshold=Decimal("10000"), # Minimum required liquidity
    rebalance_threshold=Decimal("0.2"),       # 20% imbalance triggers rebalancing
    gas_price_weight=0.2,                     # Weight for gas price in scoring
    liquidity_weight=0.3,                     # Weight for liquidity in scoring
    volume_weight=0.3,                        # Weight for volume in scoring
    success_rate_weight=0.2                   # Weight for success rate in scoring
)
```

### DistributionManager

Core manager for trade distribution:

```python
from arbitrage_bot.core.distribution import DistributionManager
from arbitrage_bot.core.memory import MemoryBank

# Initialize with memory bank for caching
memory = MemoryBank()
distribution = DistributionManager(config, memory_bank=memory)

# Get optimal DEX allocation for a trade
allocations = distribution.get_dex_allocation(
    amount=Decimal("10000"),
    pair="ETH/USDC"
)

# Update exposure after trade execution
distribution.update_exposure(
    dex="uniswap",
    pair="ETH/USDC",
    amount=Decimal("5000")
)

# Check if rebalancing is needed
if distribution.check_rebalance_needed():
    # Get rebalancing trades
    trades = distribution.get_rebalancing_trades()
    for from_dex, to_dex, pair, amount in trades:
        print(f"Transfer {amount} {pair} from {from_dex} to {to_dex}")

# Get current distribution stats
stats = distribution.get_distribution_stats()
print(f"DEX Exposure: {stats['dex_exposure']}")
print(f"Pair Exposure: {stats['pair_exposure']}")
print(f"DEX Scores: {stats['dex_scores']}")
```

## Scoring System

The distribution system uses a weighted scoring system to evaluate DEXes based on:

1. Gas Price (lower is better)
   - Normalized against highest gas price
   - Weighted by gas_price_weight

2. Liquidity (higher is better)
   - Normalized against highest liquidity
   - Weighted by liquidity_weight

3. Volume (higher is better)
   - Normalized against highest volume
   - Weighted by volume_weight

4. Success Rate (higher is better)
   - Calculated from successful vs failed trades
   - Weighted by success_rate_weight

## Exposure Management

The system manages exposure limits at two levels:

1. Per-DEX Exposure
   - Maximum amount allocated to each DEX
   - Tracked and enforced during allocation
   - Used for rebalancing decisions

2. Per-Pair Exposure
   - Maximum amount allocated to each trading pair
   - Prevents over-concentration in specific pairs
   - Applied across all DEXes

## Rebalancing

Automatic rebalancing is triggered when:

1. Exposure imbalance exceeds threshold
2. DEX scores significantly change
3. Risk limits are approached

Rebalancing process:
1. Calculate optimal distribution
2. Generate minimal set of transfer trades
3. Execute trades in optimal order
4. Update exposure tracking

## Storage Integration

The distribution system uses the storage system for:

1. Configuration persistence
   - Distribution settings
   - Exposure limits
   - Scoring weights

2. State management
   - Current exposures
   - DEX scores
   - Historical performance

3. Metrics tracking
   - Gas prices
   - Liquidity levels
   - Trading volumes
   - Success rates

## Best Practices

1. Regular Monitoring
   - Track exposure levels
   - Monitor DEX performance
   - Review rebalancing needs

2. Risk Management
   - Set conservative exposure limits
   - Maintain diversification
   - Monitor concentration risk

3. Performance Optimization
   - Adjust scoring weights based on results
   - Fine-tune rebalancing threshold
   - Review and update liquidity requirements

4. Error Handling
   - Handle failed trades gracefully
   - Maintain accurate exposure tracking
   - Regular state validation

5. Configuration
   - Start with conservative limits
   - Adjust weights based on market conditions
   - Regular review of thresholds
