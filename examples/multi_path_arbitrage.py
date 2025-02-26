#!/usr/bin/env pythonctuall
"""
Example script for finding and executing multi-path arbitrage opportunities.

This script demonstrates how to use the PathFinder to discover arbitrage
opportunities across multiple DEXs and execute them using Flashbots bundles.
"""

import asyncio
import logging
import sys
from decimal import Decimal
from typing import Dict, List, Any
from web3 import Web3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# DEX configuration
from arbitrage_bot.utils.config_loader import load_config
from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.core.dex.dex_manager import create_dex_manager
from arbitrage_bot.core.path_finder import create_path_finder, ArbitragePath

# Token addresses for Base network
TOKEN_ADDRESSES = {
    'WETH': '0x4200000000000000000000000000000000000006',
    'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    'DAI': '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb',
    'USDbC': '0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA',
}

async def main():
    """Main function to demonstrate multi-path arbitrage."""
    try:
        # Load configuration
        config = load_config()
        
        # Create Web3 manager
        web3_manager = await create_web3_manager(
            provider_url=config.get("provider_url", "https://base.llamarpc.com"),
            chain_id=config.get("chain_id", 8453),
            private_key=config.get("private_key"),
            wallet_address=config.get("wallet_address")
        )
        
        # Create DEX manager
        dex_manager = await create_dex_manager(web3_manager, config)
        
        # Create path finder with specific path-finding options
        path_finder_config = {
            "max_path_length": 3,               # Maximum number of DEX hops
            "max_hops_per_dex": 2,              # Maximum hops within a single DEX
            "max_paths_to_check": 20,           # Max candidate paths to evaluate
            "min_profit_threshold": Web3.to_wei(0.001, 'ether'),  # Min 0.001 ETH profit
            "token_whitelist": [                # Only use these tokens
                TOKEN_ADDRESSES['WETH'].lower(),
                TOKEN_ADDRESSES['USDC'].lower(),
                TOKEN_ADDRESSES['DAI'].lower(),
                TOKEN_ADDRESSES['USDbC'].lower(),
            ],
            "common_tokens": [                  # Tokens that often form good paths
                TOKEN_ADDRESSES['WETH'].lower(),
                TOKEN_ADDRESSES['USDC'].lower(),
            ],
            "preferred_dexes": [                # Preferred DEXs (checked first)
                "baseswap",
                "pancakeswap"
            ]
        }
        
        # Create path finder
        path_finder = await create_path_finder(
            dex_manager=dex_manager,
            web3_manager=web3_manager,
            config={"path_finding": path_finder_config}
        )
        
        # Find arbitrage opportunities
        logger.info("Finding arbitrage opportunities...")
        
        # Amount to use (1 WETH)
        amount_in = Web3.to_wei(1, 'ether')
        
        # Look for circular arbitrage (WETH -> ... -> WETH)
        paths = await path_finder.find_arbitrage_opportunities(
            input_token=TOKEN_ADDRESSES['WETH'],
            output_token=TOKEN_ADDRESSES['WETH'],  # Same as input for circular arbitrage
            amount_in=amount_in,
            min_profit=Web3.to_wei(0.002, 'ether'),  # Minimum 0.002 ETH profit
            max_paths=5  # Return top 5 opportunities
        )
        
        # Display results
        if not paths:
            logger.info("No profitable arbitrage opportunities found")
            return
            
        logger.info(f"Found {len(paths)} profitable arbitrage opportunities:")
        
        for i, path in enumerate(paths, 1):
            # Calculate profit in ETH
            profit_eth = Web3.from_wei(path.estimated_profit, 'ether')
            
            # Calculate ROI percentage
            input_eth = Web3.from_wei(path.amount_in, 'ether')
            roi_percentage = (profit_eth / input_eth) * 100
            
            # Display path summary
            logger.info(f"Path {i}: Profit: {profit_eth:.6f} ETH (ROI: {roi_percentage:.2f}%)")
            
            # Show route details
            logger.info("  Route:")
            for step in path.route:
                from_token = step["token_in"][-6:]  # Last 6 chars of address
                to_token = step["token_out"][-6:]   # Last 6 chars of address
                logger.info(f"  - {step['dex']}: {from_token} → {to_token}, " + 
                           f"Amount: {Web3.from_wei(step['amount_in'], 'ether'):.6f} → " +
                           f"{Web3.from_wei(step['amount_out'], 'ether'):.6f}")
            
            # Simulate best path to validate profit
            if i == 1:
                logger.info("\nSimulating best arbitrage path...")
                simulation = await path_finder.simulate_arbitrage_path(path)
                
                if simulation["success"]:
                    logger.info("Simulation successful!")
                    
                    # Get profit details
                    profit_details = simulation["profit"]
                    logger.info(f"Confirmed profit: {Web3.from_wei(profit_details['net_profit_wei'], 'ether'):.6f} ETH")
                    logger.info(f"Gas cost: {Web3.from_wei(profit_details['gas_cost'], 'ether'):.6f} ETH")
                    
                    # Ask for confirmation to execute
                    if config.get("auto_execute", False):
                        logger.info("Auto-execution enabled, submitting arbitrage...")
                        execution = await path_finder.execute_arbitrage_path(path)
                        
                        if execution["success"]:
                            logger.info(f"Arbitrage executed! Bundle ID: {execution['bundle_id']}")
                        else:
                            logger.error(f"Arbitrage execution failed: {execution.get('error')}")
                    else:
                        logger.info("Auto-execution disabled. Set auto_execute: true in config to enable.")
                else:
                    logger.error(f"Simulation failed: {simulation.get('error')}")
        
    except Exception as e:
        logger.error(f"Error in arbitrage example: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())