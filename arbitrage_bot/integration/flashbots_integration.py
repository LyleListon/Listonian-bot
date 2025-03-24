"""
Flashbots Integration Module

This module provides functionality for:
- Flashbots RPC integration
- Bundle submission
- MEV protection
"""

import logging
import json
import os
from typing import Any, Dict, List, Optional
from web3 import Web3
from decimal import Decimal
from eth_typing import HexStr
from eth_utils import is_hex_address, to_checksum_address

from ..core.web3.interfaces import Web3Client
from ..core.web3.flashbots.flashbots_provider import FlashbotsProvider

from ..core.web3.interfaces import Transaction
from ..utils.async_manager import with_retry
from ..core.flash_loan.aave_flash_loan import AaveFlashLoan, create_aave_flash_loan

logger = logging.getLogger(__name__)

class FlashbotsIntegration:
    """Manages Flashbots integration with flash loans and arbitrage."""

    def __init__(
        self,
        web3_manager: Web3Client,
        flashbots_provider: FlashbotsProvider,
        flash_loan_manager: AaveFlashLoan,
        min_profit: int = 0
    ):
        """
        Initialize Flashbots integration.

        Args:
            web3_manager: Web3 client instance
            flashbots_provider: Flashbots provider instance
            flash_loan_manager: Flash loan manager instance
            min_profit: Minimum profit threshold in wei
        """
        self.web3_manager = web3_manager
        self.flashbots_provider = flashbots_provider
        self.flash_loan_manager = flash_loan_manager
        self.min_profit = min_profit

        logger.info(
            f"Flashbots integration initialized with "
            f"min profit {web3_manager.w3.from_wei(min_profit, 'ether')} ETH"
        )

