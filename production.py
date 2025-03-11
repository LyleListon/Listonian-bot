#!/usr/bin/env python
"""
Production Arbitrage System

This script runs the arbitrage system in production mode with:
- Flash loan integration through Balancer
- MEV protection through Flashbots
- Multi-path arbitrage optimization
- Real-time monitoring
"""

import asyncio
import logging
import json
import time
import os
from pathlib import Path
from typing import Dict, Any
from eth_typing import ChecksumAddress

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

logger = logging.getLogger("production")

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
        from arbitrage_bot.core.web3.balance_validator import create_balance_validator
        from arbitrage_bot.core.web3.flashbots.flashbots_provider import create_flashbots_provider
        from arbitrage_bot.core.web3.flashbots.risk_analyzer import RiskAnalyzer
        from arbitrage_bot.core.web3.flashbots.bundle_optimizer import BundleOptimizer
        from arbitrage_bot.core.web3.flashbots.attack_detector import AttackDetector
        from arbitrage_bot.core.unified_flash_loan_manager import create_unified_flash_loan_manager
        from arbitrage_bot.core.dex.dex_manager import DexManager
        from arbitrage_bot.core.path_finder import PathFinder
        
        # Step 2: Load production configuration
        logger.info("Loading production configuration...")
        config = load_config("configs/production.json")
        
        # Step 3: Initialize Web3Manager
        logger.info("Initializing Web3Manager...")
        web3_manager = await create_web3_manager(config)
        
        logger.info(f"Connected to network with chain ID: {config['web3']['chain_id']}")
        logger.info(f"Using wallet address: {web3_manager.wallet_address}")
        
        # Step 4: Initialize Balance Validator
        logger.info("Initializing Balance Validator...")
        balance_validator = await create_balance_validator(
            web3_manager=web3_manager,
            config=config
        )
        
        # Step 5: Initialize Flashbots Provider
        logger.info("Initializing Flashbots Provider...")
        flashbots_provider = await create_flashbots_provider(
            web3_manager=web3_manager,
            relay_url=config['flashbots']['relay_url'],
            auth_key=config['flashbots']['auth_key']
        )
        
        # Step 6: Set up Flashbots components
        logger.info("Setting up Flashbots components...")
        risk_analyzer = RiskAnalyzer(web3_manager, config)
        bundle_optimizer = BundleOptimizer(web3_manager, risk_analyzer, config)
        attack_detector = AttackDetector(web3_manager, config)
        
        # Step 7: Set up DexManager and PathFinder
        logger.info("Initializing DexManager and PathFinder...")
        dex_manager = await DexManager.create(web3_manager, config)
        path_finder = PathFinder(dex_manager, config)
        
        # Step 8: Initialize Flash Loan Manager
        logger.info("Initializing Flash Loan Manager...")
        flash_loan_manager = await create_unified_flash_loan_manager(
            web3_manager=web3_manager,
            dex_manager=dex_manager,
            balance_validator=balance_validator,
            flashbots_provider=flashbots_provider,
            config=config
        )
        
        logger.info("System initialized successfully")
        logger.info("Running in production mode...")
        
        # Get configuration values
        start_token_address = ChecksumAddress(config['tokens']['WETH']['address'])
        scan_amount = int(config['scan']['amount_wei'])
        max_paths = config['scan']['max_paths']
        
        # Main arbitrage loop
        while True:
            try:
                # Step 1: Analyze mempool for MEV risk
                risk_assessment = await risk_analyzer.analyze_mempool_risk()
                logger.info(f"MEV risk level: {risk_assessment['risk_level']}")
                
                # Step 2: Check for MEV attacks
                current_block = web3_manager.w3.eth.block_number
                recent_attacks = await attack_detector.scan_for_attacks(
                    start_block=current_block - 10
                )
                if recent_attacks:
                    logger.warning(f"Detected {len(recent_attacks)} potential MEV attacks")
                
                # Step 3: Find arbitrage opportunities
                logger.info("Scanning for arbitrage opportunities...")
                paths = await path_finder.find_arbitrage_paths(
                    start_token_address=start_token_address,
                    amount_in=scan_amount,
                    max_paths=max_paths
                )
                
                # Step 4: Process opportunities
                for path in paths:
                    try:
                        # Validate opportunity profitability
                        bundle_strategy = await bundle_optimizer.optimize_bundle_strategy(
                            transactions=path.transactions,
                            target_token_addresses=path.tokens,
                            expected_profit=path.expected_profit
                        )
                        
                        # Check if bundle would be profitable
                        profitability = await bundle_optimizer.validate_bundle_profitability(
                            transactions=path.transactions,
                            gas_settings=bundle_strategy['gas_settings'],
                            expected_profit=path.expected_profit
                        )
                        
                        if profitability['is_profitable']:
                            logger.info(f"Found profitable opportunity: {profitability['net_profit']} wei")
                            
                            # Execute the opportunity
                            await flash_loan_manager.execute_flash_loan(
                                token_address=path.tokens[0],
                                amount=path.amounts[0],
                                target_contract=path.target_contract,
                                callback_data=path.callback_data,
                                path=path
                            )
                    
                    except Exception as e:
                        logger.error(f"Error processing opportunity: {e}", exc_info=True)
                        continue
                
                # Wait before next iteration
                await asyncio.sleep(config['scan']['interval'])
                
            except Exception as e:
                logger.error(f"Error in arbitrage loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait longer on error
        
    except Exception as e:
        logger.error(f"Failed to start arbitrage system: {e}", exc_info=True)
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
