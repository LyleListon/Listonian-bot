"""
Dashboard Backend Application

Provides API endpoints for:
- Configuration management
- Real-time metrics
- System status
"""

import asyncio
import logging
import os
import random
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple, NamedTuple
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from web3 import Web3
from eth_typing import ChecksumAddress

from arbitrage_bot.utils.config_loader import load_config, save_config

logger = logging.getLogger(__name__)

app = FastAPI()

# Get the directory containing this file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")

# Default configuration
DEFAULT_CONFIG = {
    "trading": {
        "max_slippage": 0.5,
        "max_liquidity_usage": 30,
        "min_profit_threshold": 0.01,
        "max_gas_price": 500
    }
}

# Mock Components
class MockEth:
    """Mock Eth class for testing."""
    
    def __init__(self, balance: int):
        """Initialize mock Eth."""
        self._balance = balance
        
    async def get_balance(self, address: str) -> int:
        """Mock get_balance method."""
        await asyncio.sleep(0.1)  # Simulate network delay
        return self._balance

class MockWeb3Manager:
    """Mock Web3 manager for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize mock Web3 manager."""
        self.w3 = Web3()
        self.wallet_address = self.w3.to_checksum_address('0x742d35Cc6634C0532925a3b844Bc454e4438f44e')
        self.chain_id = 8453  # Base mainnet
        self._balance = Web3.to_wei(10, 'ether')  # 10 ETH
        
        # Create mock eth interface
        self.eth = MockEth(self._balance)
        
    async def initialize(self):
        """Mock initialization."""
        pass
        
    async def get_block_number(self) -> int:
        """Get mock current block number."""
        await asyncio.sleep(0.1)  # Simulate network delay
        return 1000000
        
    def to_wei(self, value: float, unit: str) -> int:
        """Convert value to wei."""
        return Web3.to_wei(value, unit)
        
    def from_wei(self, value: int, unit: str) -> Decimal:
        """Convert wei to value."""
        return Decimal(str(Web3.from_wei(value, unit)))

class MockFlashLoanManager:
    """Mock flash loan manager for testing."""
    
    def __init__(self):
        """Initialize mock flash loan manager."""
        self.max_slippage = Decimal('0.005')  # 0.5%
        self.min_profit_threshold = Web3.to_wei(0.01, 'ether')  # 0.01 ETH
        
    def update_settings(self, slippage: float, min_profit: float):
        """Update mock settings."""
        self.max_slippage = Decimal(str(slippage))
        self.min_profit_threshold = Web3.to_wei(min_profit, 'ether')

class MockMarketAnalyzer:
    """Mock market analyzer for testing."""
    
    def __init__(self):
        """Initialize mock market analyzer."""
        self.max_price_impact = Decimal('0.005')  # 0.5%
        
    def update_settings(self, price_impact: float):
        """Update mock settings."""
        self.max_price_impact = Decimal(str(price_impact))

