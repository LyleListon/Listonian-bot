# Testing Triangular Arbitrage

This guide explains how to test the multi-path arbitrage functionality using Base network DEXs.

## Setup

1. Deploy the MultiPathArbitrage contract:
```bash
npx hardhat run scripts/deploy-multi-path.js --network base
```

2. Fund your wallet with:
   - At least 0.1 WETH for the trade
   - Additional ETH for gas fees (approximately 0.01 ETH)

## Test Trade Path

The test executes a triangular arbitrage across three DEXs:

1. BaseSwap (V2): WETH → USDC
2. Aerodrome (V2): USDC → USDT
3. SwapBased (V3): USDT → WETH

## Token Addresses
- WETH: 0x4200000000000000000000000000000000000006
- USDC: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
- USDT: 0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb

## Running the Test

1. Make sure you have the required tokens:
```bash
# Get WETH by wrapping ETH
cast send 0x4200000000000000000000000000000000000006 "deposit()" --value 0.11ether
```

2. Run the test script:
```bash
npx hardhat run scripts/test-triangular-trade.js --network base
```

## Expected Output

The script will:
1. Deploy the contract if not already deployed
2. Execute the triangular arbitrage
3. Log transaction details and gas costs
4. Report any profits generated

Example output:
```
Found existing deployment: 0x...
Using gas price: 1.2 gwei
Executing triangular arbitrage...
Trade path: WETH → USDC → USDT → WETH
Initial amount: 0.1 WETH
Transaction sent: 0x...
Waiting for confirmation...
Trade successful!
Profit: 0.001234 WETH
Gas used: 350000
Gas cost: 0.00042 ETH
```

## Troubleshooting

1. If transaction fails with "insufficient funds":
   - Ensure wallet has enough WETH and ETH for gas
   - Check token allowances for each DEX

2. If transaction fails with "execution reverted":
   - Check token balances and liquidity
   - Verify router addresses and token paths
   - Consider increasing gas limit

3. If no profit generated:
   - Market conditions may not be favorable
   - Try adjusting trade amount
   - Check price impact across DEXs

## Safety Notes

1. Always start with small test amounts
2. Monitor gas prices before execution
3. Verify all token addresses and DEX routers
4. Keep emergency ETH buffer for gas
5. Check DEX liquidity before trading