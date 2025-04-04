"""
Base DEX Scanner MCP Integration

This module provides integration with the Base DEX Scanner MCP server.
It includes classes for scanning DEXes, finding pools, and detecting arbitrage opportunities.
"""

import asyncio
import json
import logging
import os
import aiohttp
import backoff
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
from decimal import Decimal

from eth_utils import to_checksum_address

from ..core.arbitrage.models import ArbitrageOpportunity, TokenAmount

logger = logging.getLogger(__name__)

# =====================================================================
# MOCK DATA CONFIGURATION
# =====================================================================
# IMPORTANT: This should ALWAYS be set to False in production environments!
# Only set to True for development and testing purposes.

# Check if we're in a production environment
IS_PRODUCTION = os.environ.get("ENVIRONMENT", "").lower() == "production"

# If we're in production, force USE_MOCK_DATA to False regardless of the environment variable
if IS_PRODUCTION:
    USE_MOCK_DATA = False
    if os.environ.get("USE_MOCK_DATA", "").lower() == "true":
        logger.critical("⚠️ CRITICAL: USE_MOCK_DATA was set to 'true' in a production environment!")
        logger.critical("⚠️ CRITICAL: This has been overridden to 'false' to prevent using mock data in production.")
        logger.critical("⚠️ CRITICAL: Please check your environment variables and deployment configuration.")
else:
    # In non-production environments, respect the environment variable
    USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "false").lower() == "true"

if USE_MOCK_DATA:
    logger.warning("⚠️⚠️⚠️ !!! USING MOCK DATA FOR TESTING PURPOSES ONLY !!! Set USE_MOCK_DATA=false to use real data ⚠️⚠️⚠️")


