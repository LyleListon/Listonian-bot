# BaseSwap Protocol

## Overview
BaseSwap implementation for the Base network. This is a Uniswap V2 fork with standard AMM functionality.

## Features
- Standard AMM pools (x * y = k)
- 0.3% swap fee
- Direct token swaps
- Multi-hop routing
- Price monitoring

## Contract Addresses
```python
ADDRESSES = {
    'factory': '0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB',
    'router': '0x327Df1E6de05895d2ab08513aaDD9313Fe505d86',
    'weth': '0x4200000000000000000000000000000000000006',
}
```

## Common Tokens
```python
TOKENS = {
    'WETH': '0x4200000000000000000000000000000000000006',
    'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    'DAI': '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb',
}
```

## Usage

### Initialize
```python
from src.core.blockchain import Web3Manager
from src.core.dex.protocols.baseswap import create_baseswap

# Initialize with default addresses
web3 = Web3Manager(url="RPC_URL", chain_id=8453)
dex = create_baseswap(web3)

# Or with custom addresses
dex = BaseSwap(
    web3_manager=web3,
    factory_address="0x...",
    router_address="0x..."
)
```

### Get Pool Information
```python
# Get specific pool
pool = await dex.get_pool(weth, usdc)
print(f"WETH/USDC Pool: {pool}")

# Get reserves
reserves = await dex.get_reserves(pool.address)
print(f"Reserves: {reserves}")
```

### Get Price Quote
```python
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
    deadline=int(time.time() + 60),
    recipient="0x..."
)

# Execute
tx_hash = await dex.execute_swap(params)
print(f"Swap executed: {tx_hash}")
```

### Monitor Prices
```python
async def on_price_update(old_price: Decimal, new_price: Decimal):
    print(f"Price changed: {old_price} -> {new_price}")

# Start monitoring
await dex.monitor_price(pool.address, on_price_update)
```

## Implementation Details

### Pool Discovery
- Pools are discovered through factory events
- Pool addresses are cached for efficiency
- Health checks validate liquidity and activity

### Price Calculation
- Uses constant product formula (x * y = k)
- Accounts for decimals and normalization
- Includes price impact calculation
- Considers fees in quotes

### Path Finding
- Currently uses direct paths only
- Multi-hop routing planned for future
- Path validation checks liquidity

### Error Handling
- Comprehensive error messages
- Automatic retries for RPC calls
- Validation at multiple levels
- Safe transaction building

## Best Practices

1. Always validate pools before use:
```python
is_valid, error = validate_pool_health(pool)
if not is_valid:
    raise ValueError(f"Unhealthy pool: {error}")
```

2. Check price impact:
```python
if quote.price_impact.is_high:
    logger.warning(f"High price impact: {quote.price_impact}%")
```

3. Use appropriate slippage:
```python
# Higher for volatile pairs
params = SwapParams(quote=quote, slippage=Decimal("1.0"))

# Lower for stable pairs
params = SwapParams(quote=quote, slippage=Decimal("0.1"))
```

4. Monitor gas prices:
```python
gas_price = await web3.get_gas_price()
if gas_price > Wei("100 gwei"):
    logger.warning("High gas price")
```

Last Updated: 2025-02-10