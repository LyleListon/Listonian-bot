"""
Mock Components Module

Provides mock implementations of system components for testing the dashboard:
- Mock Web3 Manager
- Mock Flash Loan Manager
- Mock Market Analyzer
- Mock Arbitrage Executor
"""

import asyncio
import random
from decimal import Decimal
from typing import Dict, Any, Optional
from eth_typing import ChecksumAddress
from web3 import Web3

from arbitrage_bot.core.interfaces import TokenPair, ExecutionResult
from arbitrage_bot.core.memory.memory_bank import MemoryBank

class MockWeb3Manager:
    """Mock Web3 manager for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize mock Web3 manager."""
        self.w3 = Web3()
        self.wallet_address = self.w3.to_checksum_address('0x742d35Cc6634C0532925a3b844Bc454e4438f44e')
        self.chain_id = 8453  # Base mainnet
        
        # Mock balance
        self._balance = Web3.to_wei(10, 'ether')  # 10 ETH
        
    async def initialize(self):
        """Mock initialization."""
        pass
        
    async def get_block_number(self) -> int:
        """Get mock current block number."""
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
        states = ['SCANNING', 'EXECUTING', 'VALIDATING', 'WAITING']
        return {
            "status": random.choice(states),
            "step": "BUNDLE_PREPARATION",
            "error": None,
            "retries": 0,
            "runtime": random.randint(10, 100)
        }

def create_mock_components(config: Dict[str, Any]) -> Dict[str, Any]:
    """Create mock system components for testing."""
    return {
        "web3_manager": MockWeb3Manager(config),
        "flash_loan_manager": MockFlashLoanManager(),
        "market_analyzer": MockMarketAnalyzer(),
        "arbitrage_executor": MockArbitrageExecutor(),
        "memory_bank": MemoryBank(storage_dir="data/test_memory_bank")
    }