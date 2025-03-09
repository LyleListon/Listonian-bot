"""Mock implementations for testing."""

import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal

from arbitrage_bot.core import (
    OpportunityDiscoveryManager,
    ExecutionManager,
    ArbitrageAnalytics,
    MarketDataProvider,
    ArbitrageOpportunity,
    ArbitrageRoute,
    RouteStep,
    ExecutionResult,
    OpportunityStatus,
    ExecutionStatus,
    TransactionStatus,
    TransactionDetails
)

class MockDiscoveryManager(OpportunityDiscoveryManager):
    """Mock implementation of OpportunityDiscoveryManager."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._opportunities = []
    
    async def register_detector(self, detector: Any, detector_id: str) -> None:
        pass
    
    async def register_validator(self, validator: Any, validator_id: str) -> None:
        pass
    
    async def discover_opportunities(
        self,
        max_results: int = 10,
        min_profit_wei: int = 0,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """Return mock opportunities."""
        weth = self.config["arbitrage"]["tokens"]["WETH"]["address"]
        
        opportunities = []
        for i in range(max_results):
            route = ArbitrageRoute(
                input_token_address=weth,
                input_amount_wei=int(0.1 * 10**18),  # 0.1 WETH
                steps=[
                    RouteStep(
                        dex_id=f"dex{i}",
                        input_token_address=weth,
                        output_token_address=f"0x{i:040x}",
                        pool_address=f"0x{(i+1):040x}",
                        pool_fee=3000,
                        input_amount_wei=int(0.1 * 10**18),
                        min_output_amount_wei=int(0.11 * 10**18)
                    )
                ]
            )
            
            opp = ArbitrageOpportunity(
                id=f"opp{i}",
                route=route,
                expected_profit=int(0.01 * 10**18),  # 0.01 WETH profit
                confidence_score=0.95,
                status=OpportunityStatus.READY,
                gas_estimate=200000,
                timestamp=1234567890
            )
            opportunities.append(opp)
        
        return opportunities

class MockExecutionManager(ExecutionManager):
    """Mock implementation of ExecutionManager."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._strategies = {}
        self._monitors = {}
    
    async def register_strategy(self, strategy: Any, strategy_id: str) -> None:
        self._strategies[strategy_id] = strategy
    
    async def register_monitor(self, monitor: Any, monitor_id: str) -> None:
        self._monitors[monitor_id] = monitor
    
    async def execute_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        strategy_id: str = "default",
        **kwargs
    ) -> ExecutionResult:
        """Return mock execution result."""
        # Simulate successful execution
        tx_details = TransactionDetails(
            hash="0x" + "1" * 64,
            from_address="0x" + "2" * 40,
            to_address="0x" + "3" * 40,
            value=0,
            gas_used=200000,
            gas_price=50 * 10**9,  # 50 gwei
            status=TransactionStatus.CONFIRMED,
            block_number=1234567,
            timestamp=1234567890
        )
        
        return ExecutionResult(
            opportunity_id=opportunity.id,
            status=ExecutionStatus.SUCCESS,
            transaction_details=tx_details,
            actual_profit=opportunity.expected_profit,
            error=None
        )
    
    async def get_execution_status(self, execution_id: str) -> ExecutionStatus:
        return ExecutionStatus.SUCCESS

class MockAnalyticsManager(ArbitrageAnalytics):
    """Mock implementation of ArbitrageAnalytics."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._opportunities = []
        self._executions = []
    
    async def record_opportunity(self, opportunity: ArbitrageOpportunity) -> None:
        self._opportunities.append(opportunity)
    
    async def record_execution(self, execution_result: ExecutionResult) -> None:
        self._executions.append(execution_result)
    
    async def get_performance_metrics(
        self,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        return {
            "total_opportunities": len(self._opportunities),
            "total_executions": len(self._executions),
            "total_profit_wei": sum(e.actual_profit for e in self._executions),
            "success_rate": 1.0
        }
    
    async def get_recent_opportunities(
        self,
        max_results: int = 100,
        min_profit_eth: float = 0.0
    ) -> List[ArbitrageOpportunity]:
        return self._opportunities[-max_results:]
    
    async def get_recent_executions(
        self,
        max_results: int = 100
    ) -> List[ExecutionResult]:
        return self._executions[-max_results:]

class MockMarketDataProvider(MarketDataProvider):
    """Mock implementation of MarketDataProvider."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._monitoring = False
        self._update_task = None
        self._callbacks = []
    
    async def get_current_market_condition(self) -> Dict[str, Any]:
        return {
            "block_number": 1234567,
            "timestamp": 1234567890,
            "gas_price": 50 * 10**9,  # 50 gwei
            "base_fee": 40 * 10**9,  # 40 gwei
            "priority_fee": 10 * 10**9,  # 10 gwei
            "network_congestion": 0.5
        }
    
    async def register_market_update_callback(
        self,
        callback: Any
    ) -> None:
        self._callbacks.append(callback)
    
    async def start_monitoring(
        self,
        update_interval_seconds: float = 60.0
    ) -> None:
        self._monitoring = True
        self._update_task = asyncio.create_task(self._monitor_loop(update_interval_seconds))
    
    async def stop_monitoring(self) -> None:
        self._monitoring = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None
    
    async def _monitor_loop(self, interval: float) -> None:
        while self._monitoring:
            market_condition = await self.get_current_market_condition()
            for callback in self._callbacks:
                try:
                    await callback(market_condition)
                except Exception:
                    pass
            await asyncio.sleep(interval)