# Arbitrage Integration Guide

This guide explains how to integrate the Flash Loan Manager, Flashbots RPC, and MEV Protection Optimizer into a complete arbitrage system for maximum profit and protection.

## System Overview

The enhanced arbitrage system consists of several key components working together:

1. **AsyncFlashLoanManager**: Handles flash loan operations with multi-token support
2. **Flashbots RPC Integration**: Provides private transaction submission to avoid MEV attacks
3. **MEV Protection Optimizer**: Enhances protection against MEV with advanced strategies
4. **Path Finder**: Discovers profitable arbitrage opportunities across DEXs

These components work together to:
- Find profitable arbitrage opportunities
- Execute them efficiently using flash loans
- Protect transactions from MEV attacks
- Optimize gas usage for maximum profit

## Integration Guide

### Step 1: Initialize Components

First, initialize all required components in your main arbitrage script:

```python
import asyncio
import logging
from decimal import Decimal

from arbitrage_bot.utils.config_loader import load_config
from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.integration.flashbots_integration import setup_flashbots_rpc
from arbitrage_bot.core.flash_loan_manager_async import create_flash_loan_manager
from arbitrage_bot.integration.mev_protection import create_mev_protection_optimizer
from arbitrage_bot.core.dex.path_finder import PathFinder
from arbitrage_bot.core.dex.dex_manager import DexManager

async def initialize_components():
    # Load configuration
    config = load_config()
    
    # Initialize Web3Manager
    web3_manager = await create_web3_manager(
        provider_url=config.get('provider_url'),
        chain_id=config.get('chain_id'),
        private_key=config.get('private_key')
    )
    
    # Set up Flashbots RPC
    flashbots_components = await setup_flashbots_rpc(
        web3_manager=web3_manager,
        config=config
    )
    
    flashbots_manager = flashbots_components['flashbots_manager']
    balance_validator = flashbots_components['balance_validator']
    
    # Initialize Flash Loan Manager
    flash_loan_manager = await create_flash_loan_manager(
        web3_manager=web3_manager,
        config=config,
        flashbots_manager=flashbots_manager
    )
    
    # Initialize MEV Protection Optimizer
    mev_optimizer = await create_mev_protection_optimizer(
        web3_manager=web3_manager,
        config=config,
        flashbots_manager=flashbots_manager
    )
    
    # Initialize DexManager and PathFinder
    dex_manager = await DexManager.create(web3_manager, config)
    path_finder = PathFinder(dex_manager, config)
    
    return {
        'web3_manager': web3_manager,
        'flashbots_manager': flashbots_manager,
        'balance_validator': balance_validator,
        'flash_loan_manager': flash_loan_manager,
        'mev_optimizer': mev_optimizer,
        'dex_manager': dex_manager,
        'path_finder': path_finder,
        'config': config
    }
```

### Step 2: Implement Arbitrage Execution

Create a function to execute arbitrage with all protections and optimizations:

