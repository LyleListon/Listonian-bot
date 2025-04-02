#!/usr/bin/env python3
"""
Base DEX Scanner MCP Integration Example

This script demonstrates how to use the Base DEX Scanner MCP server with the Listonian Arbitrage Bot.
It shows how to discover DEXes, find arbitrage opportunities, and execute trades.
"""

import asyncio
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from arbitrage_bot.integration.base_dex_scanner_mcp import BaseDexScannerMCP, BaseDexScannerSource, USE_MOCK_DATA
from arbitrage_bot.integration.base_dex_trading_executor import BaseDexTradingExecutor, USE_MOCK_TRADING

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/base_dex_scanner_example.log"),
    ],
)
logger = logging.getLogger(__name__)

# Show warning if using mock data
if USE_MOCK_DATA:
    logger.warning("!!! EXAMPLE USING MOCK DATA/TRADING - FOR TESTING PURPOSES ONLY !!!")
    logger.warning("!!! RESULTS ARE NOT REAL AND SHOULD NOT BE USED FOR TRADING !!!")


async def discover_dexes():
    """Discover DEXes using the Base DEX Scanner MCP server."""
    logger.info("Discovering DEXes using Base DEX Scanner MCP server...")
    
    if USE_MOCK_DATA:
        logger.warning("!!! MOCK DEX DISCOVERY - FOR TESTING PURPOSES ONLY !!!")
    
    # Create the scanner
    scanner = BaseDexScannerMCP()
    
    # Scan for DEXes
    dexes = await scanner.scan_dexes()
    logger.info(f"Found {len(dexes)} DEXes")
    
    # Print DEX details
    for i, dex in enumerate(dexes, 1):
        logger.info(f"DEX {i}:")
        logger.info(f"  Name: {dex.get('name', 'Unknown')}")
        logger.info(f"  Factory: {dex.get('factory_address', 'Unknown')}")
        logger.info(f"  Router: {dex.get('router_address', 'Unknown')}")
        logger.info(f"  Type: {dex.get('type', 'Unknown')}")
        logger.info(f"  Version: {dex.get('version', 'Unknown')}")
    
    return dexes


async def find_pools(scanner: BaseDexScannerMCP, dexes: List[Dict[str, Any]]):
    """Find pools for each DEX."""
    logger.info("Finding pools for each DEX...")
    
    if USE_MOCK_DATA:
        logger.warning("!!! MOCK POOL DISCOVERY - FOR TESTING PURPOSES ONLY !!!")
    
    total_pools = 0
    dex_pools = {}
    
    for dex in dexes:
        factory_address = dex.get('factory_address')
        if not factory_address:
            continue
        
        logger.info(f"Getting pools for {dex.get('name', 'Unknown')}...")
        pools = await scanner.get_factory_pools(factory_address)
        
        dex_pools[dex.get('name', 'Unknown')] = pools
        total_pools += len(pools)
        
        logger.info(f"Found {len(pools)} pools for {dex.get('name', 'Unknown')}")
        
        # Print details for first 5 pools
        for i, pool in enumerate(pools[:5], 1):
            logger.info(f"  Pool {i}:")
            logger.info(f"    Address: {pool.get('address', 'Unknown')}")
            logger.info(f"    Token0: {pool.get('token0', {}).get('symbol', 'Unknown')}")
            logger.info(f"    Token1: {pool.get('token1', {}).get('symbol', 'Unknown')}")
            logger.info(f"    Liquidity: ${pool.get('liquidity_usd', 0):,.2f}")
    
    logger.info(f"Total pools found: {total_pools}")
    return dex_pools


