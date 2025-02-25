# Flash Loan and Flashbots Integration Guide

## Overview

This guide explains how to use the integrated Flash Loan and Flashbots functionality in the arbitrage bot. This integration provides significant benefits:

- **MEV Protection**: Prevents front-running and sandwich attacks on your arbitrage operations
- **Profit Maximization**: Ensures arbitrage profits aren't stolen by MEV bots
- **Capital Efficiency**: Uses flash loans to execute arbitrage without large capital requirements
- **Gas Optimization**: Optimizes gas prices for maximum profitability

## Configuration

Enable both Flash Loans and Flashbots in your configuration file:

```json
{
  "use_flashbots": true,
  "flash_loans": {
    "enabled": true,
    "min_profit_basis_points": 100,  // 1% minimum profit
    "max_trade_size": "0.5"  // 0.5 ETH max trade size
  },
  "tokens": {
    "WETH": {
      "address": "0x4200000000000000000000000000000000000006",
      "decimals": 18
    },
    "USDC": {
      "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "decimals": 6
    }
  }
}
```

## Usage

### Direct Method

You can directly use the Flash Loan and Flashbots integration through the `FlashLoanManager`:

```python
# Create flash loan manager
flash_loan_manager = await create_flash_loan_manager(
    web3_manager=web3_manager,
    config=config
)

# Execute flash loan arbitrage via Flashbots
result = await flash_loan_manager.execute_flashbots_arbitrage(
    token_in=weth_address,
    token_out=weth_address,  # Same token for flash loan
    amount=Web3.to_wei(0.1, 'ether'),  # 0.1 ETH
    buy_dex="baseswap",
    sell_dex="pancakeswap",
    min_profit=Web3.to_wei(0.001, 'ether')  # 0.001 ETH min profit
)
```

### Through DexManager

The `DexManager` will automatically use Flash Loans and Flashbots if both are enabled in the configuration:

```python
# Execute arbitrage (will use flash loans and Flashbots if enabled)
result = await dex_manager.execute_arbitrage(
    token_address=weth_address,
    amount=Web3.to_wei(0.1, 'ether'),
    buy_dex="baseswap",
    sell_dex="pancakeswap",
    min_profit=Web3.to_wei(0.001, 'ether')
)
```

## Result Format

The result will contain the bundle status and details:

```json
{
  "status": "submitted",
  "bundle_id": "0x8888888888888888888888888888888888888888888888888888888888888888",
  "profit": 10000000000000000,  // 0.01 ETH profit
  "gas_settings": {
    "maxFeePerGas": 10000000000,  // 10 GWEI
    "maxPriorityFeePerGas": 2000000000,  // 2 GWEI
    "gasLimit": 500000
  }
}
```

Possible status values:
- `"submitted"`: Bundle was successfully submitted to Flashbots
- `"skipped"`: Bundle was not submitted (e.g., not profitable)
- `"error"`: An error occurred during execution

## Testing

Use the test script to verify the integration:

```bash
# Run the automated tests
.\run_flashbots_tests.bat
```

### Integration Testing

For full integration testing, you can also manually test with:

```python
python -m pytest tests/integration/test_flash_loan_flashbots.py -v
```

## Performance Monitoring

When running in production, you can monitor performance metrics:

1. Success rate: percentage of profitable bundle executions
2. Average profit: average profit per arbitrage
3. Gas efficiency: gas cost relative to profits

## Troubleshooting

### Common Issues

1. **Bundle Not Submitted**
   - Check profit threshold - may be too high
   - Verify token is supported for flash loans

2. **Bundle Not Included**
   - Gas price may be too low
   - Competition from other arbitrage bots

3. **Flash Loan Failure**
   - Verify contract deployment
   - Check token balance calculations

### Logs

Check logs for detailed diagnostics:

```
2025-02-25 13:00:00 INFO Executing flash loan arbitrage via Flashbots (flash_loan_manager.py:256)
2025-02-25 13:00:01 INFO Optimized gas settings for bundle: {'maxFeePerGas': 10000000000, 'maxPriorityFeePerGas': 2000000000} (flashbots_manager.py:221)
2025-02-25 13:00:03 INFO Submitted bundle 0x8888 for block 12345678 (flashbots_manager.py:144)
```

## Future Enhancements

Upcoming improvements to the integration:
- Multi-token support
- Advanced profit calculation
- Bundle simulation testing
- Cross-chain arbitrage