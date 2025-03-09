# Production Setup Guide

This guide walks you through setting up the arbitrage system for production deployment.

## Prerequisites

- Python 3.12+
- Ethereum node access (Alchemy, Infura, or your own node)
- Private key with ETH for gas and initial trades
- Basic understanding of Ethereum and DeFi

## Step 1: Configure Provider URL and Private Key

The most critical configuration is providing the correct Ethereum node access and private key. Open `configs/production.json` and update the following fields:

```json
{
  "provider_url": "https://eth-mainnet.alchemyapi.io/v2/YOUR_API_KEY",
  "chain_id": 1,
  "private_key": "YOUR_PRIVATE_KEY_HERE",
  "network": {
    "rpc_url": "https://eth-mainnet.alchemyapi.io/v2/YOUR_API_KEY"
  }
}
```

- Replace `YOUR_API_KEY` with your actual Alchemy or Infura API key
- Replace `YOUR_PRIVATE_KEY_HERE` with your wallet's private key (without the 0x prefix)
- Ensure `chain_id` is correct for your target network (1 for Ethereum Mainnet)

## Step 2: Configure Flash Loan Settings

```json
"flash_loans": {
  "enabled": true,
  "use_flashbots": true,
  "min_profit_basis_points": 200,
  "max_trade_size": "1",
  "slippage_tolerance": 50,
  "transaction_timeout": 180,
  "balancer_vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
  "contract_address": {
    "mainnet": "YOUR_DEPLOYED_CONTRACT_ADDRESS"
  }
}
```

- If you have deployed a custom flash loan contract, update `YOUR_DEPLOYED_CONTRACT_ADDRESS`
- Adjust `min_profit_basis_points` (200 = 2% minimum profit) based on your risk tolerance
- Adjust `slippage_tolerance` (50 = 0.5% slippage tolerance) based on market volatility

## Step 3: Configure Dynamic Allocation

```json
"dynamic_allocation": {
  "enabled": true,
  "min_percentage": 5,
  "max_percentage": 50,
  "absolute_min_eth": 0.05,
  "absolute_max_eth": 10.0,
  "concurrent_trades": 2,
  "reserve_percentage": 10
}
```

- `min_percentage`: Minimum percentage of available balance to use (5%)
- `max_percentage`: Maximum percentage of available balance to use (50%)
- `absolute_min_eth`: Minimum trade size regardless of balance (0.05 ETH)
- `absolute_max_eth`: Maximum trade size regardless of balance (10 ETH)
- `concurrent_trades`: Number of simultaneous trades (2 recommended)
- `reserve_percentage`: Percentage of balance to keep in reserve for gas (10%)

## Step 4: Configure MEV Protection

```json
"mev_protection": {
  "enabled": true,
  "use_flashbots": true,
  "max_bundle_size": 5,
  "max_blocks_ahead": 3,
  "min_priority_fee": "1.5",
  "max_priority_fee": "3",
  "sandwich_detection": true,
  "frontrun_detection": true,
  "adaptive_gas": true
}
```

- If using Flashbots, ensure `use_flashbots` is set to `true`
- Adjust priority fees based on current network conditions

## Step 5: Configure Monitoring and Dashboard

```json
"monitoring": {
  "log_level": "INFO",
  "metrics_enabled": true,
  "alert_threshold": 85.0,
  "collection_interval": 10000,
  "log_rotation": {
    "max_size": "500MB",
    "backup_count": 10
  }
},
"dashboard": {
  "auth_enabled": true,
  "cors": {
    "enabled": true,
    "origins": [
      "https://dashboard.example.com",
      "http://localhost:8080"
    ]
  }
}
```

- Set `log_level` to "DEBUG" for more detailed logs during initial setup
- Update dashboard CORS origins if accessing the dashboard from specific domains

## Step 6: Running the System

Once configuration is complete, you can start the system:

```bash
# Using PowerShell
pwsh -ExecutionPolicy Bypass -File .\deploy_production.ps1

# Using Command Prompt
.\start_production.bat
```

To start the monitoring dashboard:

```bash
# Using Command Prompt
.\start_dashboard.bat

# Using Python directly
python start_dashboard.py
```

## Testing Your Configuration

Before running with real funds, you can test your configuration:

1. Set `absolute_max_eth` to a small value (e.g., 0.1 ETH)
2. Run the system and monitor the logs for any errors
3. Check the dashboard to ensure proper connectivity and data flow
4. Look for successful arbitrage opportunity scanning

## Security Considerations

- **Never** share your private key or commit it to version control
- Consider using environment variables for sensitive information:
  ```
  "private_key": "${ETHEREUM_PRIVATE_KEY}"
  ```
- Run the system on a secure server with appropriate firewall settings
- Regularly monitor logs and dashboard for unusual activities

## Troubleshooting

- **Provider URL errors**: Verify your Alchemy/Infura API key is valid and has the correct permissions
- **Transaction failures**: Check gas settings and slippage tolerance
- **Low profitability**: Adjust `min_profit_basis_points` and review gas optimization settings
- **Dashboard connectivity issues**: Verify CORS settings and network connectivity

For more detailed configuration options, see the [Arbitrage Configuration Guide](arbitrage_configuration_guide.md).