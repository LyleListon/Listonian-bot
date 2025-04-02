#!/usr/bin/env python3
"""
Base DEX Scanner MCP Server with HTTP API

This script runs the Base DEX Scanner MCP server with an HTTP API, which provides tools for scanning DEXes,
finding pools, and detecting arbitrage opportunities on the Base blockchain.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiohttp
from aiohttp import web
from web3 import Web3
from eth_utils import to_checksum_address

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/base_dex_scanner_mcp.log"),
    ],
)
logger = logging.getLogger(__name__)

# =====================================================================
# MOCK DATA CONFIGURATION
# =====================================================================

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!!                                                                                              !!!
# !!!                                   ⚠️ WARNING ⚠️                                              !!!
# !!!                                                                                              !!!
# !!!                          MOCK DATA MODE IS ENABLED                                           !!!
# !!!                                                                                              !!!
# !!!      THIS IS FOR TESTING PURPOSES ONLY - DO NOT USE IN PRODUCTION                            !!!
# !!!                                                                                              !!!
# !!!      ALL DATA RETURNED BY THIS SERVER IS FAKE AND NOT REAL BLOCKCHAIN DATA                   !!!
# !!!                                                                                              !!!
# !!!      SET THIS TO FALSE BEFORE DEPLOYING TO PRODUCTION                                        !!!
# !!!                                                                                              !!!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# IMPORTANT: This is set to "false" by default for production use. Set to "true" only for testing.
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "false").lower() == "true"
  # Default to FALSE for production
# MCP Server configuration
MCP_SERVER_PORT = 9050  # Use port 9050 as required
MCP_SERVER_HOST = os.environ.get("MCP_SERVER_HOST", "localhost")

if USE_MOCK_DATA:
    logger.warning("⚠️⚠️⚠️ !!! USING MOCK DATA FOR TESTING PURPOSES ONLY !!! ⚠️⚠️⚠️")
    logger.warning("⚠️⚠️⚠️ !!! ALL DATA IS FAKE - NOT REAL BLOCKCHAIN DATA !!! ⚠️⚠️⚠️")
    logger.warning("⚠️⚠️⚠️ !!! Set USE_MOCK_DATA=false to use real data !!! ⚠️⚠️⚠️")


class BaseDexScannerMCPServer:
    """Base DEX Scanner MCP Server."""

    def __init__(self):
        """Initialize the server."""
        self.config = self._load_config()
        self.dexes = []
        self.pools = {}
        self.running = False
        self.scan_interval = int(self.config.get("SCAN_INTERVAL_MINUTES", 60))
        self.rpc_url = self.config.get("BASE_RPC_URL", "https://mainnet.base.org")
        self.api_key = self.config.get("BASESCAN_API_KEY", "")
        self.db_uri = self.config.get("DATABASE_URI", "")
        
        # Show warning if using mock data
        if USE_MOCK_DATA:
            logger.warning("!!! BaseDexScannerMCPServer USING MOCK DATA FOR TESTING PURPOSES ONLY !!!")

    def _load_config(self) -> Dict[str, str]:
        """Load configuration from environment variables."""
        return {
            "BASE_RPC_URL": os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
            "BASESCAN_API_KEY": os.environ.get("BASESCAN_API_KEY", ""),
            "DATABASE_URI": os.environ.get("DATABASE_URI", ""),
            "SCAN_INTERVAL_MINUTES": os.environ.get("SCAN_INTERVAL_MINUTES", "60"),
        }

    async def start(self):
        """Start the server."""
        logger.info("Starting Base DEX Scanner MCP server...")
        self.running = True
        
        # Load initial data
        await self._load_initial_data()
        
        # Start background tasks
        asyncio.create_task(self._scan_loop())
        
        logger.info("Base DEX Scanner MCP server started")

    async def stop(self):
        """Stop the server."""
        logger.info("Stopping Base DEX Scanner MCP server...")
        self.running = False
        logger.info("Base DEX Scanner MCP server stopped")

    async def _load_initial_data(self):
        """Load initial data."""
        logger.info("Loading initial data...")
        
        if USE_MOCK_DATA:
            # =====================================================================
            # !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
            # =====================================================================
            logger.warning("!!! LOADING MOCK DATA - FOR TESTING PURPOSES ONLY !!!")
            
            # Load DEXes
            self.dexes = [
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
            
            # Load pools
            self.pools = {
                "0x33128a8fC17869897dcE68Ed026d694621f6FDfD": [  # BaseSwap
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
                ],
                "0x420DD381b31aEf6683db6B902084cB0FFECe40Da": [  # Aerodrome
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
                ],
                "0x71524B4f93c58fcbF659783284E38825e820E82c": []  # SushiSwap (no pools)
            }
        else:
            # =====================================================================
            # REAL DATA LOADING - PRODUCTION CODE
            # =====================================================================
            logger.info("Loading real data from the Base blockchain...")
            
            try:
                # Initialize Web3 connection
                web3 = Web3(Web3.HTTPProvider(self.rpc_url))
                if not web3.is_connected():
                    logger.error(f"Failed to connect to Base RPC at {self.rpc_url}")
                    raise Exception(f"Failed to connect to Base RPC at {self.rpc_url}")
                
                logger.info(f"Connected to Base blockchain at {self.rpc_url}")
                
                # Load known DEXes
                self.dexes = [
                    {
                        "name": "BaseSwap",
                        "factory_address": to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD"),
                        "router_address": to_checksum_address("0x327Df1E6de05895d2ab08513aaDD9313Fe505d86"),
                        "type": "uniswap_v2",
                        "version": "v2"
                    },
                    {
                        "name": "Aerodrome",
                        "factory_address": to_checksum_address("0x420DD381b31aEf6683db6B902084cB0FFECe40Da"),
                        "router_address": to_checksum_address("0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"),
                        "type": "uniswap_v2",
                        "version": "v2"
                    },
                    {
                        "name": "SushiSwap",
                        "factory_address": to_checksum_address("0x71524B4f93c58fcbF659783284E38825e820E82c"),
                        "router_address": to_checksum_address("0x6BDED42c6DA8FBf0d2bA55B2fa120C5e0c8D7891"),
                        "type": "uniswap_v2",
                        "version": "v2"
                    }
                ]
                
                # Initialize pools dictionary
                self.pools = {}
                
                # Load pools for each DEX
                for dex in self.dexes:
                    factory_address = dex["factory_address"]
                    dex_name = dex["name"]
                    
                    logger.info(f"Loading pools for {dex_name}...")
                    
                    # Load factory contract ABI
                    factory_abi = self._load_abi(f"abi/{dex_name.lower()}_factory.json")
                    if not factory_abi:
                        logger.warning(f"Factory ABI not found for {dex_name}, using default ABI")
                        factory_abi = self._load_abi("abi/dex_factory.json")
                    
                    if not factory_abi:
                        logger.error(f"No factory ABI available for {dex_name}")
                        continue
                    
                    # Create factory contract
                    factory_contract = web3.eth.contract(address=factory_address, abi=factory_abi)
                    
                    # Get pool count
                    try:
                        # Different DEXes have different methods to get pool count
                        if hasattr(factory_contract.functions, 'allPairsLength'):
                            pool_count = factory_contract.functions.allPairsLength().call()
                        elif hasattr(factory_contract.functions, 'allPoolsLength'):
                            pool_count = factory_contract.functions.allPoolsLength().call()
                        else:
                            logger.warning(f"Unknown factory interface for {dex_name}")
                            pool_count = 0
                        
                        logger.info(f"Found {pool_count} pools for {dex_name}")
                        
                        # For now, just initialize an empty list
                        # In a real implementation, we would fetch pool details
                        self.pools[factory_address] = []
                        
                    except Exception as e:
                        logger.exception(f"Error getting pool count for {dex_name}: {str(e)}")
                        self.pools[factory_address] = []
                
                logger.info(f"Loaded {len(self.dexes)} DEXes with real blockchain data")
                
            except Exception as e:
                logger.exception(f"Error loading real data: {str(e)}")
                self.dexes = []
                self.pools = {}
        
        logger.info(f"Loaded {len(self.dexes)} DEXes and {sum(len(pools) for pools in self.pools.values())} pools")

    async def _scan_loop(self):
        """Scan for DEXes and pools periodically."""
        while self.running:
            try:
                logger.info(f"Scanning for DEXes and pools (interval: {self.scan_interval} minutes)...")
                
                if USE_MOCK_DATA:
                    # =====================================================================
                    # !!! MOCK SCANNING - FOR TESTING PURPOSES ONLY !!!
                    # =====================================================================
                    logger.warning("!!! MOCK SCANNING - FOR TESTING PURPOSES ONLY !!!")
                    
                    # In a real implementation, this would scan the blockchain for DEXes and pools
                    # For now, we'll just use the initial data
                    
                    logger.info(f"Mock scan completed. Found {len(self.dexes)} DEXes and {sum(len(pools) for pools in self.pools.values())} pools")
                else:
                    # =====================================================================
                    # REAL SCANNING - PRODUCTION CODE
                    # =====================================================================
                    logger.info("Scanning the Base blockchain for new DEXes and pools...")
                    
                    try:
                        # Initialize Web3 connection
                        web3 = Web3(Web3.HTTPProvider(self.rpc_url))
                        if not web3.is_connected():
                            logger.error(f"Failed to connect to Base RPC at {self.rpc_url}")
                            raise Exception(f"Failed to connect to Base RPC at {self.rpc_url}")
                        
                        # Update pools for each DEX
                        for dex in self.dexes:
                            factory_address = dex["factory_address"]
                            dex_name = dex["name"]
                            
                            logger.info(f"Updating pools for {dex_name}...")
                            
                            # Load factory contract ABI
                            factory_abi = self._load_abi(f"abi/{dex_name.lower()}_factory.json")
                            if not factory_abi:
                                logger.warning(f"Factory ABI not found for {dex_name}, using default ABI")
                                factory_abi = self._load_abi("abi/dex_factory.json")
                            
                            if not factory_abi:
                                logger.error(f"No factory ABI available for {dex_name}")
                                continue
                            
                            # Create factory contract
                            factory_contract = web3.eth.contract(address=factory_address, abi=factory_abi)
                            
                            # Get pool count
                            try:
                                # Different DEXes have different methods to get pool count
                                if hasattr(factory_contract.functions, 'allPairsLength'):
                                    pool_count = factory_contract.functions.allPairsLength().call()
                                elif hasattr(factory_contract.functions, 'allPoolsLength'):
                                    pool_count = factory_contract.functions.allPoolsLength().call()
                                else:
                                    logger.warning(f"Unknown factory interface for {dex_name}")
                                    pool_count = 0
                                
                                logger.info(f"Found {pool_count} pools for {dex_name}")
                                
                                # For now, just update the pool count
                                # In a real implementation, we would fetch new pool details
                                if factory_address not in self.pools:
                                    self.pools[factory_address] = []
                                
                            except Exception as e:
                                logger.exception(f"Error getting pool count for {dex_name}: {str(e)}")
                        
                        logger.info(f"Scan completed. Found {len(self.dexes)} DEXes and {sum(len(pools) for pools in self.pools.values())} pools")
                        
                    except Exception as e:
                        logger.exception(f"Error scanning blockchain: {str(e)}")
                
                # Sleep until next scan
                await asyncio.sleep(self.scan_interval * 60)
            except Exception as e:
                logger.exception(f"Error in scan loop: {str(e)}")
                await asyncio.sleep(60)  # Sleep for 1 minute on error

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Handle a tool call."""
        logger.info(f"Handling tool call: {tool_name}")
        
        if USE_MOCK_DATA:
            logger.warning(f"!!! USING MOCK DATA FOR TOOL CALL: {tool_name} - FOR TESTING PURPOSES ONLY !!!")
        
        if tool_name == "scan_dexes":
            return await self.scan_dexes()
        elif tool_name == "get_dex_info":
            return await self.get_dex_info(arguments.get("dex_address"))
        elif tool_name == "get_factory_pools":
            return await self.get_factory_pools(arguments.get("factory_address"))
        elif tool_name == "check_contract":
            return await self.check_contract(arguments.get("contract_address"))
        elif tool_name == "get_recent_dexes":
            return await self.get_recent_dexes(
                arguments.get("limit", 10),
                arguments.get("days", 7)
            )
        elif tool_name == "get_pool_price":
            return await self.get_pool_price(arguments.get("pool_address"))
        else:
            logger.warning(f"Unknown tool: {tool_name}")
            return None

    async def scan_dexes(self) -> List[Dict[str, Any]]:
        """Scan for DEXes on the Base blockchain."""
        logger.info("Scanning for DEXes...")
        return self.dexes

    async def get_dex_info(self, dex_address: str) -> Optional[Dict[str, Any]]:
        """Get information about a DEX."""
        logger.info(f"Getting DEX info for {dex_address}...")
        
        for dex in self.dexes:
            if dex["factory_address"] == dex_address or dex["router_address"] == dex_address:
                return dex
        
        return None

    async def get_factory_pools(self, factory_address: str) -> List[Dict[str, Any]]:
        """Get pools for a DEX factory."""
        logger.info(f"Getting pools for factory {factory_address}...")
        
        if factory_address in self.pools:
            return self.pools[factory_address]
        
        return []

    async def check_contract(self, contract_address: str) -> Optional[Dict[str, Any]]:
        """Check if a contract is a DEX component."""
        logger.info(f"Checking contract {contract_address}...")
        
        # Check if it's a factory
        for dex in self.dexes:
            if dex["factory_address"] == contract_address:
                return {
                    "is_dex": True,
                    "type": "factory",
                    "dex_name": dex["name"],
                    "version": dex["version"]
                }
            
            # Check if it's a router
            if dex["router_address"] == contract_address:
                return {
                    "is_dex": True,
                    "type": "router",
                    "dex_name": dex["name"],
                    "version": dex["version"]
                }
        
        # Check if it's a pool
        for factory_address, pools in self.pools.items():
            for pool in pools:
                if pool["address"] == contract_address:
                    # Find the DEX name
                    dex_name = "Unknown"
                    for dex in self.dexes:
                        if dex["factory_address"] == factory_address:
                            dex_name = dex["name"]
                            break
                    
                    return {
                        "is_dex": True,
                        "type": "pool",
                        "dex_name": dex_name,
                        "version": "v2",
                        "token0": pool["token0"]["address"],
                        "token1": pool["token1"]["address"]
                    }
        
        return None

    async def get_recent_dexes(self, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
        """Get recently discovered DEXes."""
        logger.info(f"Getting recent DEXes (limit={limit}, days={days})...")
        
        # In a real implementation, this would filter DEXes by discovery date
        # For now, just return all DEXes up to the limit
        return self.dexes[:limit]

    async def get_pool_price(self, pool_address: str) -> Dict[str, Any]:
        """Get price information for a pool."""
        logger.info(f"Getting price for pool {pool_address}...")
        
        if USE_MOCK_DATA:
            # =====================================================================
            # !!! MOCK PRICE DATA - FOR TESTING PURPOSES ONLY !!!
            # =====================================================================
            logger.warning("!!! MOCK POOL PRICE DATA - FOR TESTING PURPOSES ONLY !!!")
            
            # Return mock price data based on the pool address
            if pool_address == "0x7E9DAB607D95C8336BF22E1Bd5a194B2bA262A2C":  # WETH/USDC on BaseSwap
                return {"price": 3500.0}
            elif pool_address == "0x9e5AAC1Ba1a2e6aEd6b32689DFcF62A509Ca96f3":  # WETH/USDbC on BaseSwap
                return {"price": 3450.0}
            elif pool_address == "0x2223F9FE624F69Da4D8256A7bCc9104FBA7F8f75":  # WETH/USDC on Aerodrome
                return {"price": 3550.0}
            else:
                return {"price": 0.0}
        else:
            # =====================================================================
            # REAL PRICE DATA - PRODUCTION CODE
            # =====================================================================
            logger.info(f"Fetching real price data for pool {pool_address}...")
            
            try:
                # Initialize Web3 connection
                web3 = Web3(Web3.HTTPProvider(self.rpc_url))
                if not web3.is_connected():
                    logger.error(f"Failed to connect to Base RPC at {self.rpc_url}")
                    return {"price": 0.0}
                
                # Find the pool in our data
                pool_info = None
                dex_name = "Unknown"
                
                for factory_address, pools in self.pools.items():
                    for pool in pools:
                        if pool.get("address") == pool_address:
                            pool_info = pool
                            # Find the DEX name
                            for dex in self.dexes:
                                if dex.get("factory_address") == factory_address:
                                    dex_name = dex.get("name")
                                    break
                            break
                    if pool_info:
                        break
                
                if not pool_info:
                    logger.warning(f"Pool {pool_address} not found in our data")
                    return {"price": 0.0}
                
                # Load pool ABI
                pool_abi = self._load_abi(f"abi/{dex_name.lower()}_pair.json")
                if not pool_abi:
                    logger.warning(f"Pool ABI not found for {dex_name}, using default ABI")
                    pool_abi = self._load_abi("abi/dex_pair.json")
                
                if not pool_abi:
                    logger.error(f"No pool ABI available for {dex_name}")
                    return {"price": 0.0}
                
                # Create pool contract
                pool_contract = web3.eth.contract(address=pool_address, abi=pool_abi)
                
                # Get reserves
                reserves = pool_contract.functions.getReserves().call()
                reserve0 = reserves[0]
                reserve1 = reserves[1]
                
                # Calculate price
                token0_decimals = pool_info.get("token0", {}).get("decimals", 18)
                token1_decimals = pool_info.get("token1", {}).get("decimals", 18)
                
                price = (reserve1 / 10**token1_decimals) / (reserve0 / 10**token0_decimals)
                
                logger.info(f"Calculated price for pool {pool_address}: {price}")
                return {"price": price}
                
            except Exception as e:
                logger.exception(f"Error getting real price data: {str(e)}")
                return {"price": 0.0}
    
    def _load_abi(self, abi_path: str) -> Optional[List[Dict[str, Any]]]:
        """Load ABI from a JSON file."""
        try:
            with open(abi_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading ABI from {abi_path}: {str(e)}")
            return None


class MCPHttpServer:
    """HTTP server for the MCP API."""

    def __init__(self, mcp_server: BaseDexScannerMCPServer, host: str = MCP_SERVER_HOST, port: int = MCP_SERVER_PORT):
        """Initialize the HTTP server."""
        self.mcp_server = mcp_server
        self.host = host
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Set up the API routes."""
        self.app.router.add_post('/api/v1/{tool_name}', self.handle_api_request)
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/health', self.health_check)
        
    async def handle_api_request(self, request: web.Request) -> web.Response:
        """Handle an API request."""
        tool_name = request.match_info['tool_name']
        
        try:
            # Parse the request body
            body = await request.json()
            
            # Handle the tool call
            result = await self.mcp_server.handle_tool_call(tool_name, body)
            
            # Return the result
            return web.json_response(result)
        except Exception as e:
            logger.exception(f"Error handling API request: {str(e)}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_root(self, request: web.Request) -> web.Response:
        """Handle a request to the root path."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Base DEX Scanner MCP Server</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                h1 {{ color: #333; }}
                .warning {{ background-color: #ffcccc; border: 2px solid #ff0000; padding: 10px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>Base DEX Scanner MCP Server</h1>
            <p>This server provides tools for scanning DEXes, finding pools, and detecting arbitrage opportunities on the Base blockchain.</p>
            
            {('<div class="warning"><h2>⚠️ WARNING: MOCK DATA MODE IS ENABLED ⚠️</h2><p>This server is running with mock data for testing purposes only. All data returned is fake and not real blockchain data.</p></div>' if USE_MOCK_DATA else '')}
            
            <h2>Available Endpoints:</h2>
            <ul>
                <li><code>/api/v1/{'{tool_name}'}</code> - API endpoints for tool calls (POST)</li>
                <li><code>/health</code> - Health check endpoint (GET)</li>
            </ul>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Handle a health check request."""
        return web.json_response({"status": "ok"})
    
    async def start(self):
        """Start the HTTP server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"HTTP server started at http://{self.host}:{self.port}")
        return runner
    

async def main():
    """Main entry point for the script."""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Create the MCP server
        mcp_server = BaseDexScannerMCPServer()
        
        # Start the MCP server
        await mcp_server.start()
        
        # Create and start the HTTP server
        http_server = MCPHttpServer(mcp_server)
        runner = await http_server.start()
        
        logger.info(f"Base DEX Scanner MCP server with HTTP API is running at http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}")
        
        # Run forever
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Stopping server...")
        await mcp_server.stop()
        await runner.cleanup()
    except Exception as e:
        logger.exception(f"Error running server: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())