```python
async def execute_protected_arbitrage(components):
    """Execute arbitrage with flash loans and MEV protection."""
    web3_manager = components['web3_manager']
    flashbots_manager = components['flashbots_manager']
    flash_loan_manager = components['flash_loan_manager']
    mev_optimizer = components['mev_optimizer']
    path_finder = components['path_finder']
    config = components['config']
    
    # Get token addresses
    weth_address = web3_manager.get_weth_address()
    
    # Set input amount for arbitrage
    amount_in = web3_manager.w3.to_wei(0.1, 'ether')  # 0.1 WETH
    
    # 1. Find profitable arbitrage paths
    paths = await path_finder.find_arbitrage_paths(
        token_in=weth_address,
        token_out=weth_address,  # Circular arbitrage
        amount_in=amount_in
    )
    
    # No paths found
    if not paths:
        logging.info("No profitable paths found")
        return None
    
    # Process each path in order of profitability
    for path in paths:
        try:
            # 2. Convert path to proper route format
            route = path.to_route_format()
            
            # 3. Validate with flash loan costs included
            validation = await flash_loan_manager.validate_arbitrage_opportunity(
                input_token=path.input_token,
                output_token=path.output_token,
                input_amount=path.amount_in,
                expected_output=path.expected_output,
                route=route
            )
            
            # Skip if not profitable after flash loan costs
            if not validation['is_profitable']:
                logging.info(f"Path not profitable after flash loan costs: net profit = {validation['net_profit']}")
                continue
                
            # 4. Check current mempool for MEV risk
            mev_risk = await mev_optimizer.analyze_mempool_risk()
            logging.info(f"MEV Risk Level: {mev_risk['risk_level']}")
            
            # Skip if extremely high risk and small profit
            if mev_risk['risk_level'] == 'high' and validation['profit_margin'] < 0.01:
                logging.info("Skipping due to high MEV risk with small profit margin")
                continue
            
            # 5. Prepare flash loan transaction
            tx_preparation = await flash_loan_manager.prepare_flash_loan_transaction(
                token_address=path.input_token,
                amount=path.amount_in,
                route=route,
                min_profit=validation['net_profit']
            )
            
            # Skip if transaction preparation failed
            if not tx_preparation['success']:
                logging.error(f"Failed to prepare transaction: {tx_preparation.get('error')}")
                continue
                
            # 6. Optimize bundle strategy
            transactions = [tx_preparation['transaction']]
            
            bundle_strategy = await mev_optimizer.optimize_bundle_strategy(
                transactions=transactions,
                target_token_addresses=[path.input_token, path.output_token],
                expected_profit=validation['net_profit'],
                priority_level="high"  # High priority for arbitrage
            )
            
            # 7. Create and simulate bundle
            from arbitrage_bot.integration.flashbots_integration import create_and_simulate_bundle
            
            bundle = await create_and_simulate_bundle(
                web3_manager=web3_manager,
                transactions=transactions,
                token_addresses=[path.input_token, path.output_token],
                opts={
                    'gas_settings': bundle_strategy['gas_settings']
                }
            )
            
            # Skip if simulation fails
            if not bundle['success']:
                logging.error(f"Bundle simulation failed: {bundle.get('error')}")
                continue
                
            # 8. Optimize and submit bundle
            submission = await mev_optimizer.optimize_bundle_submission(
                bundle_id=bundle['bundle_id'],
                gas_settings=bundle_strategy['gas_settings'],
                min_profit=validation['net_profit']
            )
            
            # 9. Log results
            if submission['success']:
                logging.info(f"Protected arbitrage executed successfully!")
                logging.info(f"Bundle ID: {submission['bundle_id']}")
                logging.info(f"Target blocks: {submission['target_blocks']}")
                logging.info(f"Estimated profit: {web3_manager.w3.from_wei(validation['net_profit'], 'ether')} WETH")
                
                # Return successful result
                return {
                    'success': True,
                    'path': path,
                    'validation': validation,
                    'bundle': bundle,
                    'submission': submission
                }
            else:
                logging.error(f"Bundle submission failed: {submission.get('error')}")
                
        except Exception as e:
            logging.error(f"Error executing arbitrage for path: {e}", exc_info=True)
    
    # If we reach here, no paths were successfully executed
    return {
        'success': False,
        'error': "No viable arbitrage paths could be executed"
    }
```

### Step 3: Create Main Loop

Implement the main arbitrage loop that continuously looks for opportunities:

