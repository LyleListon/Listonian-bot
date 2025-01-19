# Deployment Notes - Sepolia Testing

## Latest Contract Addresses

- PathFinder: 0xcE3cc012AacB30b5c576b822278c045f37723867
- QuoteManager: 0xfeD76Cd4BB823d0E59079C9d2a7f692D2276f408
- DEXRegistry: 0xc6BbdD9063A9d247F21BE0C71aAbd95b1C312e8B
- PathValidator: 0xA02aFB86Ce774733B543329C2d35Fb663f1755fF

## Uniswap V3 Sepolia Addresses

- Factory: 0x0227628f3F023bb0B980b67D528571c95c6DaC1c
- Quoter: 0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6
- Router: 0xE592427A0AEce92De3Edee1F18E0157C05861564

## Token Addresses

- WETH: 0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14
- USDC: 0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238

## Recent Changes (Latest First)

### 2024-02-14: Fixed NoPathFound Errors

1. Deployed new QuoteManager with:
   - Correct QuoterV2 address
   - Lower liquidity thresholds (0.01 ETH) for WETH and USDC
   - Improved error handling

2. Deployed new PathFinder with optimized parameters:
   - maxGasPerPath: 300,000
   - minLiquidityRequired: 0.01 ETH (matches QuoteManager)
   - maxPriceImpact: 5%

3. Updated config.yaml with:
   - Correct Uniswap V3 addresses
   - New QuoteManager and PathFinder addresses

### Pool Status

WETH-USDC pool (0x6Ce0896eAE6D4BD668fDe41BB784548fb8F59b50):
- Exists and has liquidity
- Current liquidity: 129484435476864
- Current tick: 183532
- Pool is unlocked and active

## Next Steps

1. Monitor arbitrage detection with new parameters
2. If needed, adjust:
   - Liquidity thresholds
   - Price impact tolerance
   - Gas limits

## Notes

- Only testing with WETH-USDC pair initially
- Lowered liquidity requirements for testing
- Using 5% max price impact for better opportunity detection
- All contracts verified on Sepolia explorer
