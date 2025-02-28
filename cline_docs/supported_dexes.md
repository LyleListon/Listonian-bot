# Supported Decentralized Exchanges (DEXes)

The arbitrage system currently supports the following 5 decentralized exchanges:

## 1. Uniswap V2

- **Factory Address**: `0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f`
- **Router Address**: `0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D`
- **Init Code Hash**: `0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f`
- **Fee**: 0.3% (30 basis points)
- **Features**:
  - Constant product AMM (x*y=k)
  - Direct pair trading
  - Price discovery and quotes
  - Pool existence verification

## 2. Sushiswap

- **Factory Address**: `0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac`
- **Router Address**: `0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F`
- **Init Code Hash**: `0xe18a34eb0e04b04f7a0ac29a6e80748dca96319b42c54d679cb821dca90c6303`
- **Fee**: 0.3% (30 basis points)
- **Features**:
  - Uniswap V2 fork with additional features
  - SUSHI token rewards
  - Same AMM model as Uniswap V2
  - Enhanced routing capabilities

## 3. Uniswap V3

- **Factory Address**: `0x1F98431c8aD98523631AE4a59f267346ea31F984`
- **Quoter Address**: `0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6`
- **Router Address**: `0xE592427A0AEce92De3Edee1F18E0157C05861564`
- **Fee Tiers**: [100, 500, 3000, 10000] (0.01%, 0.05%, 0.3%, 1%)
- **Features**:
  - Concentrated liquidity
  - Multiple fee tiers
  - Price oracles
  - Non-fungible liquidity positions
  - Range orders

## 4. Pancakeswap

- **Factory Address**: `0x1097053Fd2ea711dad45caCcc45EfF7548fCB362`
- **Router Address**: `0x10ED43C718714eb63d5aA57B78B54704E256024E`
- **Init Code Hash**: `0x00fb7f630766e6a796048ea87d01acd3068e8ff67d078148a3fa3f4a84f69bd5`
- **Fee**: 0.25% (25 basis points)
- **Features**:
  - BSC native DEX (with Ethereum deployment)
  - Lower fees than Uniswap
  - Similar AMM model to Uniswap V2
  - Optimized for high-volume trading

## 5. Baseswap

- **Factory Address**: `0xf5d7d97b33c4090a8cace5f7c5a1cc54c5740930`
- **Router Address**: `0x327df1e6de05895d2ab08513aadd9313fe505700`
- **Init Code Hash**: `0xb618a2730fae167f5f8ac7bd659dd8436d571872655bcb6fd11f2158c8a64a3b`
- **Fee**: 0.3% (30 basis points)
- **Features**:
  - Base chain native DEX
  - Optimized for Base ecosystem
  - Supports ERC-20 tokens on Base
  - Similar interface to Uniswap V2

## Implementation Details

All five DEXes are fully integrated into the arbitrage system through the `DexManager` class in `arbitrage_bot/core/dex/dex_manager.py`.

The DEX integration includes:

1. **Configuration**
   - Factory and router addresses
   - Fee structures
   - Init code hashes (for V2-style DEXes)
   - Fee tiers (for V3-style DEXes)

2. **Price Quotation**
   - Getting token prices with `get_price()`
   - Handling token decimals and conversions

3. **Pool Verification**
   - Checking if pools exist with `check_pool_exists()`
   - Supporting different pool types (V2 pairs, V3 pools)

4. **Token Support**
   - Getting lists of supported tokens with `get_supported_tokens()`
   - Common token interfaces across DEXes

## Adding New DEXes

The system is designed to be extensible, allowing for easy addition of new DEXes:

1. Add DEX configuration to `configs/dex_config.json`
2. Create DEX-specific adapter if needed
3. Register the DEX in `DexManager._load_dexes()`

See the [Implementation Summary](implementation_summary.md) for more details on the DEX integration architecture.