# PancakeSwap V3 Protocol

## Overview
PancakeSwap V3 implementation for the Base network. This is a Uniswap V3 fork with concentrated liquidity and multiple fee tiers.

## Features
- Concentrated liquidity positions
- Multiple fee tiers (0.01%, 0.05%, 0.3%, 1%)
- Price oracle integration
- Tick-based price calculations
- Advanced swap routing

## Contract Addresses
```python
ADDRESSES = {
    'factory': '0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865',
    'router': '0x1b81D678ffb9C0263b24A97847620C99d213eB14',
    'quoter': '0xB048Bbc1Ee6b733FFfCFb9e9CeF7375518e25997',
    'position_manager': '0x46A15B0b27311cedF172AB29E4f4766fbE7F4364',
    'weth': '0x4200000000000000000000000000000000000006',
}
```

## Common Tokens
```python
TOKENS = {
    'WETH': '0x4200000000000000000000000000000000000006',
    'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    'DAI': '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb',
    'USDbC': '0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA',
}
```

## Usage

### Initialize
```python
from src.core.blockchain import Web3Manager
from src.core.dex.protocols.pancakeswap import create_pancakeswap

# Initialize with default addresses
web3 = Web3Manager(url="RPC_URL", chain_id=8453)
dex = create_pancakeswap(web3)

# Or with custom addresses
dex = PancakeSwapV3(
    web3_manager=web3,
    factory_address="0x...",
    router_address="0x...",
    quoter_address="0x..."
)
```

### Get Pool Information
```python
# Get specific pool
pool = await dex.get_pool(weth, usdc)
print(f"WETH/USDC Pool: {pool}")

# Get current price
price = await dex.get_price(weth, usdc)
print(f"Current Price: {price}")
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

### Concentrated Liquidity
- Liquidity is concentrated in specific price ranges
- More efficient capital usage
- Complex math utilities for calculations
- Tick-based price management

### Fee Tiers
```python
class FeeTier(Enum):
    LOWEST = 100   # 0.01%
    LOW = 500      # 0.05%
    MEDIUM = 3000  # 0.3%
    HIGH = 10000   # 1%
```

### Price Calculation
- Uses Q96.96 fixed-point arithmetic
- Square root price representation
- Tick-based calculations
- Oracle price integration

### Pool Management
- Automatic pool discovery
- State caching
- Health validation
- Event monitoring

### Error Handling
- Comprehensive error messages
- Automatic retries
- Validation at multiple levels
- Safe transaction building

## Best Practices

1. Fee Tier Selection
```python
# Use appropriate fee tier based on pair volatility
# Lower fee for stable pairs
pool = await dex.get_pool(usdc, usdt, FeeTier.LOWEST)  # 0.01%

# Higher fee for volatile pairs
pool = await dex.get_pool(weth, usdc, FeeTier.MEDIUM)  # 0.3%
```

2. Price Impact Monitoring
```python
# Check price impact before swap
if quote.price_impact > Decimal("1.0"):  # > 1%
    logger.warning("High price impact")
```

3. Slippage Protection
```python
# Higher slippage for volatile pairs
params = SwapParams(quote=quote, slippage=Decimal("1.0"))

# Lower slippage for stable pairs
params = SwapParams(quote=quote, slippage=Decimal("0.1"))
```

4. Gas Optimization
```python
# Monitor gas prices
gas_price = await web3.get_gas_price()
if gas_price > Wei("100 gwei"):
    logger.warning("High gas price")
```

## Differences from V2
1. Liquidity Management
   - V2: Uniform liquidity distribution
   - V3: Concentrated in price ranges

2. Fee Structure
   - V2: Fixed 0.3% fee
   - V3: Multiple fee tiers

3. Price Calculation
   - V2: Simple x * y = k formula
   - V3: Complex tick-based math

4. Capital Efficiency
   - V2: Lower efficiency
   - V3: Higher through concentration

## References
- [PancakeSwap V3 Docs](https://docs.pancakeswap.finance/code/v3)
- [Uniswap V3 Whitepaper](https://uniswap.org/whitepaper-v3.pdf)
- [Base Network Docs](https://docs.base.org)

Last Updated: 2025-02-10