async def find_arbitrage_opportunities(source: BaseDexScannerSource):
    """Find arbitrage opportunities."""
    logger.info("Finding arbitrage opportunities...")
    
    if USE_MOCK_DATA:
        logger.warning("!!! MOCK ARBITRAGE DETECTION - FOR TESTING PURPOSES ONLY !!!")
        logger.warning("!!! OPPORTUNITIES ARE NOT REAL AND SHOULD NOT BE USED FOR TRADING !!!")
    
    # Detect arbitrage opportunities
    opportunities = await source.detect_arbitrage_opportunities()
    
    logger.info(f"Found {len(opportunities)} arbitrage opportunities")
    
    # Filter profitable opportunities
    profitable_opportunities = [
        opp for opp in opportunities
        if hasattr(opp, 'is_profitable') and opp.is_profitable and Decimal(str(opp.net_profit_usd)) >= Decimal('1.0')
    ]
    
    logger.info(f"Found {len(profitable_opportunities)} profitable arbitrage opportunities")
    
    # Print details for first 5 profitable opportunities
    for i, opp in enumerate(profitable_opportunities[:5], 1):
        logger.info(f"Opportunity {i}:")
        logger.info(f"  ID: {getattr(opp, 'id', 'Unknown')}")
        logger.info(f"  Token Pair: {getattr(opp, 'token_in', 'Unknown')}/{getattr(opp, 'token_out', 'Unknown')}")
        logger.info(f"  Buy DEX: {opp.path[0]['dex'] if hasattr(opp, 'path') and len(opp.path) > 0 else 'Unknown'}")
        logger.info(f"  Sell DEX: {opp.path[1]['dex'] if hasattr(opp, 'path') and len(opp.path) > 1 else 'Unknown'}")
        logger.info(f"  Net Profit (USD): ${getattr(opp, 'net_profit_usd', 0):,.2f}")
    
    return profitable_opportunities


async def execute_trades(executor: BaseDexTradingExecutor, opportunities: List[Any]):
    """Execute trades for profitable opportunities."""
    logger.info("Executing trades for profitable opportunities...")
    
    if USE_MOCK_TRADING:
        logger.warning("!!! MOCK TRADE EXECUTION - FOR TESTING PURPOSES ONLY !!!")
        logger.warning("!!! TRADES ARE NOT REAL AND NO ACTUAL TRANSACTIONS ARE BEING SENT !!!")
    
    # Start the executor
    await executor.start()
    
    # Wait for a while to let the executor process opportunities
    logger.info("Waiting for trades to execute...")
    await asyncio.sleep(60)
    
    # Get statistics
    stats = await executor.get_stats()
    logger.info("Trading Statistics:")
    logger.info(f"  Opportunities Found: {stats['opportunities_found']}")
    logger.info(f"  Trades Executed: {stats['trades_executed']}")
    logger.info(f"  Total Profit: ${stats['total_profit_usd']:,.2f}")
    logger.info(f"  Failed Trades: {stats['failed_trades']}")
    logger.info(f"  Runtime: {stats.get('runtime_formatted', 'N/A')}")
    
    # Stop the executor
    await executor.stop()


async def main():
    """Main entry point for the script."""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Show warning if using mock data
        if USE_MOCK_DATA:
            logger.warning("=" * 80)
            logger.warning("!!! THIS EXAMPLE USES MOCK DATA FOR TESTING PURPOSES ONLY !!!")
            logger.warning("!!! RESULTS ARE NOT REAL AND SHOULD NOT BE USED FOR TRADING !!!")
            logger.warning("=" * 80)
        
        # Step 1: Discover DEXes
        dexes = await discover_dexes()
        
        # Step 2: Create scanner and source
        scanner = BaseDexScannerMCP()
        source = BaseDexScannerSource()
        
        # Step 3: Initialize source
        await source.initialize()
        
        # Step 4: Find pools for each DEX
        dex_pools = await find_pools(scanner, dexes)
        
        # Step 5: Find arbitrage opportunities
        opportunities = await find_arbitrage_opportunities(source)
        
        # Step 6: Execute trades (if private key is provided)
        private_key = os.environ.get("PRIVATE_KEY")
        if private_key:
            # Create the executor
            executor = BaseDexTradingExecutor(
                private_key=private_key,
                min_profit_usd=1.0,  # Set minimum profit to $1.0
            )
            
            # Initialize the executor
            await executor.initialize()
            
            # Execute trades
            await execute_trades(executor, opportunities)
        else:
            logger.warning("PRIVATE_KEY environment variable not set. Skipping trade execution.")
        
        # Step 7: Clean up
        await source.cleanup()
        
        logger.info("Example completed successfully")
        
        # Final warning if using mock data
        if USE_MOCK_DATA:
            logger.warning("=" * 80)
            logger.warning("!!! REMEMBER: THIS EXAMPLE USED MOCK DATA FOR TESTING PURPOSES ONLY !!!")
            logger.warning("!!! RESULTS ARE NOT REAL AND SHOULD NOT BE USED FOR TRADING !!!")
            logger.warning("=" * 80)
        
    except Exception as e:
        logger.exception(f"Error running example: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())