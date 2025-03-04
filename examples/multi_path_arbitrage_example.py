"""
Multi-Path Arbitrage Example

This example demonstrates how to use the multi-path arbitrage system to
discover, optimize, and execute complex arbitrage opportunities across
multiple DEXs with maximized profits.
"""

import asyncio
import logging
import os
from decimal import Decimal

from arbitrage_bot.core.web3.providers.eth_client import EthClient
from arbitrage_bot.core.web3.flashbots.provider import FlashbotsProvider
from arbitrage_bot.core.dex.manager import DexManager
from arbitrage_bot.core.price.fetcher import PriceFetcher
from arbitrage_bot.core.finance.flash_loans.factory import FlashLoanFactory
from arbitrage_bot.core.arbitrage.path.graph_explorer import NetworkXGraphExplorer
from arbitrage_bot.core.arbitrage.path.path_finder import MultiPathFinder
from arbitrage_bot.core.arbitrage.path.path_optimizer import MonteCarloPathOptimizer
from arbitrage_bot.core.arbitrage.execution.strategies.multi_path_strategy import MultiPathStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main example function to demonstrate multi-path arbitrage."""
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
        eth_rpc_url = os.environ.get('ETH_RPC_URL', 'https://mainnet.infura.io/v3/YOUR_INFURA_KEY')
        
        # Create Web3 client
        web3_client = EthClient(provider_url=eth_rpc_url, private_key=private_key)
        await web3_client.connect()
        
        # Create DEX manager
        dex_manager = DexManager(web3_client=web3_client)
        await dex_manager.initialize()
        
        # Create price fetcher
        price_fetcher = PriceFetcher(web3_client=web3_client)
        await price_fetcher.initialize()
        
        # Create flash loan factory
        flash_loan_factory = FlashLoanFactory(
            web3_client=web3_client,
            config={
                "preferred_providers": ["balancer", "aave"],
                "max_fee_rate": "0.005"  # 0.5%
            }
        )
        await flash_loan_factory.initialize()
        
        # Create Flashbots provider
        flashbots_provider = FlashbotsProvider(
            web3_client=web3_client,
            signing_key=private_key,
            config={
                "network": "mainnet",
                "blocks_into_future": 2,
                "relay_timeout": 30
            }
        )
        await flashbots_provider.initialize()
        
        # Create graph explorer
        graph_explorer = NetworkXGraphExplorer(
            dex_manager=dex_manager,
            price_fetcher=price_fetcher,
            config={
                "graph_ttl": 60,  # 60 seconds
                "max_pools_per_dex": 1000,
                "min_liquidity": "10000",  # $10,000 minimum liquidity
                "include_stable_tokens": True,
                "include_wrapped_tokens": True,
                "max_path_length": 4
            }
        )
        await graph_explorer.initialize()
        
        # Create path finder
        path_finder = MultiPathFinder(
            graph_explorer=graph_explorer,
            dex_manager=dex_manager,
            price_fetcher=price_fetcher,
            config={
                "max_path_length": 4,
                "max_paths": 50,
                "min_profit_threshold": "0.001",  # Minimum profit in token units
                "min_profit_percentage": "0.001",  # 0.1% minimum profit
                "gas_price_buffer": "1.1",
                "slippage_tolerance": "0.005"  # 0.5%
            }
        )
        await path_finder.initialize()
        
        # Create multi-path strategy
        strategy = MultiPathStrategy(
            web3_client=web3_client,
            flashbots_provider=flashbots_provider,
            flash_loan_factory=flash_loan_factory,
            config={
                "slippage_tolerance": "0.005",  # 0.5%
                "profit_threshold_multiplier": "1.5",
                "gas_buffer": "1.2",
                "max_wait_blocks": 5,
                "use_flash_loans": True
            }
        )
        await strategy.initialize()
        
        # Define starting token (WETH on Ethereum)
        weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        
        # Find multi-path opportunities
        logger.info(f"Finding multi-path opportunities starting from WETH...")
        opportunities = await path_finder.find_opportunities(
            start_token=weth_address,
            max_opportunities=5,
            filters={
                "min_profit_percentage": 0.002  # 0.2% minimum profit
            }
        )
        
        if not opportunities:
            logger.info("No profitable opportunities found")
            return
        
        logger.info(f"Found {len(opportunities)} profitable opportunities")
        
        # Log the opportunities
        for i, opportunity in enumerate(opportunities):
            logger.info(f"Opportunity {i+1}:")
            logger.info(f"  Paths: {len(opportunity.paths)}")
            logger.info(f"  Required amount: {opportunity.required_amount}")
            logger.info(f"  Expected profit: {opportunity.expected_profit}")
            logger.info(f"  Profit percentage: {opportunity.profit_percentage:.4f}%")
            logger.info(f"  Confidence level: {opportunity.confidence_level:.2f}")
            
            # Log path details
            for j, (path, allocation) in enumerate(zip(opportunity.paths, opportunity.allocations)):
                logger.info(f"  Path {j+1}:")
                logger.info(f"    Tokens: {' -> '.join(path.tokens)}")
                logger.info(f"    DEXes: {', '.join(path.dexes)}")
                logger.info(f"    Allocation: {allocation}")
                logger.info(f"    Expected yield: {path.path_yield:.4f}")
        
        # Select the best opportunity
        best_opportunity = opportunities[0]
        logger.info(f"Selected best opportunity with {len(best_opportunity.paths)} paths")
        
        # Check if strategy is applicable
        is_applicable = await strategy.is_applicable(best_opportunity)
        logger.info(f"Strategy applicable: {is_applicable}")
        
        if not is_applicable:
            logger.warning("Strategy not applicable to this opportunity")
            return
        
        # Execute the opportunity (simulation only for this example)
        logger.info("Simulating execution (not actually executing)...")
        
        # Uncomment the following to actually execute the opportunity
        """
        result = await strategy.execute(
            opportunity=best_opportunity,
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
        """
        
    except Exception as e:
        logger.error(f"Error in example: {e}", exc_info=True)
    
    finally:
        # Clean up resources
        logger.info("Cleaning up resources...")
        
        if 'strategy' in locals():
            await strategy.close()
        
        if 'path_finder' in locals():
            await path_finder.close()
        
        if 'graph_explorer' in locals():
            await graph_explorer.close()
        
        if 'flashbots_provider' in locals():
            await flashbots_provider.close()
        
        if 'flash_loan_factory' in locals():
            await flash_loan_factory.close()
        
        if 'price_fetcher' in locals():
            await price_fetcher.close()
        
        if 'dex_manager' in locals():
            await dex_manager.close()
        
        if 'web3_client' in locals():
            await web3_client.close()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())