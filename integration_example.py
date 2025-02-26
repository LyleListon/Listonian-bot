#!/usr/bin/env python
"""
Integration Example for Arbitrage Bot Optimizations

This script demonstrates how to integrate the new optimization features:
1. Gas Optimization Framework
2. Enhanced Multi-Hop Path Support
3. Path Finding Test Framework

It can be run without relying on VSCode's terminal integration.
"""

import asyncio
import logging
import json
from pathlib import Path
from decimal import Decimal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def integrate_optimizations():
    """Demonstrate integration of optimization features."""
    logger.info("=" * 70)
    logger.info("ARBITRAGE BOT OPTIMIZATION INTEGRATION EXAMPLE")
    logger.info("=" * 70)
    
    try:
        # Step 1: Import integration utilities
        logger.info("\n[Step 1] Importing integration utilities")
        # First fix any circular imports and syntax issues
        from arbitrage_bot.utils.config_loader import load_config
        # Import with separate statements to avoid line length issues
        from arbitrage_bot.integration import setup_optimized_system
        from arbitrage_bot.integration import run_optimization_test
        logger.info("✓ Successfully imported integration utilities")
        
        # Step 2: Set up the optimized system
        logger.info("\n[Step 2] Setting up optimized system")
        logger.info("This configures gas optimization, enhanced multi-hop, and path finding")
        components = await setup_optimized_system()
        
        # Extract components for easier access
        web3_manager = components['web3_manager']
        dex_manager = components['dex_manager']
        gas_optimizer = components['gas_optimizer']
        path_finder = components['path_finder']
        config = components['config']
        
        logger.info(f"✓ System initialized with {len(dex_manager.dex_instances)} DEXs")
        
        # Step 3: Demonstrate gas optimization
        logger.info("\n[Step 3] Demonstrating gas optimization")
        
        # Get token addresses
        weth_address = web3_manager.get_weth_address()
        usdc_address = config.get('tokens', {}).get('USDC', {}).get('address', 
                                '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
        
        # Get gas estimate for a swap path
        gas_estimate = await gas_optimizer.estimate_gas_for_path(
            path=[weth_address, usdc_address],
            dex_name="baseswap_v3",
            operation_type="swap"
        )
        
        # Get optimal gas price
        gas_price = await gas_optimizer.estimate_optimal_gas_price()
        
        logger.info(f"Gas estimate for WETH→USDC swap: {gas_estimate}")
        logger.info(f"Optimal gas price: {gas_price} wei")
        
        # Step 4: Demonstrate enhanced multi-hop path finding
        logger.info("\n[Step 4] Demonstrating enhanced multi-hop paths")
        
        # Find the best V3 DEX for demonstration
        v3_dex = None
        for name, dex in dex_manager.dex_instances.items():
            if 'V3' in name.upper() or name.upper().endswith('V3'):
                v3_dex = dex
                v3_dex_name = name
                break
        
        if v3_dex and hasattr(v3_dex, 'find_best_path'):
            # Amount in: 0.1 ETH in wei
            amount_in = web3_manager.w3.to_wei(0.1, 'ether')
            
            # Find the best path between tokens
            logger.info(f"Finding best path on {v3_dex_name} for 0.1 ETH...")
            best_path, best_fees, expected_output = await v3_dex.find_best_path(
                token_in=weth_address,
                token_out=usdc_address,
                amount_in=amount_in
            )
            
            # Format the output amount for display
            output_formatted = Decimal(expected_output) / Decimal(10**6)  # USDC has 6 decimals
            
            logger.info(f"Best path found: {best_path}")
            logger.info(f"Fee tiers: {[v3_dex.fee_tier_names.get(fee, str(fee)) for fee in best_fees]}")
            logger.info(f"Expected output: {output_formatted} USDC")
        else:
            logger.warning("No enhanced V3 DEX found or DEX doesn't support find_best_path")
        
        # Step 5: Run a quick optimization test
        logger.info("\n[Step 5] Running optimization test")
        logger.info("This will test all components together with 3 token pairs")
        
        results = await run_optimization_test(components, count=3)
        
        # Display results summary
        logger.info("\n----- Test Results -----")
        logger.info(f"Success rate: {results['success_rate']*100:.1f}%")
        logger.info(f"Avg execution time: {results['avg_execution_time']*1000:.1f}ms")
        logger.info(f"Multi-hop paths found: {results['multi_hop_paths']}")
        
        # Save detailed results
        output_path = Path("optimization_test_results.json")
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Full results saved to {output_path}")
        
        # Step 6: Provide integration code example
        logger.info("\n[Step 6] Integration code example for your main bot")
        logger.info("""
# Add to your main bot code:

from arbitrage_bot.integration import setup_optimized_system

# In your async initialization function:
components = await setup_optimized_system()

# Extract components for use in your bot
web3_manager = components['web3_manager']
dex_manager = components['dex_manager']
gas_optimizer = components['gas_optimizer']
path_finder = components['path_finder']

# Now use these optimized components in your arbitrage logic
# For example, find arbitrage paths with optimized components:
paths = await path_finder.find_arbitrage_paths(
    token_in=weth_address,
    token_out=usdc_address,
    amount_in=amount_in
)
        """)
        
        logger.info("=" * 70)
        logger.info("INTEGRATION EXAMPLE COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
        return results
        
    except Exception as e:
        logger.error(f"Error in integration example: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    """Run the integration example."""
    asyncio.run(integrate_optimizations())