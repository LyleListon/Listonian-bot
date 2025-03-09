"""Shared test fixtures."""

import os
import json
import pytest
import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, Generator
from pathlib import Path
from unittest.mock import MagicMock, patch
from web3 import Web3

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

pytestmark = pytest.mark.asyncio

@pytest.fixture(scope="function")
def event_loop():
    """Create an event loop for each test function."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    if loop.is_running():
        loop.stop()
    pending = asyncio.all_tasks(loop)
    if pending:
        loop.run_until_complete(asyncio.gather(*pending))
    loop.close()
    asyncio.set_event_loop(None)

@pytest.fixture(scope="session")
def config() -> Dict[str, Any]:
    """Load test configuration."""
    with open("tests/data/test_config.json", "r") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Get test data directory."""
    data_dir = Path("tests/data")
    data_dir.mkdir(exist_ok=True)
    return data_dir

@pytest.fixture(scope="session")
async def temp_dir(test_data_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary directory for test data."""
    import uuid
    temp_path = test_data_dir / str(uuid.uuid4())
    temp_path.mkdir(exist_ok=True)
    yield temp_path
    # Cleanup with error handling
    if temp_path.exists():
        for file in temp_path.glob("*"):
            try:
                file.unlink()
            except Exception as e:
                logger.error(f"Error deleting file {file}: {e}")
        try:
            temp_path.rmdir()
        except Exception as e:
            logger.error(f"Error removing directory {temp_path}: {e}")

def handle_get_pair(args: list, config: Dict[str, Any]) -> str:
    """Handle getPair contract call."""
    if len(args) < 3:
        return "0x0000000000000000000000000000000000000000"
    
    token0, token1, stable = args[0], args[1], args[2]
    target_tokens = {token0.lower(), token1.lower()}
    
    dexes = config.get("dexes", {})
    aerodrome = dexes.get("aerodrome", {})
    pools = aerodrome.get("pools", {})
    
    for pool_key, pool_data in pools.items():
        key_tokens = set(pool_key.lower().split("/"))
        if key_tokens == target_tokens:
            pool_type = "stable" if stable else "volatile"
            pool = pool_data.get(pool_type)
            logger.debug(f"Found {pool_type} pool: {pool}")
            return pool if pool else "0x0000000000000000000000000000000000000000"
    
    return "0x0000000000000000000000000000000000000000"

def handle_get_pool(args: list, config: Dict[str, Any]) -> str:
    """Handle getPool contract call."""
    if len(args) < 3:
        return "0x0000000000000000000000000000000000000000"
    
    token0, token1, fee = args[0], args[1], args[2]
    target_tokens = {token0.lower(), token1.lower()}
    
    dexes = config.get("dexes", {})
    aerodrome_v3 = dexes.get("aerodrome_v3", {})
    pools = aerodrome_v3.get("pools", {})
    
    for pool_key, pool_data in pools.items():
        key_tokens = set(pool_key.lower().split("/"))
        if key_tokens == target_tokens:
            fee_key = f"fee_{fee}"
            pool = pool_data.get(fee_key)
            logger.debug(f"Found pool with fee {fee}: {pool}")
            return pool if pool else "0x0000000000000000000000000000000000000000"
    
    return "0x0000000000000000000000000000000000000000"

def handle_fee(args: list, config: Dict[str, Any]) -> Decimal:
    """Handle fee contract call."""
    if not args or not isinstance(args[0], str):
        logger.debug("Invalid args for fee call")
        return Decimal("500") / Decimal("1000000")  # Default 500 bps = 0.05%
    
    pool_address = args[0].lower()
    logger.debug(f"Checking fee for pool: {pool_address}")
    
    # Check V2 pools
    dexes = config.get("dexes", {})
    aerodrome = dexes.get("aerodrome", {})
    v2_pools = aerodrome.get("pools", {})
    
    for pool_key, pools in v2_pools.items():
        stable_addr = pools["stable"].lower()
        volatile_addr = pools["volatile"].lower()
        
        if pool_address == stable_addr:
            fee = (Decimal("100") / Decimal("1000000")).quantize(Decimal("0.000001"))  # 100 bps = 0.01%
            logger.debug(f"Found V2 stable pool {stable_addr}, fee: {fee}")
            return fee
        if pool_address == volatile_addr:
            fee = (Decimal("500") / Decimal("1000000")).quantize(Decimal("0.000001"))  # 500 bps = 0.05%
            logger.debug(f"Found V2 volatile pool {volatile_addr}, fee: {fee}")
            return fee
    
    # Check V3 pools
    aerodrome_v3 = dexes.get("aerodrome_v3", {})
    v3_pools = aerodrome_v3.get("pools", {})
    
    for pool_key, pools in v3_pools.items():
        for fee_key, addr in pools.items():
            addr_lower = addr.lower()
            if pool_address == addr_lower:
                fee_bps = int(fee_key.split("_")[1])
                fee = (Decimal(str(fee_bps)) / Decimal("1000000")).quantize(Decimal("0.000001"))
                logger.debug(f"Found V3 pool {addr_lower} with {fee_bps} bps, fee: {fee}")
                return fee
    
    # Default fee
    logger.debug(f"No pool match found for {pool_address}, using default fee")
    return (Decimal("500") / Decimal("1000000")).quantize(Decimal("0.000001"))  # 500 bps = 0.05%

def handle_metadata(args: list, config: Dict[str, Any]) -> list:
    """Handle metadata contract call."""
    if not args:
        return [18, 6, 0, 0, False, config["tokens"]["WETH"], config["tokens"]["USDC"]]
    
    pool_address = args[0]
    if isinstance(pool_address, str):
        pool_address = pool_address.lower().replace("0x", "")
    logger.debug(f"Checking metadata for pool: {pool_address}")
    
    # Check V2 pools
    dexes = config.get("dexes", {})
    aerodrome = dexes.get("aerodrome", {})
    v2_pools = aerodrome.get("pools", {})
    
    for pools in v2_pools.values():
        stable_addr = pools["stable"].lower().replace("0x", "")
        volatile_addr = pools["volatile"].lower().replace("0x", "")
        
        if pool_address == stable_addr:
            logger.debug("Found V2 stable pool metadata")
            return [18, 6, 0, 0, True, config["tokens"]["WETH"], config["tokens"]["USDC"]]
        if pool_address == volatile_addr:
            logger.debug("Found V2 volatile pool metadata")
            return [18, 6, 0, 0, False, config["tokens"]["WETH"], config["tokens"]["USDC"]]
    
    # Check V3 pools
    aerodrome_v3 = dexes.get("aerodrome_v3", {})
    v3_pools = aerodrome_v3.get("pools", {})
    
    for pools in v3_pools.values():
        for fee_key, addr in pools.items():
            addr_lower = addr.lower().replace("0x", "")
            if pool_address == addr_lower:
                fee_bps = int(fee_key.split("_")[1])
                logger.debug(f"Found V3 pool metadata with fee {fee_bps}")
                return [18, 6, 0, 0, False, config["tokens"]["WETH"], config["tokens"]["USDC"], fee_bps]
    
    logger.debug("No pool match found for metadata")
    return [18, 6, 0, 0, False, config["tokens"]["WETH"], config["tokens"]["USDC"]]

@pytest.fixture(scope="session")
async def mock_web3(config: Dict[str, Any]) -> Web3:
    """Mock Web3 instance with test responses."""
    w3 = Web3()
    
    def mock_contract_call(args, fn_name, contract_address=None):
        """Mock contract function calls."""
        logger.debug(f"Contract call: {fn_name} with args: {args}, contract: {contract_address}")
        
        if fn_name == "getPair":
            return handle_get_pair(args, config)
        elif fn_name == "getPool":
            return handle_get_pool(args, config)
        elif fn_name == "fee":
            # For fee calls, use the contract address as the pool address
            if contract_address:
                # Return raw basis points for fee calls (e.g., 500 for 0.05%)
                pool_address = contract_address.lower()
                for pools in config["dexes"]["aerodrome"]["pools"].values():
                    if pools["volatile"].lower() == pool_address:
                        return 500  # 0.05% for volatile pools
                    if pools["stable"].lower() == pool_address:
                        return 100  # 0.01% for stable pools
                for pools in config["dexes"]["aerodrome_v3"]["pools"].values():
                    for fee_key, addr in pools.items():
                        if addr.lower() == pool_address:
                            return int(fee_key.split("_")[1])  # Return fee from key (e.g., "fee_100" -> 100)
                return 500  # Default to 0.05%
            return handle_fee(args, config)
        elif fn_name == "metadata":
            return handle_metadata(args, config)
        elif fn_name == "getReserves":
            return [1000 * 10**18, 2000000 * 10**6, 0]  # 1000 WETH, 2M USDC
        elif fn_name == "slot0":
            return [2**96, 0, 0, 0, 0, 0, True]  # sqrt_price_x96 = 2^96 (price = 1)
        elif fn_name == "liquidity":
            return 1000000 * 10**18  # 1M units
        elif fn_name == "decimals":
            if not args:
                return 18
            token_address = args[0].lower()
            if token_address == config["tokens"]["WETH"].lower():
                return 18
            elif token_address == config["tokens"]["USDC"].lower():
                return 6
            return 18
        elif fn_name == "token0":
            return config["tokens"]["WETH"]
        elif fn_name == "token1":
            return config["tokens"]["USDC"]
        elif fn_name == "isPaused":
            return False
        elif fn_name == "getAmountsOut":
            if len(args) < 3:
                return None
            amount_in = args[0]
            return [amount_in, amount_in * 2000]  # 1 WETH = 2000 USDC
        elif fn_name == "quoteExactInput":
            if len(args) < 2:
                return [0, 0]
            amount_in = args[1]  # Second arg is amount_in
            return [int(amount_in * 2000), 0]  # 1 WETH = 2000 USDC
    
    # Create mock contract class
    class MockContract:
        def __init__(self, fn_name, address=None):
            self.fn_name = fn_name
            self.address = address
            self.fn_args = None
            self.contract_args = {}
        
        def __call__(self, *args, **kwargs):
            logger.debug(f"Contract function {self.fn_name} called with args: {args}, kwargs: {kwargs}")
            # Store args directly, don't convert to list yet
            self.fn_args = args
            self.contract_args = kwargs
            return self
        
        def call(self, *args, **kwargs):
            logger.debug(f"Contract function {self.fn_name} call() with args: {args}, kwargs: {kwargs}")
            # Convert stored args to list only if we have them
            combined_args = []
            if self.fn_args:
                # Handle both single values and tuples
                if isinstance(self.fn_args, tuple):
                    combined_args.extend(self.fn_args)
                else:
                    combined_args.append(self.fn_args)
            # Add any additional args from call()
            if args:
                combined_args.extend(args)
            logger.debug(f"Combined args for {self.fn_name}: {combined_args}")
            return mock_contract_call(combined_args, self.fn_name, self.address)
    
    class MockFunctions:
        def __init__(self, address):
            self.address = address
            
        def __getattr__(self, name):
            return MockContract(name, self.address)
    
    def create_contract(address, abi):
        """Create a mock contract with the given address."""
        mock_contract = MagicMock()
        mock_contract.functions = MockFunctions(address)
        return mock_contract

    # Mock eth module
    w3.eth = MagicMock()
    w3.eth.contract = create_contract
    w3.eth.get_block.return_value = {"timestamp": 1000000}
    w3.eth.get_transaction_count.return_value = 0
    
    return w3

@pytest.fixture(scope="function")
async def mock_process():
    """Mock psutil.Process for testing."""
    class MockProcess:
        def __init__(self):
            self.memory_info_value = None
            self.cpu_percent_value = 0.0
            self.nice_value = None
        
        def memory_info(self):
            class MemInfo:
                def __init__(self, rss):
                    self.rss = rss
            return MemInfo(self.memory_info_value or 100 * 1024 * 1024)  # 100MB default
        
        def cpu_percent(self):
            return self.cpu_percent_value
        
        def nice(self, value):
            self.nice_value = value
    
    return MockProcess()

@pytest.fixture(scope="function")
async def mock_network():
    """Mock psutil network counters for testing."""
    class MockNetwork:
        def __init__(self):
            self.bytes_sent = 0
            self.bytes_recv = 0
        
        def update(self, sent: int, recv: int):
            self.bytes_sent = sent
            self.bytes_recv = recv
    
    return MockNetwork()

@pytest.fixture(scope="function")
async def mock_task():
    """Mock asyncio.Task for testing."""
    class MockTask:
        def __init__(self):
            self.name = "mock_task"
            self.priority = 50
            self.cancelled = False
        
        def cancel(self):
            self.cancelled = True
    
    return MockTask()
