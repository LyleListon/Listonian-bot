"""
Flashbots Flash Loan Example

This example demonstrates how to use the combined Flashbots Flash Loan strategy
to execute an arbitrage opportunity with flash loans and MEV protection.
"""

import asyncio
import logging
import os
from decimal import Decimal

from arbitrage_bot.core.web3.providers.eth_client import EthClient
from arbitrage_bot.core.web3.flashbots.provider import FlashbotsProvider
from arbitrage_bot.core.web3.flashbots.simulator import BundleSimulator
from arbitrage_bot.core.arbitrage.execution.strategies.flashbots_flash_loan_strategy import FlashbotsFlashLoanStrategy
from arbitrage_bot.core.arbitrage.interfaces import ArbitrageOpportunity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main example function to demonstrate Flashbots Flash Loan integration."""
    try:
        # Get private key from environment variable
        private_key = os.environ.get('PRIVATE_KEY')
        if not private_key:
            logger.error("PRIVATE_KEY environment variable not set")
            return
        
        # Remove '0x' prefix if present
        if private_key.startswith('0x'):
            private_key = private_key[2:]
        
        # Get Ethereum node URL
        eth_rpc_url = os.environ.get('ETH_RPC_URL', 'https://goerli.infura.io/v3/YOUR_INFURA_KEY')
        
        # Create Web3 client
        web3_client = EthClient(provider_url=eth_rpc_url)
        await web3_client.connect()
        
        # Create Flashbots provider
        flashbots_provider = FlashbotsProvider(
            web3_client=web3_client,
            signing_key=private_key,
            config={
                "network": "goerli",  # Use Ethereum mainnet
                "blocks_into_future": 2,
                "relay_timeout": 30
            }
        )
        await flashbots_provider.initialize()
        
        # Create strategy
        strategy = FlashbotsFlashLoanStrategy(
            web3_client=web3_client,
            flashbots_provider=flashbots_provider,
            config={
                "flash_loan": {
                    "slippage_tolerance": "0.005",  # 0.5%
                    "profit_threshold_multiplier": "1.5",
                    "gas_buffer": "1.2"
                },
                "flashbots": {
                    "max_wait_blocks": 5
                }
            }
        )
        await strategy.initialize()
        
        # Create a sample opportunity (in a real scenario, this would come from a scanner)
        opportunity = create_sample_opportunity()
        
        # Check if strategy is applicable
        is_applicable = await strategy.is_applicable(opportunity)
        logger.info(f"Strategy applicable: {is_applicable}")
        
        if not is_applicable:
            logger.warning("Strategy not applicable to this opportunity")
            return
        
        # Execute the opportunity
        result = await strategy.execute(
            opportunity=opportunity,
            execution_params={
                "min_profit_threshold": 0.001,  # 0.001 ETH
                "blocks_into_future": 2
            }
        )
        
        # Log the result
        if result.status.name == "EXECUTED":
            logger.info(f"Execution successful!")
            logger.info(f"Transaction hash: {result.transaction_hash}")
            logger.info(f"Profit: {result.profit_amount} {result.profit_token}")
            logger.info(f"Gas used: {result.gas_used}, Gas price: {result.gas_price}")
        else:
            logger.warning(f"Execution failed: {result.error_message}")
        
    except Exception as e:
        logger.error(f"Error in example: {e}", exc_info=True)
    
    finally:
        # Clean up resources
        if 'web3_client' in locals():
            await web3_client.close()
        
        if 'flashbots_provider' in locals():
            await flashbots_provider.close()
        
        if 'strategy' in locals():
            await strategy.close()


def create_sample_opportunity() -> ArbitrageOpportunity:
    """
    Create a sample arbitrage opportunity for demonstration.
    
    In a real application, opportunities would be discovered by
    a scanner that monitors prices across multiple DEXes.
    
    Returns:
        A sample arbitrage opportunity
    """
    # WETH address on Ethereum (checksummed)
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    
    # Create an opportunity with 10 ETH input and 10.1 ETH output (1% profit)
    opportunity = ArbitrageOpportunity(
        start_token=weth_address,
        end_token=weth_address,
        start_amount=Decimal("10"),
        end_amount=Decimal("10.1"),
        profit_amount=Decimal("0.1"),
        required_amount=Decimal("10"),
        path=[weth_address, "0x6B175474E89094C44Da98b954EedeAC495271d0F", weth_address],  # WETH -> DAI -> WETH
        dexes=["uniswap_v2", "sushiswap"],
        execution_data={
            "calldata": "0x",  # Simplified for example
            "gas_estimate": 500000
        }
    )
    
    return opportunity


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())