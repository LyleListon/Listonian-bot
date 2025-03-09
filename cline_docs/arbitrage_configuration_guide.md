# Arbitrage System Configuration Guide

This document provides a comprehensive guide to the configuration parameters for the arbitrage system, including detailed explanations of each parameter, their units of measurement, and recommended settings.

## Table of Contents

1. [Dynamic Allocation Parameters](#dynamic-allocation-parameters)
2. [Flash Loan Parameters](#flash-loan-parameters)
3. [MEV Protection Parameters](#mev-protection-parameters)
4. [General Configuration](#general-configuration)
5. [Safety Relationships](#safety-relationships)
6. [Configuration Scenarios](#configuration-scenarios)

## Dynamic Allocation Parameters

The `dynamic_allocation` section controls how the system allocates your funds for trading.

| Parameter | Unit | Description | Recommended |
|-----------|------|-------------|-------------|
| `enabled` | boolean | Enables/disables dynamic allocation | `true` |
| `min_percentage` | percentage (%) | Minimum percentage of available balance to use for a trade | 5% |
| `max_percentage` | percentage (%) | Maximum percentage of available balance to use for a trade | 50% |
| `absolute_min_eth` | ETH | Absolute minimum trade size regardless of balance | 0.05 ETH |
| `absolute_max_eth` | ETH | Absolute maximum trade size regardless of balance | 10.0 ETH |
| `concurrent_trades` | count | Maximum number of trades to execute simultaneously | 2 |
| `reserve_percentage` | percentage (%) | Percentage of balance to keep in reserve | 10% |

### Example Calculation

With a wallet containing 10 ETH and default settings:
- Reserve: 1 ETH (10% of 10 ETH)
- Available for trading: 9 ETH
- Min trade size: 0.45 ETH (5% of available 9 ETH)
- Max trade size: 2.25 ETH (50% ÷ 2 concurrent trades)

## Flash Loan Parameters

The `flash_loans` section controls flash loan borrowing and arbitrage execution.

| Parameter | Unit | Description | Recommended |
|-----------|------|-------------|-------------|
| `enabled` | boolean | Enables/disables flash loans | `true` |
| `use_flashbots` | boolean | Use Flashbots for MEV protection | `true` |
| `min_profit_basis_points` | basis points (1/100%) | Minimum profit threshold (200 = 2%) | 200-300 |
| `max_trade_size` | ETH | Maximum flash loan size | "1" |
| `slippage_tolerance` | basis points (1/100%) | Maximum acceptable slippage (50 = 0.5%) | 50-100 |
| `transaction_timeout` | seconds | Maximum time to wait for transaction confirmation | 180 |
| `balancer_vault` | address | Address of Balancer Vault for flash loans | contract-specific |

### Understanding Basis Points

Basis points (bps) are used to express small percentage changes:
- 1 basis point = 0.01% (one hundredth of a percent)
- 50 basis points = 0.5%
- 100 basis points = 1%
- 200 basis points = 2%

### Key Safeguards

- `min_profit_basis_points` should always be significantly higher than `slippage_tolerance` (usually 4x higher)
- Example: With 200 bps min profit and 50 bps slippage, worst-case profit is still 150 bps (1.5%)

## MEV Protection Parameters

The `mev_protection` section configures protection against frontrunning and other MEV attacks.

| Parameter | Unit | Description | Recommended |
|-----------|------|-------------|-------------|
| `enabled` | boolean | Enables/disables MEV protection | `true` |
| `use_flashbots` | boolean | Use Flashbots for private transactions | `true` |
| `max_bundle_size` | count | Maximum transactions in a bundle | 5 |
| `max_blocks_ahead` | blocks | Maximum blocks to target ahead | 3 |
| `min_priority_fee` | gwei | Minimum priority fee for transactions | "1.5" |
| `max_priority_fee` | gwei | Maximum priority fee for transactions | "3" |
| `sandwich_detection` | boolean | Enable sandwich attack detection | `true` |
| `frontrun_detection` | boolean | Enable frontrunning detection | `true` |
| `adaptive_gas` | boolean | Enable adaptive gas pricing | `true` |

## General Configuration

These parameters control general system behavior.

| Parameter | Unit | Description | Recommended |
|-----------|------|-------------|-------------|
| `provider_url` | URL | Ethereum node URL | Network-specific |
| `chain_id` | number | Blockchain network ID | Network-specific |
| `private_key` | string | Private key for transaction signing | Secure key |
| `log_level` | string | Logging verbosity level | "INFO" |
| `max_paths_to_check` | count | Maximum arbitrage paths to check | 100 |
| `min_profit_threshold` | ETH | Minimum profit in ETH | 0.001 |
| `gas_limit_buffer` | percentage (%) | Extra gas limit buffer | 20 |

## Safety Relationships

The system maintains several important relationships between parameters to ensure safety:

1. **Profit vs. Slippage**
   - `min_profit_basis_points` > `slippage_tolerance`
   - This ensures that even with maximum slippage, trades remain profitable

2. **Position Sizing**
   - `absolute_min_eth` serves as a floor regardless of percentage calculations
   - `absolute_max_eth` serves as a ceiling regardless of percentage calculations
   - These prevent extremely small or large trades

3. **Risk Management**
   - `concurrent_trades` limits exposure
   - `reserve_percentage` ensures funds for gas and emergencies

4. **MEV Protection**
   - `use_flashbots` + `frontrun_detection` provides multi-layered protection
   - `adaptive_gas` adjusts to market conditions

## Configuration Scenarios

### Conservative Setting

```json
{
  "dynamic_allocation": {
    "min_percentage": 3,
    "max_percentage": 30,
    "absolute_min_eth": 0.05,
    "absolute_max_eth": 5.0,
    "concurrent_trades": 1,
    "reserve_percentage": 15
  },
  "flash_loans": {
    "min_profit_basis_points": 300,
    "slippage_tolerance": 30
  }
}
```

### Balanced Setting (Default)

```json
{
  "dynamic_allocation": {
    "min_percentage": 5,
    "max_percentage": 50,
    "absolute_min_eth": 0.05,
    "absolute_max_eth": 10.0,
    "concurrent_trades": 2,
    "reserve_percentage": 10
  },
  "flash_loans": {
    "min_profit_basis_points": 200,
    "slippage_tolerance": 50
  }
}
```

### Aggressive Setting

```json
{
  "dynamic_allocation": {
    "min_percentage": 10,
    "max_percentage": 70,
    "absolute_min_eth": 0.1,
    "absolute_max_eth": 20.0,
    "concurrent_trades": 3,
    "reserve_percentage": 5
  },
  "flash_loans": {
    "min_profit_basis_points": 150,
    "slippage_tolerance": 75
  }
}
```

## Validation and Safety Mechanisms

The system implements multiple layers of validation to ensure safe operation:

1. **Pre-Execution Validation**
   - Confirms expected profit exceeds minimum threshold
   - Accounts for flash loan fees, gas costs, and slippage

2. **Smart Contract Safety**
   - Sets minimum output parameters to enforce slippage limits
   - Reverts transactions if minimum outputs aren't met

3. **Transaction Simulation**
   - Simulates transactions before execution
   - Confirms profitability with current market conditions

4. **Balance Verification**
   - Verifies sufficient balance before transaction submission
   - Maintains reserves according to configuration

These mechanisms work together to prevent unprofitable trades and protect your funds.