#!/usr/bin/env python
"""
Production Arbitrage System

This script runs the arbitrage system in production mode.
"""

import asyncio
import logging
import json
import time
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
logger = logging.getLogger("production")

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Create a timestamp for log filename
timestamp = time.strftime("%Y%m%d-%H%M%S")
log_file = log_dir / f"arbitrage_production_{timestamp}.log"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

async def run_production_system():
    """Run the arbitrage system in production mode."""
    logger.info("=" * 70)
    logger.info("STARTING ARBITRAGE SYSTEM IN PRODUCTION MODE")
    logger.info("=" * 70)
    
    try:
        # Step 1: Import required components
        logger.info("Importing required components...")
        from arbitrage_bot.utils.config_loader import load_config
        from arbitrage_bot.core.web3.web3_manager import create_web3_manager
        from arbitrage_bot.integration.flashbots_integration import setup_flashbots_rpc
        from arbitrage_bot.core.flash_loan_manager_async import create_flash_loan_manager
        from arbitrage_bot.integration.mev_protection import create_mev_protection_optimizer
        from arbitrage_bot.core.dex.dex_manager import DexManager
        from arbitrage_bot.core.path_finder import PathFinder
        from arbitrage_bot.utils.dashboard_bridge import get_dashboard_bridge
        
        # Get dashboard bridge
        dashboard = get_dashboard_bridge()
        
        # Initialize system status
        await dashboard.update_system_status({
            'start_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'uptime': 0,
            'mev_risk_level': 'initializing',
            'flash_loans_enabled': False,
            'flashbots_enabled': False
        })
        
        # Step 2: Load production configuration
        logger.info("Loading production configuration...")
        config = load_config("configs/production.json")
        
        # Step 3: Initialize Web3Manager
        logger.info("Initializing Web3Manager...")
        web3_manager = await create_web3_manager(
            provider_url=config.get('provider_url'),
            chain_id=config.get('chain_id'),
            private_key=config.get('private_key')
        )
        
        chain_id = config.get('chain_id')
        logger.info(f"Connected to network with chain ID: {chain_id}")
        logger.info(f"Using wallet address: {web3_manager.wallet_address}")
        
        # Update network info in dashboard
        await dashboard.update_network({
            'chain_id': chain_id,
            'connected_nodes': 1,
            'block_number': await web3_manager.get_block_number(),
            'gas_price': await web3_manager.get_gas_price(),
            'rpc_latency': 0.0
        })
        
        # Step 4: Set up Flashbots RPC integration
        logger.info("Setting up Flashbots RPC integration...")
        flashbots_components = await setup_flashbots_rpc(
            web3_manager=web3_manager,
            config=config
        )
        
        flashbots_manager = flashbots_components['flashbots_manager']
        balance_validator = flashbots_components['balance_validator']
        
        # Update system status with Flashbots enabled
        await dashboard.update_system_status({
            'flashbots_enabled': True
        })
        
        # Step 5: Initialize Flash Loan Manager
        logger.info("Initializing Flash Loan Manager...")
        flash_loan_manager = await create_flash_loan_manager(
            web3_manager=web3_manager,
            config=config,
            flashbots_manager=flashbots_manager
        )
        
        # Update system status with flash loans enabled
        await dashboard.update_system_status({
            'flash_loans_enabled': True
        })
        
        # Step 6: Initialize MEV Protection Optimizer
        logger.info("Initializing MEV Protection Optimizer...")
        mev_optimizer = await create_mev_protection_optimizer(
            web3_manager=web3_manager,
            config=config,
            flashbots_manager=flashbots_manager
        )
        
        # Step 7: Set up DexManager and PathFinder
        logger.info("Initializing DexManager and PathFinder...")
        dex_manager = await DexManager.create(web3_manager, config)
        path_finder = PathFinder(dex_manager, config)
        
        # Update DEX stats in dashboard
        await dashboard.update_dex_stats({
            'active_dexes': len(dex_manager.dexes),
            'total_pools': await dex_manager.get_total_pools(),
            'monitored_tokens': len(await dex_manager.get_monitored_tokens()),
            'price_updates': 0
        })
        
        # Add system initialization event
        await dashboard.add_event(
            'SYSTEM_START',
            'Arbitrage system initialized successfully',
            {
                'chain_id': chain_id,
                'wallet': web3_manager.wallet_address,
                'flashbots_enabled': True,
                'flash_loans_enabled': True
            }
        )
        
        logger.info("System initialized successfully")
        logger.info("Running in production mode...")
        
        # Performance tracking
        start_time = time.time()
        opportunities_found = 0
        successful_trades = 0
        failed_trades = 0
        total_profit = 0.0
        
        # Main arbitrage loop
        while True:
            try:
                # Update network stats
                block_number = await web3_manager.get_block_number()
                gas_price = await web3_manager.get_gas_price()
                await dashboard.update_network({
                    'block_number': block_number,
                    'gas_price': gas_price
                })
                
                # Analyze mempool for MEV risk
                risk_assessment = await mev_optimizer.analyze_mempool_risk()
                risk_level = risk_assessment['risk_level']
                logger.info(f"MEV risk level: {risk_level}")
                
                # Update MEV protection stats
                await dashboard.update_mev_protection({
                    'risk_level': risk_level,
                    'frontrun_attempts': risk_assessment.get('frontrun_attempts', 0),
                    'sandwich_attacks': risk_assessment.get('sandwich_attacks', 0)
                })
                
                # Update system status
                await dashboard.update_system_status({
                    'mev_risk_level': risk_level,
                    'uptime': int(time.time() - start_time),
                    'flashbots_enabled': True,
                    'flash_loans_enabled': True
                })
                
                # Look for arbitrage opportunities
                logger.info("Scanning for arbitrage opportunities...")
                
                trading_config = config['trading']
                start_token = trading_config['pairs'][0]['token0']
                min_amount = int(float(trading_config['pairs'][0]['min_amount']) * 1e18)
                
                opportunities = await path_finder.find_arbitrage_paths(
                    start_token_address=start_token,
                    amount_in=min_amount,
                    min_profit_threshold=float(trading_config.get('min_profit', 0.25))
                )
                
                # Process opportunities
                for opportunity in opportunities:
                    try:
                        # Validate opportunity
                        simulation = await path_finder.simulate_execution(opportunity)
                        if simulation['success']:
                            opportunities_found += 1
                            
                            # Execute trade if profitable after gas
                            gas_cost = gas_price * trading_config.get('gas_limit', 500000) / 1e18
                            if simulation['profit_realized'] > gas_cost:
                                start_exec = time.time()
                                
                                # Execute trade through Flashbots
                                success = await flash_loan_manager.execute_arbitrage(
                                    opportunity['route'],
                                    flashbots=True
                                )
                                
                                exec_time = time.time() - start_exec
                                
                                if success:
                                    successful_trades += 1
                                    total_profit += simulation['profit_realized']
                                else:
                                    failed_trades += 1
                                    
                                await dashboard.add_event(
                                    'TRADE_EXECUTED',
                                    f"{'Successful' if success else 'Failed'} trade with profit {simulation['profit_realized']:.4f} ETH",
                                    {
                                        'profit': simulation['profit_realized'],
                                        'path': opportunity['route'],
                                        'execution_time': exec_time,
                                        'gas_price': gas_price
                                    }
                                )
                            
                    except Exception as e:
                        logger.error(f"Error processing opportunity: {e}", exc_info=True)
                        failed_trades += 1
                
                # Update path finder stats
                await dashboard.update_path_finder({
                    'paths_analyzed': path_finder.total_paths_analyzed,
                    'profitable_paths': path_finder.profitable_paths_found,
                    'max_profit_seen': path_finder.max_profit_seen,
                    'avg_path_length': path_finder.average_path_length
                })
                
                # Update performance metrics
                await dashboard.update_performance({
                    'opportunities_found': opportunities_found,
                    'successful_trades': successful_trades,
                    'failed_trades': failed_trades,
                    'total_profit_eth': total_profit,
                    'avg_execution_time': 0.0,
                    'gas_saved': 0.0
                })
                
                # Wait before next iteration
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in arbitrage loop: {e}", exc_info=True)
                await dashboard.add_event('ERROR', f"Error in arbitrage loop: {str(e)}")
                await asyncio.sleep(10)  # Wait longer on error
        
    except Exception as e:
        logger.error(f"Failed to start arbitrage system: {e}", exc_info=True)
        if 'dashboard' in locals():
            await dashboard.add_event('FATAL_ERROR', f"System startup failed: {str(e)}")
        raise

if __name__ == "__main__":
    """Run the production system."""
    try:
        asyncio.run(run_production_system())
    except KeyboardInterrupt:
        logger.info("System shutdown requested")
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
