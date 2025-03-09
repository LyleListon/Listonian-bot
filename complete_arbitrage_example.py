"""
Complete Arbitrage Example

This example demonstrates:
- Flash loan execution
- Flashbots integration
- MEV protection
- Multi-path arbitrage
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, List
from eth_typing import ChecksumAddress

from arbitrage_bot.utils.config_loader import load_config
from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.core.web3.balance_validator import create_balance_validator
from arbitrage_bot.core.dex.dex_manager import create_dex_manager
from arbitrage_bot.core.dex.path_finder import create_path_finder
from arbitrage_bot.core.unified_flash_loan_manager import create_unified_flash_loan_manager
from arbitrage_bot.integration.flashbots_integration import setup_flashbots_rpc
from arbitrage_bot.integration.mev_protection import create_mev_protection_optimizer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_token_addresses(config: Dict[str, Any]) -> List[ChecksumAddress]:
    """Get unique token addresses from config."""
    return list(config['tokens'].values())

async def main():
    try:
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded")

        # Initialize Web3 manager
        web3_manager = await create_web3_manager(
            provider_url=config['provider_url'],
            private_key=config.get('private_key'),
            chain_id=config['chain_id'],
            config=config
        )
        logger.info("Web3 manager initialized")

        # Set up Flashbots
        flashbots_result = await setup_flashbots_rpc(
            web3_manager=web3_manager,
            config=config
        )

        if not flashbots_result['success']:
            raise RuntimeError(f"Failed to set up Flashbots: {flashbots_result}")

        flashbots_provider = flashbots_result['provider']
        logger.info("Flashbots integration set up")

        # Initialize balance validator
        balance_validator = await create_balance_validator(
            web3_manager=web3_manager,
            config=config
        )
        logger.info("Balance validator initialized")

        # Initialize DEX manager
        dex_manager = await create_dex_manager(
            web3_manager=web3_manager,
            config=config
        )
        logger.info("DEX manager initialized")

        # Initialize path finder
        path_finder = await create_path_finder(
            web3_manager=web3_manager,
            dex_manager=dex_manager,
            config=config
        )
        logger.info("Path finder initialized")

        # Initialize flash loan manager
        flash_loan_manager = await create_unified_flash_loan_manager(
            web3_manager=web3_manager,
            dex_manager=dex_manager,
            balance_validator=balance_validator,
            flashbots_provider=flashbots_provider,
            config=config
        )
        logger.info("Flash loan manager initialized")

        # Initialize MEV protection
        mev_protection = await create_mev_protection_optimizer(
            web3_manager=web3_manager,
            flashbots_provider=flashbots_provider,
            config=config
        )
        logger.info("MEV protection initialized")

        # Example: Find arbitrage paths
        weth_address = config['tokens']['WETH']
        token_addresses = get_token_addresses(config)

        paths = await path_finder.find_paths(
            start_token=weth_address,
            max_hops=3,
            token_addresses=token_addresses
        )
        logger.info(f"Found {len(paths)} potential arbitrage paths")

        # Example: Analyze first path
        if paths:
            path = paths[0]
            amount_in = web3_manager.w3.to_wei(0.1, 'ether')  # 0.1 ETH

            analysis = await path_finder.analyze_path(
                path=path,
                amount_in=amount_in
            )

            if analysis['profitable']:
                logger.info(
                    f"Found profitable path with {analysis['profit']} wei profit"
                )

                # Validate flash loan
                valid = await flash_loan_manager.validate_flash_loan(
                    token_address=weth_address,
                    amount=amount_in,
                    expected_profit=analysis['profit']
                )

                if valid:
                    # Create transaction
                    tx = {
                        'to': flash_loan_manager.balancer_vault,
                        'value': 0,
                        'gas': analysis['gas_cost'],
                        'nonce': await web3_manager.w3.eth.get_transaction_count(
                            web3_manager.wallet_address
                        )
                    }

                    # Check for MEV attacks
                    mev_check = await mev_protection.check_for_mev_attacks(tx)
                    if mev_check['safe']:
                        # Optimize transaction
                        tx = await mev_protection.optimize_transaction(tx)

                        # Execute flash loan
                        result = await flash_loan_manager.execute_flash_loan(
                            token_address=weth_address,
                            amount=amount_in,
                            target_contract=web3_manager.wallet_address,
                            callback_data=b''
                        )

                        if result['success']:
                            logger.info(
                                f"Flash loan executed: {result['tx_hash']}"
                            )
                        else:
                            logger.error(
                                f"Flash loan failed: {result.get('error')}"
                            )
                    else:
                        logger.warning(
                            f"MEV attack detected: {mev_check['warnings']}"
                        )
                else:
                    logger.warning("Flash loan validation failed")
            else:
                logger.info("No profitable paths found")
        else:
            logger.info("No arbitrage paths found")

    except Exception as e:
        logger.error(f"Error in arbitrage example: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main())