class BaseDexScannerMCP:
    """Client for the Base DEX Scanner MCP server."""

    def __init__(self, server_name: str = "base-dex-scanner"):
        """Initialize the Base DEX Scanner MCP client.

        Args:
            server_name: Name of the MCP server
        """
        self.server_name = server_name
        self._cache = {}
        self._cache_lock = asyncio.Lock()
        self._use_mock_data = USE_MOCK_DATA
        self._session = None
        self._api_key = os.environ.get("BASE_DEX_SCANNER_API_KEY", "")

    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool result
        """
        try:
            # Check if we should use mock data
            if self._use_mock_data:
                # =====================================================================
                # !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
                # =====================================================================
                logger.info("Using mock data for tool call: %s", tool_name)
                
                if tool_name == "scan_dexes":
                    return await self._mock_scan_dexes()
                elif tool_name == "get_dex_info":
                    return await self._mock_get_dex_info(arguments.get("dex_address"))
                elif tool_name == "get_factory_pools":
                    return await self._mock_get_factory_pools(arguments.get("factory_address"))
                elif tool_name == "check_contract":
                    return await self._mock_check_contract(arguments.get("contract_address"))
                elif tool_name == "get_recent_dexes":
                    return await self._mock_get_recent_dexes(
                        arguments.get("limit", 10),
                        arguments.get("days", 7)
                    )
                elif tool_name == "get_pool_price":
                    return await self._mock_get_pool_price(arguments.get("pool_address"))
                else:
                    logger.warning(f"Unknown mock tool: {tool_name}")
                    return None
            else:
                # =====================================================================
                # REAL API CALL - PRODUCTION CODE
                # =====================================================================
                try:
                    # Get MCP server URL from environment or use default
                    mcp_url = os.environ.get("BASE_DEX_SCANNER_MCP_URL", "http://localhost:9050")
                    api_endpoint = f"{mcp_url}/api/v1/{tool_name}"
                    
                    # Create session if it doesn't exist
                    if self._session is None:
                        self._session = aiohttp.ClientSession(
                            headers={
                                "Content-Type": "application/json",
                                "X-API-Key": self._api_key
                            }
                        )
                    
                    # Prepare request payload
                    payload = {
                        **arguments
                    }
                    
                    # Make the API call with retry logic
                    return await self._make_api_call_with_retry(api_endpoint, payload)
                    
                except Exception as e:
                    logger.exception(f"Error making API call to {tool_name}: {str(e)}")
                    return None
        except Exception as e:
            logger.exception(f"Error calling MCP tool {tool_name}: {str(e)}")
            return None

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=30
    )
    async def _make_api_call_with_retry(self, url: str, payload: Dict[str, Any]) -> Any:
        """Make an API call with retry logic.

        Args:
            url: API endpoint URL
            payload: Request payload

        Returns:
            API response
        """
        try:
            start_time = time.time()
            logger.info(f"Making API call to {url}")
            
            async with self._session.post(url, json=payload, timeout=30) as response:
                elapsed_time = time.time() - start_time
                logger.info(f"API call to {url} completed in {elapsed_time:.2f}s with status {response.status}")
                
                # Check if the request was successful
                if response.status == 200:
                    # Parse the response
                    result = await response.json()
                    try:
                        # Handle both dictionary with 'data' key and direct list/dict responses
                        if isinstance(result, dict) and "data" in result:
                            return result.get("data")
                        else:
                            return result
                    except Exception as e:
                        logger.error(f"Unexpected error in API call to {url}: {str(e)}")
                        return None
                elif response.status == 429:
                    # Rate limited, wait and retry
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    logger.warning(f"Rate limited. Retrying after {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    raise aiohttp.ClientError("Rate limited")
                else:
                    # Other error
                    error_text = await response.text()
                    logger.error(f"API call failed with status {response.status}: {error_text}")
                    return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"API call to {url} failed: {str(e)}. Retrying...")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in API call to {url}: {str(e)}")
            return None

    async def scan_dexes(self) -> List[Dict[str, Any]]:
        """Scan for DEXes on the Base blockchain.

        Returns:
            List of DEXes
        """
        try:
            async with self._cache_lock:
                if "dexes" in self._cache:
                    logger.info("Using cached DEXes")
                    return self._cache["dexes"]

            logger.info("Scanning for DEXes on Base blockchain...")
            dexes = await self._call_mcp_tool("scan_dexes", {})

            if dexes:
                async with self._cache_lock:
                    self._cache["dexes"] = dexes
                logger.info(f"Found {len(dexes)} DEXes")
            else:
                logger.warning("No DEXes found")
                dexes = []

            return dexes
        except Exception as e:
            logger.exception(f"Error scanning DEXes: {str(e)}")
            return []

    async def get_dex_info(self, dex_address: str) -> Optional[Dict[str, Any]]:
        """Get information about a DEX.

        Args:
            dex_address: Address of the DEX factory or router

        Returns:
            DEX information or None if not found
        """
        try:
            # Ensure address is checksummed
            dex_address = to_checksum_address(dex_address)

            async with self._cache_lock:
                cache_key = f"dex_info_{dex_address}"
                if cache_key in self._cache:
                    logger.info(f"Using cached DEX info for {dex_address}")
                    return self._cache[cache_key]

            logger.info(f"Getting DEX info for {dex_address}...")
            dex_info = await self._call_mcp_tool("get_dex_info", {"dex_address": dex_address})

            if dex_info:
                async with self._cache_lock:
                    self._cache[cache_key] = dex_info
                logger.info(f"Found DEX info for {dex_address}")
            else:
                logger.warning(f"No DEX info found for {dex_address}")

            return dex_info
        except Exception as e:
            logger.exception(f"Error getting DEX info: {str(e)}")
            return None

    async def get_factory_pools(self, factory_address: str) -> List[Dict[str, Any]]:
        """Get pools for a DEX factory.

        Args:
            factory_address: Address of the DEX factory

        Returns:
            List of pools
        """
        try:
            # Ensure address is checksummed
            factory_address = to_checksum_address(factory_address)

            async with self._cache_lock:
                cache_key = f"factory_pools_{factory_address}"
                if cache_key in self._cache:
                    logger.info(f"Using cached pools for factory {factory_address}")
                    return self._cache[cache_key]

            logger.info(f"Getting pools for factory {factory_address}...")
            pools = await self._call_mcp_tool("get_factory_pools", {"factory_address": factory_address})

            if pools:
                async with self._cache_lock:
                    self._cache[cache_key] = pools
                logger.info(f"Found {len(pools)} pools for factory {factory_address}")
            else:
                logger.warning(f"No pools found for factory {factory_address}")
                pools = []

            return pools
        except Exception as e:
            logger.exception(f"Error getting factory pools: {str(e)}")
            return []

    async def check_contract(self, contract_address: str) -> Optional[Dict[str, Any]]:
        """Check if a contract is a DEX component.

        Args:
            contract_address: Address of the contract to check

        Returns:
            Contract information or None if not a DEX component
        """
        try:
            # Ensure address is checksummed
            contract_address = to_checksum_address(contract_address)

            async with self._cache_lock:
                cache_key = f"contract_info_{contract_address}"
                if cache_key in self._cache:
                    logger.info(f"Using cached contract info for {contract_address}")
                    return self._cache[cache_key]

            logger.info(f"Checking contract {contract_address}...")
            contract_info = await self._call_mcp_tool("check_contract", {"contract_address": contract_address})

            if contract_info:
                async with self._cache_lock:
                    self._cache[cache_key] = contract_info
                logger.info(f"Found contract info for {contract_address}")
            else:
                logger.warning(f"No contract info found for {contract_address}")

            return contract_info
        except Exception as e:
            logger.exception(f"Error checking contract: {str(e)}")
            return None

    async def get_recent_dexes(self, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
        """Get recently discovered DEXes.

        Args:
            limit: Maximum number of DEXes to return
            days: Number of days to look back

        Returns:
            List of recently discovered DEXes
        """
        try:
            async with self._cache_lock:
                cache_key = f"recent_dexes_{limit}_{days}"
                if cache_key in self._cache:
                    logger.info(f"Using cached recent DEXes (limit={limit}, days={days})")
                    return self._cache[cache_key]

            logger.info(f"Getting recent DEXes (limit={limit}, days={days})...")
            dexes = await self._call_mcp_tool("get_recent_dexes", {"limit": limit, "days": days})

            if dexes:
                async with self._cache_lock:
                    self._cache[cache_key] = dexes
                logger.info(f"Found {len(dexes)} recent DEXes")
            else:
                logger.warning("No recent DEXes found")
                dexes = []

            return dexes
        except Exception as e:
            logger.exception(f"Error getting recent DEXes: {str(e)}")
            return []

    async def get_pool_price(self, pool_address: str) -> Optional[Dict[str, Any]]:
        """Get price information for a pool.

        Args:
            pool_address: Address of the pool

        Returns:
            Price information or None if not found
        """
        try:
            # Ensure address is checksummed
            pool_address = to_checksum_address(pool_address)

            async with self._cache_lock:
                cache_key = f"pool_price_{pool_address}"
                if cache_key in self._cache and (datetime.now() - self._cache[cache_key]["timestamp"]).total_seconds() < 60:
                    logger.info(f"Using cached pool price for {pool_address}")
                    return self._cache[cache_key]["data"]

            logger.info(f"Getting price for pool {pool_address}...")
            price_info = await self._call_mcp_tool("get_pool_price", {"pool_address": pool_address})

            if price_info:
                async with self._cache_lock:
                    self._cache[cache_key] = {
                        "data": price_info,
                        "timestamp": datetime.now()
                    }
                logger.info(f"Found price info for pool {pool_address}")
            else:
                logger.warning(f"No price info found for pool {pool_address}")

            return price_info
        except Exception as e:
            logger.exception(f"Error getting pool price: {str(e)}")
            return None

    # =====================================================================
    # !!! MOCK METHODS - FOR TESTING PURPOSES ONLY !!!
    # =====================================================================

    async def _mock_scan_dexes(self) -> List[Dict[str, Any]]:
        """Mock scan_dexes method.
        
        !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
        """
        logger.warning("!!! MOCK DATA: _mock_scan_dexes - FOR TESTING PURPOSES ONLY !!!")
        return [
            {
                "name": "BaseSwap",
                "factory_address": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
                "router_address": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",
                "type": "uniswap_v2",
                "version": "v2"
            },
            {
                "name": "Aerodrome",
                "factory_address": "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
                "router_address": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
                "type": "uniswap_v2",
                "version": "v2"
            },
            {
                "name": "SushiSwap",
                "factory_address": "0x71524B4f93c58fcbF659783284E38825e820E82c",
                "router_address": "0x6BDED42c6DA8FBf0d2bA55B2fa120C5e0c8D7891",
                "type": "uniswap_v2",
                "version": "v2"
            }
        ]

    async def _mock_get_dex_info(self, dex_address: str) -> Optional[Dict[str, Any]]:
        """Mock get_dex_info method.
        
        !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
        """
        logger.warning("!!! MOCK DATA: _mock_get_dex_info - FOR TESTING PURPOSES ONLY !!!")
        dexes = await self._mock_scan_dexes()
        for dex in dexes:
            if dex["factory_address"] == dex_address or dex["router_address"] == dex_address:
                return dex
        return None

    async def _mock_get_factory_pools(self, factory_address: str) -> List[Dict[str, Any]]:
        """Mock get_factory_pools method.
        
        !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
        """
        logger.warning("!!! MOCK DATA: _mock_get_factory_pools - FOR TESTING PURPOSES ONLY !!!")
        if factory_address == "0x33128a8fC17869897dcE68Ed026d694621f6FDfD":  # BaseSwap
            return [
                {
                    "address": "0x7E9DAB607D95C8336BF22E1Bd5a194B2bA262A2C",
                    "token0": {
                        "address": "0x4200000000000000000000000000000000000006",
                        "symbol": "WETH",
                        "decimals": 18
                    },
                    "token1": {
                        "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                        "symbol": "USDC",
                        "decimals": 6
                    },
                    "liquidity_usd": 5000000.0
                },
                {
                    "address": "0x9e5AAC1Ba1a2e6aEd6b32689DFcF62A509Ca96f3",
                    "token0": {
                        "address": "0x4200000000000000000000000000000000000006",
                        "symbol": "WETH",
                        "decimals": 18
                    },
                    "token1": {
                        "address": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
                        "symbol": "USDbC",
                        "decimals": 6
                    },
                    "liquidity_usd": 3000000.0
                }
            ]
        elif factory_address == "0x420DD381b31aEf6683db6B902084cB0FFECe40Da":  # Aerodrome
            return [
                {
                    "address": "0x2223F9FE624F69Da4D8256A7bCc9104FBA7F8f75",
                    "token0": {
                        "address": "0x4200000000000000000000000000000000000006",
                        "symbol": "WETH",
                        "decimals": 18
                    },
                    "token1": {
                        "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                        "symbol": "USDC",
                        "decimals": 6
                    },
                    "liquidity_usd": 4500000.0
                }
            ]
        elif factory_address == "0x71524B4f93c58fcbF659783284E38825e820E82c":  # SushiSwap
            return [
                {
                    "address": "0x9e5AAC1Ba1a2e6aEd6b32689DFcF62A509Ca96f3",
                    "token0": {
                        "address": "0x4200000000000000000000000000000000000006",
                        "symbol": "WETH",
                        "decimals": 18
                    },
                    "token1": {
                        "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                        "symbol": "USDC",
                        "decimals": 6
                    },
                    "liquidity_usd": 2000000.0
                }
            ]
        else:
            return []

    async def _mock_check_contract(self, contract_address: str) -> Optional[Dict[str, Any]]:
        """Mock check_contract method.
        
        !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
        """
        logger.warning("!!! MOCK DATA: _mock_check_contract - FOR TESTING PURPOSES ONLY !!!")
        if contract_address == "0x33128a8fC17869897dcE68Ed026d694621f6FDfD":
            return {
                "is_dex": True,
                "type": "factory",
                "dex_name": "BaseSwap",
                "version": "v2"
            }
        elif contract_address == "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86":
            return {
                "is_dex": True,
                "type": "router",
                "dex_name": "BaseSwap",
                "version": "v2"
            }
        elif contract_address == "0x7E9DAB607D95C8336BF22E1Bd5a194B2bA262A2C":
            return {
                "is_dex": True,
                "type": "pool",
                "dex_name": "BaseSwap",
                "version": "v2",
                "token0": "0x4200000000000000000000000000000000000006",
                "token1": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
            }
        else:
            return None

    async def _mock_get_recent_dexes(self, limit: int, days: int) -> List[Dict[str, Any]]:
        """Mock get_recent_dexes method.
        
        !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
        """
        logger.warning("!!! MOCK DATA: _mock_get_recent_dexes - FOR TESTING PURPOSES ONLY !!!")
        dexes = await self._mock_scan_dexes()
        return dexes[:limit]

    async def _mock_get_pool_price(self, pool_address: str) -> Dict[str, Any]:
        """Mock get_pool_price method.
        
        !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
        """
        logger.warning("!!! MOCK DATA: _mock_get_pool_price - FOR TESTING PURPOSES ONLY !!!")
        if pool_address == "0x7E9DAB607D95C8336BF22E1Bd5a194B2bA262A2C":  # WETH/USDC on BaseSwap
            return {"price": 3500.0}
        elif pool_address == "0x9e5AAC1Ba1a2e6aEd6b32689DFcF62A509Ca96f3":  # WETH/USDbC on BaseSwap
            return {"price": 3450.0}
        elif pool_address == "0x2223F9FE624F69Da4D8256A7bCc9104FBA7F8f75":  # WETH/USDC on Aerodrome
            return {"price": 3550.0}
        else:
            return {"price": 0.0}

    async def close(self):
        """Close the client and clean up resources."""
        logger.info("Closing BaseDexScannerMCP client")
        if self._session is not None:
            await self._session.close()
            self._session = None


class BaseDexScannerSource:
    """Source for DEX discovery using the Base DEX Scanner MCP server."""

    def __init__(self, server_name: str = "base-dex-scanner"):
        """Initialize the Base DEX Scanner source.

        Args:
            server_name: Name of the MCP server
        """
        self.server_name = server_name
        self.scanner = BaseDexScannerMCP(server_name=server_name)
        self._dexes = []
        self._pools = {}
        self._lock = asyncio.Lock()
        
        # Show warning if using mock data
        if USE_MOCK_DATA:
            logger.warning("!!! BaseDexScannerSource USING MOCK DATA FOR TESTING PURPOSES ONLY !!!")

    async def initialize(self) -> bool:
        """Initialize the source.

        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Fetch initial DEXes
            dexes = await self.scanner.scan_dexes()
            
            async with self._lock:
                self._dexes = dexes
            
            logger.info(f"Initialized Base DEX Scanner source with {len(dexes)} DEXes")
            return True
        except Exception as e:
            logger.exception(f"Error initializing Base DEX Scanner source: {str(e)}")
            return False

    async def fetch_dexes(self) -> List[Dict[str, Any]]:
        """Fetch DEXes from the scanner.

        Returns:
            List of DEXes
        """
        try:
            dexes = await self.scanner.scan_dexes()
            
            async with self._lock:
                self._dexes = dexes
            
            return dexes
        except Exception as e:
            logger.exception(f"Error fetching DEXes: {str(e)}")
            return []

    async def get_pools_for_dex(self, dex: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get pools for a DEX.

        Args:
            dex: DEX information

        Returns:
            List of pools
        """
        try:
            factory_address = dex.get("factory_address")
            if not factory_address:
                logger.warning(f"No factory address for DEX {dex.get('name', 'unknown')}")
                return []
            
            async with self._lock:
                if factory_address in self._pools:
                    logger.info(f"Using cached pools for DEX {dex.get('name', 'unknown')}")
                    return self._pools[factory_address]
            
            pools = await self.scanner.get_factory_pools(factory_address)
            
            async with self._lock:
                self._pools[factory_address] = pools
            
            return pools
        except Exception as e:
            logger.exception(f"Error getting pools for DEX: {str(e)}")
            return []

    async def detect_arbitrage_opportunities(self) -> List[ArbitrageOpportunity]:
        """Detect arbitrage opportunities.

        Returns:
            List of arbitrage opportunities
        """
        try:
            # Fetch DEXes if not already fetched
            if not self._dexes:
                await self.fetch_dexes()
            
            # Get pools for each DEX
            all_pools = {}
            for dex in self._dexes:
                dex_name = dex.get("name", "unknown")
                pools = await self.get_pools_for_dex(dex)
                all_pools[dex_name] = pools
            
            # Find arbitrage opportunities
            opportunities = []
            
            # For each token pair, check prices across different DEXes
            token_pairs = set()
            for dex_name, pools in all_pools.items():
                for pool in pools:
                    token0 = pool.get("token0", {}).get("symbol", "unknown")
                    token1 = pool.get("token1", {}).get("symbol", "unknown")
                    token_pairs.add(f"{token0}/{token1}")
            
            for token_pair in token_pairs:
                # Find pools for this token pair across different DEXes
                pair_pools = {}
                for dex_name, pools in all_pools.items():
                    for pool in pools:
                        token0 = pool.get("token0", {}).get("symbol", "unknown")
                        token1 = pool.get("token1", {}).get("symbol", "unknown")
                        if f"{token0}/{token1}" == token_pair or f"{token1}/{token0}" == token_pair:
                            pair_pools[dex_name] = pool
                
                # Check for price differences
                if len(pair_pools) >= 2:
                    # Find DEX with lowest price (best to buy from)
                    buy_dex = None
                    buy_price = float('inf')
                    
                    # Find DEX with highest price (best to sell to)
                    sell_dex = None
                    sell_price = 0
                    
                    if USE_MOCK_DATA:
                        logger.warning("!!! USING MOCK PRICE DATA FOR TESTING PURPOSES ONLY !!!")
                        logger.warning("!!! ARBITRAGE OPPORTUNITIES ARE NOT REAL !!!")
                    
                    for dex_name, pool in pair_pools.items():
                        # Get price from pool
                        price_info = await self.scanner.get_pool_price(pool.get("address"))
                        if not price_info:
                            continue
                            
                        price = price_info.get("price", 0)
                        if price <= 0:
                            continue
                            
                        if price < buy_price:
                            buy_price = price
                            buy_dex = dex_name
                            
                        if price > sell_price:
                            sell_price = price
                            sell_dex = dex_name
                    
                    # If we found a price difference
                    if buy_dex and sell_dex and buy_dex != sell_dex:
                        # Calculate profit
                        price_diff = sell_price - buy_price
                        price_diff_pct = price_diff / buy_price
                        
                        # Only consider significant price differences
                        if price_diff_pct >= 0.01:  # 1% or more
                            # Create opportunity
                            tokens = token_pair.split('/')
                            
                            # Get pool details
                            buy_pool = pair_pools[buy_dex]
                            sell_pool = pair_pools[sell_dex]
                            
                            # Calculate profit
                            # Assume 1 ETH trade size for calculation
                            trade_amount_eth = 1.0
                            gross_profit_usd = trade_amount_eth * price_diff
                            
                            # Estimate gas cost
                            gas_cost_eth = 0.01  # Estimate
                            gas_price_gwei = 30  # Estimate
                            gas_cost_usd = gas_cost_eth * buy_price
                            
                            # Calculate net profit
                            net_profit_usd = gross_profit_usd - gas_cost_usd
                            
                            # Only consider profitable opportunities
                            if net_profit_usd > 0:
                                # Create opportunity object
                                opp = ArbitrageOpportunity(
                                    id=f"{tokens[0]}_{tokens[1]}_{buy_dex}_{sell_dex}",
                                    token_in=tokens[0],
                                    token_out=tokens[1],
                                    input_amount=TokenAmount(
                                        amount=trade_amount_eth,
                                        decimals=18
                                    ),
                                    output_amount=TokenAmount(
                                        amount=trade_amount_eth * (1 + price_diff_pct),
                                        decimals=18
                                    ),
                                    path=[
                                        {"dex": buy_dex, "pool": buy_pool.get("address")},
                                        {"dex": sell_dex, "pool": sell_pool.get("address")}
                                    ],
                                    gas_estimate=gas_cost_eth,
                                    gas_price_gwei=gas_price_gwei,
                                    input_price_usd=buy_price,
                                    output_price_usd=sell_price,
                                    gross_profit_usd=gross_profit_usd,
                                    gas_cost_usd=gas_cost_usd,
                                    net_profit_usd=net_profit_usd,
                                    is_profitable=True,
                                    timestamp=datetime.now().timestamp()
                                )
                                
                                opportunities.append(opp)
            
            # Sort opportunities by profit
            opportunities.sort(key=lambda x: x.net_profit_usd, reverse=True)
            
            logger.info(f"Found {len(opportunities)} arbitrage opportunities")
            return opportunities
        except Exception as e:
            logger.exception(f"Error detecting arbitrage opportunities: {str(e)}")
            return []

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Close the scanner's session
            await self.scanner.close()
            logger.info("Cleaned up BaseDexScannerSource resources")
        except Exception as e:
            logger.exception(f"Error during cleanup: {str(e)}")