class MockArbitrageExecutor:
    """Mock arbitrage executor for testing."""
    
    def __init__(self):
        """Initialize mock arbitrage executor."""
        self.max_gas_price = Web3.to_wei(500, 'gwei')  # 500 gwei
        self._execution_count = 0
        self._success_count = 0
        self._total_profit = 0
        self._total_gas = 0
        
    def update_settings(self, max_gas_price: int):
        """Update mock settings."""
        self.max_gas_price = Web3.to_wei(max_gas_price, 'gwei')
        
    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get mock execution statistics."""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Generate some random stats
        self._execution_count += 1
        if random.random() > 0.2:  # 80% success rate
            self._success_count += 1
            profit = random.randint(
                Web3.to_wei(0.01, 'ether'),
                Web3.to_wei(0.1, 'ether')
            )
            self._total_profit += profit
            
        gas_used = random.randint(100000, 300000)
        self._total_gas += gas_used
        
        return {
            "total_executions": self._execution_count,
            "success_rate": self._success_count / self._execution_count if self._execution_count > 0 else 0,
            "avg_profit": self._total_profit // self._execution_count if self._execution_count > 0 else 0,
            "avg_gas": self._total_gas // self._execution_count if self._execution_count > 0 else 0
        }
        
    async def get_current_state(self) -> Optional[Dict[str, Any]]:
        """Get mock current state."""
        await asyncio.sleep(0.1)  # Simulate network delay
        states = ['SCANNING', 'EXECUTING', 'VALIDATING', 'WAITING']
        return {
            "status": random.choice(states),
            "step": "BUNDLE_PREPARATION",
            "error": None,
            "retries": 0,
            "runtime": random.randint(10, 100)
        }

class MockMemoryBank:
    """Mock memory bank for testing."""
    
    def __init__(self, storage_dir: str = "data/test_memory_bank"):
        """Initialize mock memory bank."""
        self.storage_dir = storage_dir
        
    async def initialize(self):
        """Mock initialization."""
        pass
        
    async def update_system_metrics(self, metrics: Dict[str, Any]):
        """Mock metrics update."""
        pass

def create_mock_components(config: Dict[str, Any]) -> Dict[str, Any]:
    """Create mock system components for testing."""
    return {
        "web3_manager": MockWeb3Manager(config),
        "flash_loan_manager": MockFlashLoanManager(),
        "market_analyzer": MockMarketAnalyzer(),
        "arbitrage_executor": MockArbitrageExecutor(),
        "memory_bank": MockMemoryBank()
    }

class TradingConfig(BaseModel):
    """Trading configuration parameters."""
    slippage: float
    maxLiquidity: int
    minProfit: float
    maxGasPrice: int

class SystemComponents:
    """Holds system component instances."""
    def __init__(self):
        """Initialize system components."""
        self.web3_manager = None
        self.flash_loan_manager = None
        self.market_analyzer = None
        self.arbitrage_executor = None
        self.memory_bank = None

system = SystemComponents()

@app.on_event("startup")
async def startup_event():
    """Initialize system components on startup."""
    try:
        # Try to load config, use defaults if not found
        try:
            config = load_config()
            logger.info("Loaded configuration from file")
        except FileNotFoundError:
            config = DEFAULT_CONFIG.copy()
            logger.info("Using default configuration")
        
        # Initialize mock components
        components = create_mock_components(config)
        
        # Set components
        system.web3_manager = components["web3_manager"]
        system.flash_loan_manager = components["flash_loan_manager"]
        system.market_analyzer = components["market_analyzer"]
        system.arbitrage_executor = components["arbitrage_executor"]
        system.memory_bank = components["memory_bank"]
        
        # Initialize components
        await system.web3_manager.initialize()
        await system.memory_bank.initialize()
        
        logger.info("System components initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        raise

@app.get("/")
async def read_root():
    """Serve the dashboard HTML."""
    return FileResponse(os.path.join(current_dir, "static/index.html"))

@app.get("/api/config")
async def get_config():
    """Get current trading configuration."""
    try:
        config = load_config()
    except FileNotFoundError:
        config = DEFAULT_CONFIG.copy()
        
    return {
        "slippage": config.get("trading", {}).get("max_slippage", 0.5),
        "maxLiquidity": config.get("trading", {}).get("max_liquidity_usage", 30),
        "minProfit": config.get("trading", {}).get("min_profit_threshold", 0.01),
        "maxGasPrice": config.get("trading", {}).get("max_gas_price", 500)
    }

@app.post("/api/config")
async def update_config(trading_config: TradingConfig):
    """Update trading configuration."""
    try:
        # Load current config or use defaults
        try:
            config = load_config()
        except FileNotFoundError:
            config = DEFAULT_CONFIG.copy()
        
        # Update trading parameters
        if "trading" not in config:
            config["trading"] = {}
            
        config["trading"].update({
            "max_slippage": trading_config.slippage,
            "max_liquidity_usage": trading_config.maxLiquidity,
            "min_profit_threshold": trading_config.minProfit,
            "max_gas_price": trading_config.maxGasPrice
        })
        
        # Save updated config
        await save_config(config)
        
        # Update component configurations
        if system.flash_loan_manager:
            system.flash_loan_manager.update_settings(
                slippage=trading_config.slippage / 100,
                min_profit=trading_config.minProfit
            )
            
        if system.market_analyzer:
            system.market_analyzer.update_settings(
                price_impact=trading_config.slippage / 100
            )
            
        if system.arbitrage_executor:
            system.arbitrage_executor.update_settings(
                max_gas_price=trading_config.maxGasPrice
            )

        # Update memory bank metrics
        await system.memory_bank.update_system_metrics({
            "config_updated": True,
            "settings": {
                "slippage": trading_config.slippage,
                "max_liquidity": trading_config.maxLiquidity,
                "min_profit": trading_config.minProfit,
                "max_gas_price": trading_config.maxGasPrice
            }
        })
        
        logger.info("Trading configuration updated successfully")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics")
async def get_metrics():
    """Get real-time system metrics."""
    try:
        # Get wallet balance
        wallet_balance = await system.web3_manager.eth.get_balance(
            system.web3_manager.wallet_address
        )
        wallet_balance_eth = system.web3_manager.from_wei(wallet_balance, 'ether')
        
        # Get execution stats
        execution_stats = await system.arbitrage_executor.get_execution_stats()
        
        # Get current state
        current_state = await system.arbitrage_executor.get_current_state()
        
        return {
            "walletBalance": float(wallet_balance_eth),
            "totalProfit": execution_stats["avg_profit"] * execution_stats["total_executions"],
            "successRate": execution_stats["success_rate"] * 100,
            "averageGas": execution_stats["avg_gas"],
            "averageProfit": execution_stats["avg_profit"],
            "totalExecutions": execution_stats["total_executions"],
            "currentState": current_state
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    """Get system status and health check."""
    try:
        return {
            "status": "running",
            "web3_connected": bool(system.web3_manager and system.web3_manager.w3.is_connected()),
            "components_initialized": all([
                system.web3_manager,
                system.flash_loan_manager,
                system.market_analyzer,
                system.arbitrage_executor
            ]),
            "current_block": await system.web3_manager.get_block_number()
        }
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=9050)