```python
async def main():
    """Main arbitrage execution loop."""
    # Initialize components
    components = await initialize_components()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='arbitrage.log'
    )
    
    # Log successful initialization
    logging.info("Arbitrage system initialized")
    
    # Execute continuous arbitrage monitoring loop
    try:
        while True:
            try:
                # Execute protected arbitrage
                result = await execute_protected_arbitrage(components)
                
                if result and result.get('success'):
                    # Log successful arbitrage
                    logging.info(f"Successful arbitrage executed")
                    
                    # Get profit amount for logging
                    validation = result.get('validation', {})
                    net_profit = validation.get('net_profit', 0)
                    profit_eth = components['web3_manager'].w3.from_wei(net_profit, 'ether')
                    
                    logging.info(f"Net profit: {profit_eth} ETH")
                    
                    # Optional: Add delay after successful arbitrage
                    await asyncio.sleep(10)
                else:
                    # No viable opportunities found
                    logging.info("No viable arbitrage opportunities found")
                    
                    # Check for MEV attacks
                    mev_optimizer = components['mev_optimizer']
                    attacks = await mev_optimizer.detect_mev_attacks()
                    
                    if attacks:
                        logging.warning(f"Detected {len(attacks)} potential MEV attacks")
                    
                    # Wait before checking again
                    await asyncio.sleep(5)
                
            except Exception as e:
                logging.error(f"Error in arbitrage loop: {e}", exc_info=True)
                await asyncio.sleep(30)  # Longer delay after error
    
    except KeyboardInterrupt:
        logging.info("Arbitrage system shutting down")
    
    finally:
        # Clean up resources
        logging.info("Cleaning up resources")
        # Add any cleanup code here

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration Options

### Flash Loan Configuration

Add these options to your config.json:

```json
{
  "flash_loans": {
    "enabled": true,
    "use_flashbots": true,
    "min_profit_basis_points": 200,
    "max_trade_size": "1",
    "slippage_tolerance": 50,
    "transaction_timeout": 180,
    "balancer_vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
    "contract_address": {
      "mainnet": "0x...",
      "testnet": "0xa111E81d1F6F8bF648d1405ADf45aAC92602BcA8"
    }
  }
}
```

### Flashbots Configuration

Add these options to your config.json:

```json
{
  "flashbots": {
    "relay_url": "https://relay.flashbots.net",
    "auth_signer_key": "0x...",
    "min_profit_threshold": 1000000000000000
  }
}
```

### MEV Protection Configuration

Add these options to your config.json:

```json
{
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
}
```

## Profit Maximization Strategies

To maximize profits, the system employs several strategies:

1. **Optimal Path Selection**: The PathFinder identifies the most profitable arbitrage paths across multiple DEXs

2. **Flash Loan Cost Optimization**: The AsyncFlashLoanManager calculates all costs accurately to ensure only truly profitable opportunities are executed

3. **MEV Protection**: The MEV Protection Optimizer prevents value extraction from arbitrage transactions:
   - **Risk Assessment**: Analyzes mempool for current MEV activity
   - **Bundle Optimization**: Creates optimal transaction bundles
   - **Gas Price Strategy**: Sets gas prices based on expected profit and current conditions
   - **Attack Detection**: Monitors and responds to MEV attack patterns

4. **Multi-Token Arbitrage**: Supports a wide range of tokens for more opportunities

5. **Gas Optimization**: Intelligently sets gas parameters based on historical data and current conditions

## Monitoring and Analytics

The system provides several monitoring capabilities:

1. **MEV Attack Statistics**:
```python
stats = await mev_optimizer.get_mev_attack_statistics()
print(f"Total attacks detected: {stats['total_attacks']}")
print(f"Current risk level: {stats['risk_level']}")
```

2. **Bundle Statistics**:
```python
stats = await mev_optimizer.get_bundle_statistics()
print(f"Total bundles: {stats['total_bundles']}")
print(f"Success rate: {stats['success_rate'] * 100:.2f}%")
```

3. **Flash Loan Validation**:
```python
validation = await flash_loan_manager.validate_arbitrage_opportunity(
    input_token=token_in,
    output_token=token_out,
    input_amount=amount_in,
    expected_output=expected_output,
    route=route
)
print(f"Is profitable: {validation['is_profitable']}")
print(f"Net profit: {validation['net_profit']}")
print(f"Profit margin: {validation['profit_margin'] * 100:.2f}%")
```

## Examples

See the following example files for detailed usage:

1. `flash_loan_example.py`: Demonstrates the AsyncFlashLoanManager
2. `flashbots_example.py`: Demonstrates the Flashbots RPC integration
3. `mev_protection_example.py`: Demonstrates the MEV Protection Optimizer

## Testing

Run the comprehensive test suite to verify functionality:

```bash
pytest tests/flashbots_flash_loan_test.py -v
```

This guide provides a complete framework for integrating all components of the enhanced arbitrage system to maximize profits while protecting from MEV attacks.