#!/usr/bin/env python
"""
Example script demonstrating multi-hop arbitrage path finding.

This script shows how to find and execute arbitrage opportunities
using multi-hop paths within individual DEXs.
"""

import asyncio
import logging
import sys
import os
from decimal import Decimal
from web3 import Web3

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arbitrage_bot.core.path_finder import create_path_finder, ArbitragePath
from arbitrage_bot.utils.config_loader import load_config
from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.core.dex.dex_manager import create_dex_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def find_multi_hop_opportunities(
    input_token: str,
    amount_in: int = None,
    config: dict = None
):
    """Find multi-hop arbitrage opportunities."""
    logger.info("Finding multi-hop arbitrage opportunities")
    
    # Load config if not provided
    if not config:
        config = load_config()
    
    # Enable multi-hop paths in config
    if "path_finding" not in config:
        config["path_finding"] = {}
    config["path_finding"]["enable_multi_hop_paths"] = True
    config["path_finding"]["max_hops_per_dex"] = 3  # Allow up to 3 hops within a DEX
    
    # Create Web3 manager
    web3_manager = await create_web3_manager(config)
    
    # Create DEX manager
    dex_manager = await create_dex_manager(web3_manager, config)
    
    # Create path finder
    path_finder = await create_path_finder(dex_manager, web3_manager, config)
    
    # Find arbitrage opportunities
    opportunities = await path_finder.find_arbitrage_opportunities(
        input_token=input_token,
        output_token=input_token,  # Circular path (same start and end token)
        amount_in=amount_in,
        min_profit=0,  # Show all opportunities, even if small profit
        max_paths=10    # Return up to 10 paths
    )
    
    # Group paths by type (multi-hop vs direct)
    multi_hop_paths = []
    direct_paths = []
    
    for path in opportunities:
        has_multi_hop = any(len(step.get('path', [])) > 2 for step in path.route)
        if has_multi_hop:
            multi_hop_paths.append(path)
        else:
            direct_paths.append(path)
    
    # Display results
    logger.info(f"Found {len(opportunities)} arbitrage opportunities:")
    logger.info(f"  - {len(multi_hop_paths)} multi-hop paths")
    logger.info(f"  - {len(direct_paths)} direct paths")
    
    # Display top opportunities
    if opportunities:
        logger.info("\nTop opportunities:")
        for i, path in enumerate(opportunities[:5]):
            # Calculate profit in ETH
            profit_eth = Web3.from_wei(path.estimated_profit, 'ether')
            
            # Get path description
            path_desc = []
            for step in path.route:
                if len(step.get('path', [])) > 2:
                    # Multi-hop path
                    hop_desc = " -> ".join([token[-6:] for token in step['path']])
                    path_desc.append(f"{step['dex']}({hop_desc})")
                else:
                    # Direct path
                    path_desc.append(f"{step['dex']}({step['token_in'][-6:]} -> {step['token_out'][-6:]})")
            
            path_str = " → ".join(path_desc)
            
            logger.info(f"{i+1}. Profit: {profit_eth:.6f} ETH - Path: {path_str}")
            
            # Show gas details
            gas_cost_eth = Web3.from_wei(path.estimated_gas_cost * 10**9, 'ether')  # Assuming 1 GWEI
            logger.info(f"   Gas: {path.estimated_gas_cost} ({gas_cost_eth:.6f} ETH at 1 GWEI)")
    
    return opportunities

async def simulate_and_execute_opportunity(
    path_finder,
    opportunity: ArbitragePath,
    min_profit_eth: float = 0.001
):
    """Simulate and potentially execute an arbitrage opportunity."""
    logger.info(f"Simulating arbitrage opportunity with {len(opportunity.route)} steps")
    
    # Convert min profit to wei
    min_profit_wei = Web3.to_wei(min_profit_eth, 'ether')
    
    # Simulate the opportunity
    simulation = await path_finder.simulate_arbitrage_path(
        path=opportunity,
        use_flashbots=True
    )
    
    if not simulation["success"]:
        logger.error(f"Simulation failed: {simulation.get('error', 'Unknown error')}")
        return False
    
    logger.info("Simulation successful!")
    
    # Check profit from simulation
    profit = simulation.get("profit", {}).get("net_profit_wei", 0)
    profit_eth = Web3.from_wei(profit, 'ether')
    
    logger.info(f"Estimated profit: {profit_eth:.6f} ETH")
    
    # Check if profit meets minimum threshold
    if profit < min_profit_wei:
        logger.warning(f"Profit below minimum threshold of {min_profit_eth} ETH, skipping execution")
        return False
    
    # In a real scenario, you might execute the opportunity here
    # await path_finder.execute_arbitrage_path(opportunity, use_flashbots=True, min_profit=min_profit_wei)
    
    # For this example, we'll just log that we would execute
    logger.info(f"Would execute opportunity with {profit_eth:.6f} ETH profit")
    return True

async def main():
    """Main function."""
    logger.info("Starting multi-hop arbitrage example")
    
    # Example token (WETH on Base)
    weth_address = "0x4200000000000000000000000000000000000006"
    
    # Default amount (1 ETH)
    amount_in = Web3.to_wei(1, 'ether')
    
    try:
        # Find arbitrage opportunities
        opportunities = await find_multi_hop_opportunities(
            input_token=weth_address,
            amount_in=amount_in
        )
        
        if not opportunities:
            logger.info("No profitable opportunities found")
            return
        
        # Get the most profitable opportunity
        best_opportunity = opportunities[0]
        
        # Show detailed information about the best opportunity
        logger.info("\nBest opportunity details:")
        logger.info(f"Input: {Web3.from_wei(best_opportunity.amount_in, 'ether')} ETH")
        logger.info(f"Output: {Web3.from_wei(best_opportunity.estimated_output, 'ether')} ETH")
        logger.info(f"Profit: {Web3.from_wei(best_opportunity.estimated_profit, 'ether')} ETH")
        logger.info(f"Gas cost: {best_opportunity.estimated_gas_cost}")
        
        # For each step in the path, show details including the full token path
        logger.info("\nPath steps:")
        for i, step in enumerate(best_opportunity.route):
            input_amount = Web3.from_wei(step['amount_in'], 'ether') if step['token_in'] == weth_address else step['amount_in']
            output_amount = Web3.from_wei(step['amount_out'], 'ether') if step['token_out'] == weth_address else step['amount_out']
            
            # Check if this is a multi-hop step
            if len(step.get('path', [])) > 2:
                token_path = " -> ".join([token[-6:] for token in step['path']])
                logger.info(f"Step {i+1}: {step['dex']} - Multi-hop: {token_path}")
            else:
                logger.info(f"Step {i+1}: {step['dex']} - {step['token_in'][-6:]} -> {step['token_out'][-6:]}")
                
            logger.info(f"  In: {input_amount} {'ETH' if step['token_in'] == weth_address else ''}")
            logger.info(f"  Out: {output_amount} {'ETH' if step['token_out'] == weth_address else ''}")
            logger.info(f"  Gas: {step['gas_estimate']}")
        
        # Create path finder again for simulation
        config = load_config()
        web3_manager = await create_web3_manager(config)
        dex_manager = await create_dex_manager(web3_manager, config)
        path_finder = await create_path_finder(dex_manager, web3_manager, config)
        
        # Simulate the best opportunity
        await simulate_and_execute_opportunity(
            path_finder=path_finder,
            opportunity=best_opportunity,
            min_profit_eth=0.001  # Minimum 0.001 ETH profit
        )
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())