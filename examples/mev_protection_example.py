"""
MEV Protection Example

This script demonstrates how to use the MEV protection mechanisms
to protect arbitrage transactions from front-running and sandwich attacks.
"""

import asyncio
import json
import logging
from decimal import Decimal
from pathlib import Path

from web3 import Web3
from eth_utils import to_checksum_address

from arbitrage_bot.core.web3.web3_manager import Web3Manager
from arbitrage_bot.core.flashbots.flashbots_provider import FlashbotsProvider, create_flashbots_provider
from arbitrage_bot.core.flashbots.bundle import BundleManager
from arbitrage_bot.core.flashbots.simulation import SimulationManager
from arbitrage_bot.integration.mev_protection_integration import (
    setup_mev_protection,
    MEVProtectionIntegration
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Token addresses (example)
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

async def load_config():
    """Load configuration from files."""
    try:
        # Load main config
        config_path = Path("configs/config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Load MEV protection config
        mev_config_path = Path("configs/mev_protection_config.json")
        with open(mev_config_path, "r") as f:
            mev_config = json.load(f)
        
        # Merge configs
        config.update(mev_config)
        
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise

async def setup_components(config):
    """Set up required components."""
    try:
        # Create Web3 manager
        web3_manager = Web3Manager(
            rpc_url=config["web3"]["rpc_url"],
            private_key=config["web3"]["private_key"],
            chain_id=config["web3"]["chain_id"]
        )
        await web3_manager.initialize()
        
        # Create Flashbots provider
        flashbots_provider = await create_flashbots_provider(
            web3=web3_manager.w3,
            config=config["flashbots"]
        )
        
        # Create bundle manager
        bundle_manager = BundleManager(
            flashbots_manager=flashbots_provider,
            min_profit=Decimal(str(config["flashbots"]["min_profit"])),
            max_gas_price=Decimal(str(config["flashbots"]["max_gas_price"])),
            max_priority_fee=Decimal(str(config["flashbots"]["max_priority_fee"]))
        )
        
        # Create simulation manager
        simulation_manager = SimulationManager(
            flashbots_manager=flashbots_provider,
            bundle_manager=bundle_manager
        )
        
        # Set up MEV protection
        mev_protection_result = await setup_mev_protection(
            web3_manager=web3_manager,
            flashbots_provider=flashbots_provider,
            bundle_manager=bundle_manager,
            simulation_manager=simulation_manager,
            config=config
        )
        
        if not mev_protection_result["success"]:
            raise RuntimeError(f"Failed to set up MEV protection: {mev_protection_result.get('error')}")
        
        mev_protection = mev_protection_result["integration"]
        
        return {
            "web3_manager": web3_manager,
            "flashbots_provider": flashbots_provider,
            "bundle_manager": bundle_manager,
            "simulation_manager": simulation_manager,
            "mev_protection": mev_protection
        }
    except Exception as e:
        logger.error(f"Error setting up components: {e}")
        raise

async def create_example_transactions(web3_manager):
    """Create example transactions for demonstration."""
    # This is a simplified example - in a real implementation,
    # you would create actual swap transactions
    
    # Example: Simple token transfer
    tx1 = {
        "to": WETH_ADDRESS,
        "data": web3_manager.w3.eth.contract(
            address=WETH_ADDRESS,
            abi=[{
                "constant": False,
                "inputs": [
                    {"name": "dst", "type": "address"},
                    {"name": "wad", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function"
            }]
        ).encodeABI(
            fn_name="transfer",
            args=[web3_manager.wallet_address, web3_manager.w3.to_wei(0.1, "ether")]
        ),
        "value": 0
    }
    
    return [tx1]

async def demonstrate_mev_protection():
    """Demonstrate MEV protection functionality."""
    try:
        # Load config
        config = await load_config()
        
        # Set up components
        components = await setup_components(config)
        web3_manager = components["web3_manager"]
        mev_protection = components["mev_protection"]
        
        logger.info("Components initialized successfully")
        
        # Create example transactions
        transactions = await create_example_transactions(web3_manager)
        
        # Token addresses to monitor
        token_addresses = [WETH_ADDRESS, USDC_ADDRESS]
        
        # 1. Demonstrate MEV attack detection
        logger.info("Demonstrating MEV attack detection...")
        detection_result = await mev_protection.mev_protection.detect_potential_mev_attacks(
            token_addresses=[to_checksum_address(addr) for addr in token_addresses]
        )
        
        logger.info(f"MEV detection result: {detection_result}")
        
        # 2. Demonstrate slippage adjustment
        logger.info("Demonstrating slippage adjustment...")
        adjusted_slippage = await mev_protection.mev_protection.adjust_slippage_for_mev_protection(
            base_slippage=Decimal("0.005"),
            mev_detection_result=detection_result
        )
        
        logger.info(f"Adjusted slippage: {adjusted_slippage:.2%}")
        
        # 3. Demonstrate backrun protection decision
        logger.info("Demonstrating backrun protection decision...")
        transaction_value = Decimal("0.1")  # 0.1 ETH
        need_backrun = await mev_protection.mev_protection.should_add_backrun_protection(
            token_addresses=[to_checksum_address(addr) for addr in token_addresses],
            transaction_value=transaction_value
        )
        
        logger.info(f"Need backrun protection: {need_backrun}")
        
        # 4. Demonstrate bundle gas optimization
        logger.info("Demonstrating bundle gas optimization...")
        
        # Create a sample bundle
        bundle = {
            "transactions": transactions,
            "target_block": await web3_manager.w3.eth.block_number + 1,
            "gas_price": 20000000000,  # 20 gwei
            "priority_fee": 1000000000,  # 1 gwei
            "total_gas": 500000,
            "bundle_cost": 0.01
        }
        
        # Get current base fee
        base_fee = await components["flashbots_provider"].get_gas_price()
        
        # Optimize bundle gas
        optimized_bundle = await mev_protection.mev_protection.optimize_bundle_gas_for_mev_protection(
            bundle=bundle,
            base_fee=base_fee,
            mev_risk_level=detection_result["risk_level"]
        )
        
        logger.info(f"Original gas price: {bundle['gas_price'] / 1e9} gwei")
        logger.info(f"Original priority fee: {bundle['priority_fee'] / 1e9} gwei")
        logger.info(f"Optimized gas price: {optimized_bundle['gas_price'] / 1e9} gwei")
        logger.info(f"Optimized priority fee: {optimized_bundle['priority_fee'] / 1e9} gwei")
        
        # 5. Demonstrate protected bundle execution
        logger.info("Demonstrating protected bundle execution...")
        
        # Note: In a real implementation, you would execute the bundle
        # For this example, we'll just simulate the process
        
        logger.info("MEV protection demonstration completed")
        
        # Clean up resources
        await web3_manager.close()
        await components["flashbots_provider"].close()
        
    except Exception as e:
        logger.error(f"Error in MEV protection demonstration: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(demonstrate_mev_protection())
    except KeyboardInterrupt:
        logger.info("Demonstration interrupted by user")
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")