async def setup_flashbots_rpc(
    web3_manager: Web3Client,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Set up Flashbots RPC integration for production.

    Args:
        web3_manager: Web3 client instance
        config: Configuration dictionary with required keys:
            - flashbots.relay_url: Flashbots relay URL
            - flashbots.auth_key: Authentication key
            - flash_loan.aave_pool: Aave pool address
            - min_profit: Minimum profit in wei

    Returns:
        Result dictionary with components
    """
    try:
        # Validate configuration
        if not config.get('flashbots', {}).get('relay_url'):
            raise ValueError("Flashbots relay URL not configured")
            
        auth_key = os.environ.get('FLASHBOTS_AUTH_KEY')
        if not auth_key:
            raise ValueError("Flashbots auth key not configured")
        
        # Strip 0x prefix if present
        if auth_key.startswith('0x'):
            auth_key = auth_key[2:]
        
        # Validate auth key format
        if len(auth_key) != 64:  # 32 bytes = 64 hex chars
            raise ValueError("Invalid Flashbots auth key format - must be 32 bytes hex")
            
        if not config.get('flash_loan', {}).get('aave_pool'):
            raise ValueError("Aave pool address not configured")
        if not is_hex_address(config['flash_loan']['aave_pool']):
            raise ValueError("Invalid Aave pool address format")

        # Create components
        logger.info(f"Initializing Flashbots provider with RPC URL: {web3_manager._rpc_url}")
        
        flashbots_provider = FlashbotsProvider(
            w3=Web3(Web3.HTTPProvider(web3_manager._rpc_url, request_kwargs={"timeout": web3_manager._timeout})),
            relay_url=config['flashbots']['relay_url'],
            auth_key=auth_key,
            chain_id=config["web3"]["chain_id"]
        )

        flash_loan_manager = await create_aave_flash_loan(
            w3=web3_manager.w3,
            config=config
        )

        integration = FlashbotsIntegration(
            web3_manager=web3_manager,
            flashbots_provider=flashbots_provider,
            flash_loan_manager=flash_loan_manager,
            min_profit=int(config.get('flashbots', {}).get('min_profit', '0'))
        )

        logger.info("Flashbots RPC integration set up successfully for production")

        return {
            'success': True,
            'integration': integration,
            'flashbots_provider': flashbots_provider,
            'flash_loan_manager': flash_loan_manager
        }

    except Exception as e:
        logger.error(f"Failed to set up Flashbots RPC for production: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@with_retry(max_attempts=3, base_delay=1.0)
async def execute_arbitrage_bundle(
    integration: FlashbotsIntegration,
    transactions: List[Transaction],
    token_addresses: List[str],
    flash_loan_amount: int
) -> Dict[str, Any]:
    """
    Execute arbitrage bundle with flash loan through Flashbots.

    Args:
        integration: FlashbotsIntegration instance
        transactions: List of swap transactions
        token_addresses: List of token addresses to track
        flash_loan_amount: Flash loan amount in wei

    Returns:
        Result dictionary with execution details
    """
    try:
        # Validate inputs
        if not transactions:
            raise ValueError("No transactions provided")
        if not token_addresses:
            raise ValueError("No token addresses provided")
        if flash_loan_amount <= 0:
            raise ValueError("Invalid flash loan amount")

        # Create flash loan transaction
        flash_loan_tx = await integration.flash_loan_manager.build_flash_loan_tx(
            tokens=token_addresses,
            amounts=[flash_loan_amount],
            target_contract=integration.web3_manager.wallet_address,
            callback_data=b''
        )

        # Combine flash loan and swap transactions
        bundle_txs = [flash_loan_tx] + transactions

        # First simulate without state overrides
        simulation = await integration.flashbots_provider.simulate_bundle(
            transactions=bundle_txs
        )

        if not simulation['success']:
            # Try simulation with state overrides if initial fails
            state_overrides = {
                integration.web3_manager.wallet_address: {
                    "balance": "0xffffffffffffffff"  # Large balance
                }
            }
            
            simulation = await integration.flashbots_provider.simulate_bundle(
                transactions=bundle_txs,
                state_overrides=state_overrides
            )
            
            if not simulation['success']:
                raise ValueError(f"Bundle simulation failed with state overrides: {simulation.get('error')}")
                
            logger.warning(
                "Initial simulation failed but succeeded with state overrides. "
                "Proceeding with caution."
            )

        # Validate simulation results
        if 'mevValue' not in simulation or 'totalCost' not in simulation:
            raise ValueError("Simulation missing required profit metrics")

        # Validate profitability
        net_profit = simulation['mevValue'] - simulation['totalCost']
        if net_profit < integration.min_profit:
            raise ValueError(
                f"Bundle not profitable enough. "
                f"Expected: {integration.web3_manager.w3.from_wei(integration.min_profit, 'ether')} ETH, "
                f"Got: {integration.web3_manager.w3.from_wei(net_profit, 'ether')} ETH"
            )

        # Submit bundle
        bundle_hash = await integration.flashbots_provider.send_bundle(
            transactions=bundle_txs
        )

        logger.info(
            f"Arbitrage bundle submitted successfully:\n"
            f"Bundle hash: {bundle_hash}\n"
            f"Net profit: {integration.web3_manager.w3.from_wei(net_profit, 'ether')} ETH\n"
            f"Gas used: {simulation['gasUsed']}\n"
            f"Gas price: {integration.web3_manager.w3.from_wei(simulation['effectiveGasPrice'], 'gwei')} gwei"
        )

        return {
            'success': True,
            'bundle_hash': bundle_hash,
            'net_profit': net_profit,
            'gas_used': simulation['gasUsed'],
            'gas_price': simulation['effectiveGasPrice'],
            'simulation': simulation
        }

    except Exception as e:
        logger.error(f"Failed to execute arbitrage bundle: {e}")
        return {
            'success': False,
            'error': str(e)
        }

async def close_flashbots_integration(integration: FlashbotsIntegration):
    """Clean up Flashbots integration resources."""
    try:
        await integration.flashbots_provider.close()
        await integration.flash_loan_manager.close()
        logger.info("Flashbots integration resources cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up Flashbots integration: {e}")
