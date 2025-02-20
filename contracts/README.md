# Multi-Path Arbitrage System

## Overview
This system enables complex arbitrage trades across multiple DEXs and tokens, supporting both direct and triangular arbitrage opportunities.

## Contracts

### MultiPathArbitrage.sol
Advanced flash loan arbitrage contract that supports:
- Multi-token trading paths (e.g., ETH → USDC → TOKEN → ETH)
- Multiple DEX interactions in a single transaction
- Both V2 and V3 DEX protocols
- Atomic execution through flash loans

## Deployment

1. Deploy the contract:
```bash
npx hardhat run scripts/deploy-multi-path.js --network base
```

2. The deployment script will:
   - Deploy the contract
   - Set up the profit recipient
   - Verify the contract on Etherscan
   - Save deployment details to `multi-path-deployment-details.json`

## Usage

### Example: Triangular Arbitrage

```javascript
// Example trade path: ETH → USDC → TOKEN → ETH
const tradeSteps = [
    {
        router: "0x...", // DEX1 router address
        path: [WETH_ADDRESS, USDC_ADDRESS],
        isV3: true,
        amount: ethers.utils.parseEther("1"),
        fee: 500 // 0.05% fee tier
    },
    {
        router: "0x...", // DEX2 router address
        path: [USDC_ADDRESS, TOKEN_ADDRESS],
        isV3: false,
        amount: 0, // Will be set to output from previous step
        fee: 0 // Not used for V2
    },
    {
        router: "0x...", // DEX3 router address
        path: [TOKEN_ADDRESS, WETH_ADDRESS],
        isV3: true,
        amount: 0, // Will be set to output from previous step
        fee: 3000 // 0.3% fee tier
    }
];

// Execute flash loan with trade steps
await contract.executeFlashLoan(
    WETH_ADDRESS,
    ethers.utils.parseEther("1"),
    tradeSteps
);
```

### Example: Direct Arbitrage

```javascript
// Example: Buy on DEX1, sell on DEX2
const tradeSteps = [
    {
        router: "0x...", // DEX1 router address
        path: [WETH_ADDRESS, USDC_ADDRESS],
        isV3: true,
        amount: ethers.utils.parseEther("1"),
        fee: 500
    },
    {
        router: "0x...", // DEX2 router address
        path: [USDC_ADDRESS, WETH_ADDRESS],
        isV3: true,
        amount: 0, // Will be set to output from previous step
        fee: 500
    }
];

await contract.executeFlashLoan(
    WETH_ADDRESS,
    ethers.utils.parseEther("1"),
    tradeSteps
);
```

## Safety Features

1. **Atomic Execution**: All trades in a path must succeed, or the entire transaction reverts
2. **Flash Loan Security**: Loan must be repaid in the same transaction
3. **Profit Protection**: Transaction reverts if final balance is insufficient
4. **Emergency Functions**: Owner can withdraw stuck tokens/ETH if needed

## Gas Optimization

The contract is optimized for gas usage:
- Minimizes storage operations
- Uses efficient data structures
- Batches approvals when possible
- Reuses token allowances

## Monitoring

Monitor trades and profits through events:
- `FlashLoanExecuted`: Emitted after successful flash loan execution
- `ProfitTransferred`: Emitted when profits are sent to recipient
- `TradeExecuted`: Emitted for each successful trade step

## Testing

Run the test suite:
```bash
npx hardhat test
```

## Security Notes

1. Always verify token allowances before trading
2. Test with small amounts first
3. Monitor gas prices to ensure profitability
4. Keep emergency ETH buffer for gas costs
5. Regularly check for contract upgrades
