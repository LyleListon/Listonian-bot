"""Mock arbitrage system for development and testing."""

import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class StrategyType(Enum):
    FLASH_LOAN = "FLASH_LOAN"
    MULTI_PATH = "MULTI_PATH"
    CROSS_DEX = "CROSS_DEX"

class OpportunityStatus(Enum):
    VALID = "VALID"
    PENDING = "PENDING"
    INVALID = "INVALID"
    EXECUTED = "EXECUTED"

class ExecutionStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"

@dataclass
class Route:
    input_token_address: str
    output_token_address: str

@dataclass
class Opportunity:
    id: str
    strategy_type: StrategyType
    route: Route
    expected_profit: int  # In wei
    confidence_score: float
    status: OpportunityStatus
    timestamp: float

@dataclass
class Execution:
    opportunity_id: str
    success: bool
    transaction_hash: Optional[str]
    status: ExecutionStatus
    gas_used: Optional[int]
    actual_profit: Optional[int]  # In wei
    timestamp: float

class MockArbitrageSystem:
    def __init__(self):
        self._running = False
        self._start_time = None
        self._opportunities = []
        self._executions = []
        self._discovery_enabled = True
        self._auto_execute_enabled = True
        
        # Generate some sample data
        self._generate_sample_data()
    
    def _generate_sample_data(self):
        # Sample token addresses
        tokens = [
            "0x4200000000000000000000000000000000000006",  # WETH
            "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",  # USDC
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDT
        ]
        
        # Generate opportunities
        for i in range(5):
            self._opportunities.append(
                Opportunity(
                    id=str(uuid.uuid4()),
                    strategy_type=StrategyType.FLASH_LOAN if i % 2 == 0 else StrategyType.MULTI_PATH,
                    route=Route(
                        input_token_address=tokens[i % 2],
                        output_token_address=tokens[(i + 1) % 2]
                    ),
                    expected_profit=int(0.01 * (10**18) * (1 + i * 0.5)),  # 0.01-0.03 ETH
                    confidence_score=0.6 + (i * 0.1),
                    status=OpportunityStatus.VALID if i < 3 else OpportunityStatus.EXECUTED,
                    timestamp=time.time() - (i * 300)  # 5 minutes apart
                )
            )
        
        # Generate executions
        for i in range(3):
            opp = self._opportunities[i]
            self._executions.append(
                Execution(
                    opportunity_id=opp.id,
                    success=i < 2,
                    transaction_hash=f"0x{''.join(['0123456789abcdef'[i % 16] for _ in range(64)])}" if i < 2 else None,
                    status=ExecutionStatus.SUCCESS if i < 2 else ExecutionStatus.FAILED,
                    gas_used=150000 + (i * 10000) if i < 2 else None,
                    actual_profit=int(opp.expected_profit * 0.9) if i < 2 else None,
                    timestamp=time.time() - (i * 600)  # 10 minutes apart
                )
            )
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def discovery_enabled(self) -> bool:
        return self._discovery_enabled
    
    @property
    def auto_execute_enabled(self) -> bool:
        return self._auto_execute_enabled
    
    @property
    def uptime_seconds(self) -> int:
        if not self._start_time:
            return 0
        return int(time.time() - self._start_time)
    
    async def start(self):
        self._running = True
        self._start_time = time.time()
    
    async def stop(self):
        self._running = False
        self._start_time = None
    
    async def get_recent_opportunities(
        self,
        max_results: int = 10,
        min_profit_eth: float = 0.001
    ) -> List[Opportunity]:
        min_profit_wei = int(min_profit_eth * 10**18)
        opportunities = [
            opp for opp in self._opportunities
            if opp.expected_profit >= min_profit_wei
        ]
        opportunities.sort(key=lambda x: x.timestamp, reverse=True)
        return opportunities[:max_results]
    
    async def get_recent_executions(
        self,
        max_results: int = 10
    ) -> List[Execution]:
        executions = sorted(self._executions, key=lambda x: x.timestamp, reverse=True)
        return executions[:max_results]
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        total_opportunities = len(self._opportunities)
        total_executions = len(self._executions)
        successful_executions = len([e for e in self._executions if e.success])
        total_profit_wei = sum(e.actual_profit or 0 for e in self._executions if e.success)
        
        return {
            "opportunities_found": total_opportunities,
            "executed": total_executions,
            "successful": successful_executions,
            "total_profit_eth": total_profit_wei / 10**18,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0.0,
            "average_gas_used": sum(e.gas_used or 0 for e in self._executions) // max(total_executions, 1),
            "average_execution_time": 2.5,  # Mock average execution time in seconds
            "timestamp": time.time()
        }
    
    async def get_opportunity_by_id(self, opportunity_id: str) -> Optional[Opportunity]:
        for opp in self._opportunities:
            if opp.id == opportunity_id:
                return opp
        return None
    
    async def execute_opportunity(self, opportunity: Opportunity, strategy_id: str = "standard"):
        # Simulate execution by creating a new execution record
        execution = Execution(
            opportunity_id=opportunity.id,
            success=True,
            transaction_hash=f"0x{''.join(['0123456789abcdef'[(len(self._executions) + 1) % 16] for _ in range(64)])}",
            status=ExecutionStatus.SUCCESS,
            gas_used=150000,
            actual_profit=int(opportunity.expected_profit * 0.9),
            timestamp=time.time()
        )
        self._executions.append(execution)
        
        # Update opportunity status
        for opp in self._opportunities:
            if opp.id == opportunity.id:
                opp.status = OpportunityStatus.EXECUTED
                break