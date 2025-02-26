"""Flashbots RPC integration for arbitrage bot.

This module provides utilities for integrating and testing the Flashbots RPC
functionality with the arbitrage bot system.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

# Import core components
from ..core.web3.web3_manager import Web3Manager, create_web3_manager
from ..core.web3.flashbots_manager import FlashbotsManager
from ..core.web3.balance_validator import create_balance_validator
from ..utils.config_loader import load_config

logger = logging.getLogger(__name__)


async def setup_flashbots_rpc(
    web3_manager: Optional[Web3Manager] = None,
    config: Optional[Dict[str, Any]] = None,
    flashbots_relay_url: Optional[str] = None,
    auth_signer_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Set up and initialize the Flashbots RPC integration.
    
    Args:
        web3_manager: Existing Web3Manager instance (optional)
        config: Configuration dictionary (optional)
        flashbots_relay_url: Flashbots relay URL (optional)
        auth_signer_key: Private key for Flashbots auth signer (optional)
        
    Returns:
        Dictionary with initialized components
    """
    try:
        # Load config if not provided
        if config is None:
            config = load_config()
        
        # Use config values if parameters not provided
        if flashbots_relay_url is None:
            flashbots_relay_url = config.get("flashbots", {}).get(
                "relay_url", "https://relay.flashbots.net")
        
        if auth_signer_key is None:
            auth_signer_key = config.get("flashbots", {}).get(
                "auth_signer_key", config.get("private_key"))
        
        # Create or update Web3Manager
        if web3_manager is None:
            # Create with Flashbots enabled
            web3_manager = await create_web3_manager(
                provider_url=config.get("provider_url"),
                chain_id=config.get("chain_id"),
                private_key=config.get("private_key"),
                wallet_address=config.get("wallet_address"),
                flashbots_enabled=True,
                flashbots_relay_url=flashbots_relay_url
            )
        elif not hasattr(web3_manager, 'flashbots_manager') or web3_manager.flashbots_manager is None:
            # Initialize Flashbots on existing manager
            web3_manager.flashbots_enabled = True
            web3_manager.flashbots_relay_url = flashbots_relay_url
            web3_manager.flashbots_manager = FlashbotsManager(
                web3_manager,
                auth_signer_key=auth_signer_key,
                flashbots_relay_url=flashbots_relay_url
            )
            await web3_manager.flashbots_manager.setup_flashbots_provider()
        
        # Initialize balance validator if needed
        if not hasattr(web3_manager.flashbots_manager, 'balance_validator') or web3_manager.flashbots_manager.balance_validator is None:
            balance_validator = await create_balance_validator(web3_manager)
            web3_manager.flashbots_manager.balance_validator = balance_validator
        
        logger.info("Flashbots RPC integration initialized successfully")
        
        return {
            'web3_manager': web3_manager,
            'flashbots_manager': web3_manager.flashbots_manager,
            'balance_validator': web3_manager.flashbots_manager.balance_validator,
            'config': config
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize Flashbots RPC integration: {e}")
        raise


async def test_flashbots_connection(
    web3_manager: Optional[Web3Manager] = None,
    components: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Test the Flashbots RPC connection by retrieving user stats.
    
    Args:
        web3_manager: Web3Manager instance with Flashbots enabled
        components: Components dictionary from setup_flashbots_rpc
        
    Returns:
        Dictionary with test results
    """
    try:
        # Get web3_manager from components if provided
        if components is not None and web3_manager is None:
            web3_manager = components.get('web3_manager')
        
        if web3_manager is None or not hasattr(web3_manager, 'flashbots_manager') or web3_manager.flashbots_manager is None:
            raise ValueError("Flashbots manager not available")
        
        # Test user stats to verify the connection
        stats = await web3_manager.w3.flashbots.get_user_stats()
        
        # Check if we're getting a valid response
        is_valid = isinstance(stats, dict)
        
        logger.info(f"Flashbots connection test: {'success' if is_valid else 'failed'}")
        
        return {
            'success': is_valid,
            'stats': stats if is_valid else None,
            'error': None if is_valid else "Invalid response from Flashbots"
        }
        
    except Exception as e:
        logger.error(f"Flashbots connection test failed: {e}")
        return {
            'success': False,
            'stats': None,
            'error': str(e)
        }


async def create_and_simulate_bundle(
    web3_manager: Web3Manager,
    transactions: List[Dict[str, Any]],
    token_addresses: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create and simulate a transaction bundle through Flashbots.
    
    Args:
        web3_manager: Web3Manager instance with Flashbots enabled
        transactions: List of transactions to include in the bundle
        token_addresses: List of token addresses to track for balance changes
        
    Returns:
        Dictionary with bundle simulation results
    """
    try:
        if not hasattr(web3_manager, 'flashbots_manager') or web3_manager.flashbots_manager is None:
            raise ValueError("Flashbots manager not available")
        
        # Target next block
        next_block = await web3_manager.w3.eth.block_number + 1
        
        # Create bundle
        bundle_id = await web3_manager.flashbots_manager.create_bundle(
            target_block=next_block,
            transactions=transactions,
            revert_on_fail=True
        )
        
        # Simulate bundle
        simulation = await web3_manager.flashbots_manager.simulate_bundle(bundle_id)
        
        # Calculate profit
        profit_result = await web3_manager.flashbots_manager.calculate_bundle_profit(
            bundle_id=bundle_id,
            token_addresses=token_addresses,
            account_to_check=web3_manager.wallet_address
        )
        
        # Validate bundle if balance validator is available
        validation_result = None
        if hasattr(web3_manager.flashbots_manager, 'balance_validator') and web3_manager.flashbots_manager.balance_validator is not None:
            validation_result = await web3_manager.flashbots_manager.balance_validator.validate_bundle_balance(
                bundle_id=bundle_id,
                token_addresses=token_addresses or [],
                account_to_check=web3_manager.wallet_address
            )
        
        logger.info(f"Bundle {bundle_id} created and simulated. Profit: {profit_result.get('net_profit_wei', 0)} wei")
        
        return {
            'success': True,
            'bundle_id': bundle_id,
            'simulation': simulation,
            'profit': profit_result,
            'validation': validation_result,
            'target_block': next_block
        }
        
    except Exception as e:
        logger.error(f"Failed to create and simulate bundle: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def optimize_and_submit_bundle(
    web3_manager: Web3Manager,
    bundle_id: str,
    min_profit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Optimize gas settings and submit a bundle if profitable.
    
    Args:
        web3_manager: Web3Manager instance with Flashbots enabled
        bundle_id: ID of the bundle to submit
        min_profit: Minimum profit required in wei
        
    Returns:
        Dictionary with submission results
    """
    try:
        if not hasattr(web3_manager, 'flashbots_manager') or web3_manager.flashbots_manager is None:
            raise ValueError("Flashbots manager not available")
        
        # Optimize gas settings
        gas_settings = await web3_manager.flashbots_manager.optimize_bundle_gas(
            bundle_id=bundle_id,
            max_priority_fee=int(2e9)  # 2 GWEI priority fee
        )
        
        # Validate and submit bundle
        result = await web3_manager.flashbots_manager.validate_and_submit_bundle(
            bundle_id=bundle_id,
            min_profit=min_profit
        )
        
        logger.info(f"Bundle {bundle_id} submission: {'success' if result.get('submit_result') else 'failed'}")
        
        return {
            'success': 'submit_result' in result and result['submit_result'] is not None,
            'gas_settings': gas_settings,
            'result': result
        }
        
    except Exception as e:
        logger.error(f"Failed to optimize and submit bundle: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# Command-line script for Flashbots integration testing
async def main():
    """Run Flashbots integration as a command-line script."""
    import argparse
    import json
    from pathlib import Path
    
    # Parse command line args
    parser = argparse.ArgumentParser(description='Test Flashbots RPC integration')
    parser.add_argument('--test-connection', action='store_true', help='Test Flashbots RPC connection')
    parser.add_argument('--output', type=str, help='Save test results to file')
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize Flashbots RPC integration
        logger.info("Initializing Flashbots RPC integration...")
        components = await setup_flashbots_rpc()
        
        # Test connection if requested
        if args.test_connection:
            logger.info("Testing Flashbots RPC connection...")
            test_result = await test_flashbots_connection(components=components)
            
            # Print results
            if test_result['success']:
                logger.info("Flashbots RPC connection test successful")
                logger.info(f"Stats: {json.dumps(test_result['stats'], indent=2)}")
            else:
                logger.error(f"Flashbots RPC connection test failed: {test_result['error']}")
            
            # Save results to file if requested
            if args.output:
                output_path = Path(args.output)
                with open(output_path, 'w') as f:
                    json.dump(test_result, f, indent=2)
                logger.info(f"Test results saved to {output_path}")
        
        logger.info("Flashbots RPC integration test completed")
        
    except Exception as e:
        logger.error(f"Error in Flashbots RPC integration test: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    asyncio.run(main())