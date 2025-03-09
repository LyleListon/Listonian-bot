# DEX Layer

## Overview
The DEX layer provides a unified interface for interacting with different decentralized exchanges (DEXs) on the Base network. It implements protocol-specific adapters while maintaining a consistent API across all supported DEXs.

## Structure
```
dex/
├── interfaces/          # Core interfaces and types
│   ├── types.py        # Data structures
│   └── base.py         # Base DEX interface
├── protocols/          # Protocol implementations
│   ├── baseswap/       # BaseSwap implementation
│   ├── swapbased/      # SwapBased implementation
│   └── pancakeswap/    # PancakeSwap implementation
└── utils/             # Shared utilities
    ├── calculations.py # Price and amount calculations
    ├── contracts.py    # Contract interaction helpers
    └── validation.py   # Input validation functions
```

## Components

### Interfaces
The `interfaces` package defines the core contracts that all DEX implementations must follow:

```python
from src.core.dex.interfaces import BaseDEX, Token, TokenAmount

class MyDEX(BaseDEX):
    async def get_price(
        self,
        base_token: Token,
        quote_token: Token
    ) -> Decimal:
        # Implementation
```

### Protocols
Protocol-specific implementations in the `protocols` directory:
- BaseSwap (Uniswap V2 fork)
- SwapBased (Uniswap V2 fork)
- PancakeSwap (Uniswap V3 fork)

### Utilities
Shared functionality in the `utils` package:
```python
from src.core.dex.utils import (
    calculate_price_impact,
    get_amount_out,
    validate_pool_health
)
```

## Usage Examples

### Initialize DEX
```python
from src.core.blockchain import Web3Manager
from src.core.dex.protocols.baseswap import BaseSwap

# Initialize
web3 = Web3Manager(url="RPC_URL", chain_id=8453)
dex = BaseSwap(
    web3_manager=web3,
    factory_address="0x...",
    router_address="0x..."
)

# Connect
await web3.connect()
```

### Get Price Quote
```python
# Get tokens
weth = await dex.get_token("0x...")
usdc = await dex.get_token("0x...")

# Create amount
amount = TokenAmount(
    token=weth,
    amount=Decimal("1.0")
)

# Get quote
quote = await dex.get_quote(
    input_amount=amount,
    output_token=usdc
)

print(f"1 WETH = {quote.output_amount} USDC")
print(f"Price Impact: {quote.price_impact}%")
```

### Execute Swap
```python
# Create swap parameters
params = SwapParams(
    quote=quote,
    slippage=Decimal("0.5"),  # 0.5%
    deadline=int(time.time() + 60),  # 1 minute
    recipient="0x..."
)

# Validate
is_valid, error = validate_swap_params(params)
if not is_valid:
    raise ValueError(f"Invalid swap: {error}")

# Execute
tx_hash = await dex.execute_swap(params)
print(f"Swap executed: {tx_hash}")
```

### Monitor Prices
```python
async def price_update(old_price: Decimal, new_price: Decimal):
    print(f"Price changed: {old_price} -> {new_price}")

# Start monitoring
pool = await dex.get_pool(weth, usdc)
await dex.monitor_price(
    pool_address=pool.address,
    callback=price_update
)
```

## Best Practices

1. **Validation**
   - Always validate inputs
   - Check pool health
   - Verify price impact
   - Monitor reserve changes

2. **Error Handling**
   - Handle RPC errors
   - Implement retries
   - Log all operations
   - Validate responses

3. **Gas Optimization**
   - Use multicall when possible
   - Batch similar operations
   - Monitor gas prices
   - Implement fallbacks

4. **Price Monitoring**
   - Use WebSocket for updates
   - Implement heartbeats
   - Handle disconnections
   - Validate price changes

## Configuration

### Environment Variables
```env
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR-API-KEY
CHAIN_ID=8453
```

### Contract Addresses
```json
{
  "baseswap": {
    "factory": "0x...",
    "router": "0x..."
  },
  "swapbased": {
    "factory": "0x...",
    "router": "0x..."
  }
}
```

## Development

### Adding New Protocol
1. Create protocol directory
2. Implement BaseDEX interface
3. Add contract ABIs
4. Write unit tests
5. Update documentation

### Testing
```bash
# Run tests
pytest tests/core/dex

# Test specific protocol
pytest tests/core/dex/protocols/baseswap
```

Last Updated: 2025-02-10