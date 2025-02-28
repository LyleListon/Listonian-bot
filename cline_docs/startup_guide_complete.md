# Complete Arbitrage Bot Startup Guide

This comprehensive guide will walk you through the process of setting up and running the enhanced arbitrage bot system with all the new components. Follow each section sequentially to ensure proper configuration and startup.

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Configuration](#2-configuration)
3. [Starting the System](#3-starting-the-system)
4. [Component-Specific Instructions](#4-component-specific-instructions)
5. [Troubleshooting](#5-troubleshooting)
6. [Monitoring and Maintenance](#6-monitoring-and-maintenance)

## 1. Environment Setup

### 1.1 Python Environment

Ensure you have Python 3.10+ installed:

```bash
python --version
```

Create and activate a virtual environment (optional but recommended):

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

### 1.2 Install Dependencies

Install all required packages:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools
```

You may need to run the environment setup scripts to fix potential issues:

```bash
# Fix Python installation issues
python check_python.py

# For VSCode terminal issues
.\fix_vscode_terminal.bat
```

### 1.3 Network Requirements

The arbitrage bot requires access to:
- Ethereum node (mainnet or testnet)
- Flashbots relay
- DEX contracts

Ensure your firewall allows outgoing connections to these services.

## 2. Configuration

### 2.1 Core Configuration

Create or modify `configs/config.json`:

```json
{
  "provider_url": "YOUR_ETHEREUM_NODE_URL",
  "chain_id": 1,  // 1 for Ethereum Mainnet, 5 for Goerli, etc.
  "private_key": "YOUR_PRIVATE_KEY",  // Without 0x prefix
  "wallet_address": "YOUR_WALLET_ADDRESS",  // With 0x prefix
  
  "tokens": {
    "WETH": {
      "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
      "decimals": 18
    },
    "USDC": {
      "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      "decimals": 6
    },
    "USDT": {
      "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
      "decimals": 6
    },
    "DAI": {
      "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
      "decimals": 18
    }
  },
  
  "log_level": "INFO",
  "max_paths_to_check": 100,
  "min_profit_threshold": 0.001,  // In ETH
  "slippage_tolerance": 50,  // In basis points (0.5%)
  "gas_limit_buffer": 20  // In percent
}
```

### 2.2 Flash Loan Configuration

Add to your `configs/config.json`:

```json
{
  // Existing config above...
  
  "flash_loans": {
    "enabled": true,
    "use_flashbots": true,
    "min_profit_basis_points": 200,  // 2%
    "max_trade_size": "1",  // In ETH
    "slippage_tolerance": 50,  // In basis points (0.5%)
    "transaction_timeout": 180,  // In seconds
    "balancer_vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
    "contract_address": {
      "mainnet": "0xYOUR_DEPLOYED_CONTRACT_ADDRESS",
      "testnet": "0xYOUR_TESTNET_CONTRACT_ADDRESS"
    }
  }
}
```

### 2.3 Flashbots Configuration

Add to your `configs/config.json`:

```json
{
  // Existing config above...
  
  "flashbots": {
    "relay_url": "https://relay.flashbots.net",
    "auth_signer_key": "YOUR_FLASHBOTS_AUTH_KEY",  // Without 0x prefix
    "min_profit_threshold": 1000000000000000  // 0.001 ETH in wei
  }
}
```

### 2.4 MEV Protection Configuration

Add to your `configs/config.json`:

```json
{
  // Existing config above...
  
  "mev_protection": {
    "enabled": true,
    "use_flashbots": true,
    "max_bundle_size": 5,
    "max_blocks_ahead": 3,
    "min_priority_fee": "1.5",  // In gwei
    "max_priority_fee": "3",  // In gwei
    "sandwich_detection": true,
    "frontrun_detection": true,
    "adaptive_gas": true
  }
}
```

### 2.5 Monitoring Dashboard Configuration

Create `config/monitor_config.json`:

```json
{
  "host": "localhost",
  "port": 8080,
  "refresh_interval": 30,
  "data_directory": "monitoring_data",
  "metrics_history_size": 100,
  "charts_enabled": true,
  "alerts_enabled": true,
  "profit_threshold_alert": 0.001,
  "gas_price_threshold_alert": 150,
  "mev_risk_threshold_alert": "high"
}
```

### 2.6 DEX Configuration

Modify `configs/dex_config.json` to include the DEXs you want to monitor:

```json
{
  "uniswap_v2": {
    "enabled": true,
    "factory_address": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    "router_address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
    "init_code_hash": "0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f",
    "fee": 30  // In basis points (0.3%)
  },
  "uniswap_v3": {
    "enabled": true,
    "factory_address": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
    "quoter_address": "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",
    "router_address": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
    "fee_tiers": [100, 500, 3000, 10000]
  },
  "sushiswap": {
    "enabled": true,
    "factory_address": "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",
    "router_address": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
    "init_code_hash": "0xe18a34eb0e04b04f7a0ac29a6e80748dca96319b42c54d679cb821dca90c6303",
    "fee": 30  // In basis points (0.3%)
  }
  // Add other DEXs as needed
}
```

## 3. Starting the System

### 3.1 Using the Launcher Script

The easiest way to run the system is using the PowerShell launcher script:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_example.ps1
```

This will present a menu with options:
1. Complete Arbitrage Example
2. Flash Loan Example
3. MEV Protection Example
4. Monitoring Dashboard
5. Run Tests

Choose the option based on what you want to run.

### 3.2 Running the Complete System

For production use, you'll want to run the complete arbitrage system:

```bash
python run_bot.py
```

This will start the arbitrage bot with all enhanced components.

### 3.3 Starting Individual Components

If you prefer to start components separately:

**Main Arbitrage Bot:**
```bash
python run_bot.py
```

**Monitoring Dashboard:**
```bash
python -m dashboard.arbitrage_monitor
```

**Path Testing:**
```bash
python test_path_finder.py
```

## 4. Component-Specific Instructions

### 4.1 Flash Loan Manager

To use the Flash Loan Manager in your code:

```python
from arbitrage_bot.core.flash_loan_manager_async import create_flash_loan_manager

# In your async code:
flash_loan_manager = await create_flash_loan_manager(web3_manager, config)

# Validate an arbitrage opportunity
validation = await flash_loan_manager.validate_arbitrage_opportunity(
    input_token=weth_address,
    output_token=weth_address,  # For circular arbitrage
    input_amount=amount_in,
    expected_output=expected_output,
    route=route
)

# Execute arbitrage if profitable
if validation['is_profitable']:
    result = await flash_loan_manager.execute_flash_loan_arbitrage(
        token_address=weth_address,
        amount=amount_in,
        route=route,
        min_profit=validation['net_profit'],
        use_flashbots=True
    )
```

### 4.2 MEV Protection Optimizer

To use the MEV Protection Optimizer:

```python
from arbitrage_bot.integration.mev_protection import create_mev_protection_optimizer

# In your async code:
mev_optimizer = await create_mev_protection_optimizer(web3_manager, config, flashbots_manager)

# Analyze mempool for MEV risk
risk_assessment = await mev_optimizer.analyze_mempool_risk()

# Optimize bundle strategy
bundle_strategy = await mev_optimizer.optimize_bundle_strategy(
    transactions=transactions,
    target_token_addresses=[weth_address, usdc_address],
    expected_profit=expected_profit,
    priority_level="high"
)

# Optimize and submit bundle
submission = await mev_optimizer.optimize_bundle_submission(
    bundle_id=bundle_id,
    gas_settings=bundle_strategy['gas_settings'],
    min_profit=min_profit
)
```

### 4.3 Monitoring Dashboard

Accessing the dashboard:
1. Start the monitoring dashboard using the launcher or direct command
2. Open a web browser and navigate to `http://localhost:8080`

Sending metrics to the dashboard from your code:

```python
from dashboard.arbitrage_monitor import update_metrics

# In your async code:
await update_metrics("http://localhost:8080", {
    "arbitrage": {
        "paths_found": 15,
        "paths_executed": 8,
        "success_rate": 53.33,
        "avg_execution_time": 120
    },
    "flash_loan": {
        "loans_executed": 8,
        "success_rate": 100.0,
        "average_cost": 0.0009,
        "total_volume": 10.5
    },
    "profit": {
        "total_profit": 0.085,
        "average_profit": 0.0106,
        "profit_after_gas": 0.073,
        "profit_margin": 3.2
    }
})
```

## 5. Troubleshooting

### 5.1 Terminal Issues

If you encounter terminal issues:

```bash
# Fix VSCode terminal
.\fix_vscode_terminal.bat

# Alternative terminal fix
.\fix_terminal.bat
```

### 5.2 Python Environment Issues

For Python environment issues:

```bash
# Check Python installation
python check_python.py

# Rebuild virtual environment
.\rebuild_venv.bat

# Memory-efficient rebuild
.\memory_efficient_rebuild.bat
```

### 5.3 Dependency Issues

If you encounter dependency issues:

```bash
# Install dependencies
pip install -r requirements.txt

# For development dependencies
pip install -r requirements-dev.txt
```

### 5.4 Connection Issues

If you have connection issues:

1. Check your Ethereum node URL
2. Verify Flashbots relay URL
3. Ensure your firewall allows outgoing connections
4. Check your private key and wallet address

### 5.5 Common Errors

**Insufficient Funds:**
- Ensure your wallet has enough ETH for gas
- Check token balances for trading

**Invalid Nonce:**
- Reset your nonce or wait for pending transactions to complete

**Gas Price Too Low:**
- Increase your gas price settings

**Slippage Error:**
- Increase slippage tolerance in configuration

## 6. Monitoring and Maintenance

### 6.1 Logs

Log files are stored in the `logs/` directory. Check these for detailed information about system operation.

### 6.2 Performance Metrics

Performance metrics are stored in:
- `analytics/gas_YYYYMM.json` - Gas usage metrics
- `analytics/performance_YYYYMM.json` - Performance metrics
- `monitoring_data/` - Dashboard metrics

### 6.3 Regular Maintenance

1. Update token addresses and DEX configurations as needed
2. Monitor gas usage and adjust parameters for optimal profit
3. Review performance metrics to identify optimization opportunities
4. Update dependencies periodically

### 6.4 Security Considerations

1. Store your private key securely
2. Use a dedicated wallet for arbitrage
3. Set appropriate max trade size limits
4. Regularly monitor for suspicious activities

## Conclusion

You now have a fully configured and operational arbitrage bot with enhanced features for MEV protection, flash loans, and monitoring. The system is designed to maximize profit while protecting from MEV attacks.

For detailed information about specific components, refer to:
- `cline_docs/arbitrage_integration_guide.md` - Integration instructions
- `cline_docs/monitoring_dashboard.md` - Dashboard documentation
- `MEMORY_BANK_UPDATES.md` - Memory bank information
- `DOCKER_AI_INTEGRATION.md` - Future Docker AI integration plan

For any issues or questions, consult the troubleshooting section or check the code documentation.