# DEX Integration Module

The DEX (Decentralized Exchange) integration module provides a unified interface for interacting with various decentralized exchanges. It abstracts away the complexities of different DEX protocols and presents a consistent API for the arbitrage bot.

## Supported DEXes

The module currently supports the following DEXes:

- **Uniswap V2/V3**: Ethereum and L2 deployments
- **PancakeSwap**: BSC and other chains
- **SushiSwap**: Multi-chain deployments
- **BaseSwap**: Base chain native DEX
- **RocketSwap**: Optimized for low slippage
- **SwapBased**: Base chain DEX
- **Aerodrome**: Optimized for stable pairs

## Architecture

The DEX integration follows a hierarchical inheritance pattern:

- **BaseDEX**: Abstract base class defining the common interface
- **BaseDEXV2/V3**: Protocol-specific base classes (e.g., for Uniswap V2/V3 style DEXes)
- **Specific DEX Implementations**: Concrete implementations for each supported DEX

## Key Components

### DEX Manager

The `DexManager` class serves as the central coordinator for all DEX interactions:

```python
from arbitrage_bot.dex.dex_manager import DexManager

# Create a DEX manager
dex_manager = await DexManager.create(web3_manager, config)

# Get a specific DEX instance
uniswap = await dex_manager.get_dex("uniswap_v3")

# Get all active DEXes
active_dexes = await dex_manager.get_active_dexes()
```

### DEX Interface

Each DEX implementation provides the following core functionality:

- **Price Queries**: Get current prices and quotes
- **Liquidity Analysis**: Analyze pool liquidity and depth
- **Swap Execution**: Execute token swaps
- **Pool Data**: Get detailed pool information
- **Gas Estimation**: Estimate gas costs for operations

## Usage Examples

### Getting Price Quotes

```python
# Get a price quote
quote = await dex.get_quote(
    token_in="0x...",  # Input token address
    token_out="0x...",  # Output token address
    amount_in=Web3.to_wei(1, "ether")
)

print(f"Expected output: {Web3.from_wei(quote.amount_out, 'ether')} tokens")
print(f"Price impact: {quote.price_impact}%")
```

### Analyzing Liquidity

```python
# Get pool liquidity
liquidity = await dex.get_pool_liquidity(
    token_a="0x...",
    token_b="0x..."
)

print(f"Pool liquidity: ${liquidity.total_liquidity_usd}")
print(f"Token A reserves: {liquidity.reserve_a}")
print(f"Token B reserves: {liquidity.reserve_b}")
```

### Creating Swap Transactions

```python
# Create a swap transaction
tx = await dex.create_swap_transaction(
    token_in="0x...",
    token_out="0x...",
    amount_in=Web3.to_wei(1, "ether"),
    min_amount_out=Web3.to_wei(0.95, "ether")  # 5% slippage tolerance
)

# The transaction can then be sent or included in a bundle
```

## Adding New DEXes

To add support for a new DEX:

1. Identify which base class to extend (BaseDEXV2, BaseDEXV3, etc.)
2. Implement the required methods for the specific DEX
3. Register the DEX in the `dex_registry.py` file
4. Add any necessary ABIs to the `abi/` directory

Example of a new DEX implementation:

```python
from arbitrage_bot.dex.base.base_dex_v3 import BaseDEXV3

class NewDEX(BaseDEXV3):
    """Implementation for NewDEX."""
    
    def __init__(self, web3, config):
        super().__init__(web3, config)
        self.name = "new_dex"
        self.factory_address = "0x..."
        self.router_address = "0x..."
        
    async def initialize(self):
        """Initialize the DEX with necessary contracts."""
        await super().initialize()
        # DEX-specific initialization
        
    async def get_pool_address(self, token_a, token_b, fee=3000):
        """Get the pool address for the given token pair."""
        # DEX-specific implementation
```

## Configuration

DEX-specific configuration is stored in `configs/dex_config.json`:

```json
{
  "uniswap_v3": {
    "enabled": true,
    "factory_address": "0x...",
    "router_address": "0x...",
    "quoter_address": "0x...",
    "fee_tiers": [100, 500, 3000, 10000]
  },
  "pancakeswap": {
    "enabled": true,
    "factory_address": "0x...",
    "router_address": "0x..."
  }
}
```

## Testing

Each DEX implementation has dedicated tests:

```bash
python -m pytest arbitrage_bot/tests/dex/