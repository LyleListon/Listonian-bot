"""
Arbitrage System Tests

This module provides tests for the arbitrage system architecture.
These tests demonstrate how to use the architecture and validate its functionality.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from unittest import mock

import pytest
import sys

# Add the project root to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from models
from arbitrage_bot.core.arbitrage.models import (
    ArbitrageOpportunity, ArbitrageRoute, RouteStep, ExecutionResult,
    StrategyType, OpportunityStatus, ExecutionStatus, TransactionStatus,
    ErrorType, ErrorDetails, TransactionDetails, PerformanceMetrics, ArbitrageSettings
)
# Import from interfaces
from arbitrage_bot.core.arbitrage.interfaces import (
    ArbitrageSystem, OpportunityDiscoveryManager, OpportunityDetector,
    OpportunityValidator, ExecutionManager, ExecutionStrategy,
    TransactionMonitor, ArbitrageAnalytics, MarketDataProvider
)
# Import base system
from arbitrage_bot.core.arbitrage.base_system import BaseArbitrageSystem
# Import factory functions
from arbitrage_bot.core.arbitrage.factory import create_arbitrage_system, create_arbitrage_system_from_config

# Dummy type for mock testing
class MockableProtocol:
    """Dummy class to avoid type checking errors with runtime protocols in tests."""
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Mock Implementations for Testing
class MockOpportunityDetector(MockableProtocol):
    """Mock implementation of OpportunityDetector for testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.called_count = 0
        
    async def detect_opportunities(
        self, 
        market_condition: Dict[str, Any], 
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """Mock method that returns predefined opportunities."""
        self.called_count += 1
        logger.info(f"MockOpportunityDetector.detect_opportunities called (count: {self.called_count})")
        
        # Create mock opportunities
        opportunities = []
        for i in range(3):
            # Create route steps
            steps = [
                RouteStep(
                    dex_id="uniswap",
                    input_token_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
                    output_token_address="0x6B175474E89094C44Da98b954EedeAC495271d0F",  # DAI
                    pool_address="0xa478c2975ab1ea89e8196811f51a7b7ade33eb11",
                    input_amount=1000000000000000000,  # 1 ETH
                    expected_output=1800000000000000000000  # 1800 DAI
                ),
                RouteStep(
                    dex_id="sushiswap",
                    input_token_address="0x6B175474E89094C44Da98b954EedeAC495271d0F",  # DAI
                    output_token_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
                    pool_address="0xc3d03e4f041fd4cd388c549ee2a29a9e5075882f",
                    input_amount=1800000000000000000000,  # 1800 DAI
                    expected_output=1050000000000000000  # 1.05 ETH
                )
            ]
            
            # Create route
            route = ArbitrageRoute(
                steps=steps,
                input_token_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
                output_token_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
                input_amount=1000000000000000000,  # 1 ETH
                expected_output=1050000000000000000,  # 1.05 ETH
                expected_profit=50000000000000000  # 0.05 ETH
            )
            
            # Create opportunity
            opportunity = ArbitrageOpportunity(
                id=f"opp-{i}-{uuid.uuid4()}",
                strategy_type=StrategyType.CROSS_DEX,
                route=route,
                input_amount=1000000000000000000,  # 1 ETH
                expected_output=1050000000000000000,  # 1.05 ETH
                expected_profit=50000000000000000,  # 0.05 ETH
                confidence_score=0.8,
                detector_id="mock-detector",
                gas_estimate=200000
            )
            
            opportunities.append(opportunity)
        
        return opportunities


class MockOpportunityValidator(MockableProtocol):
    """Mock implementation of OpportunityValidator for testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.called_count = 0
        
    async def validate_opportunity(
        self, 
        opportunity: ArbitrageOpportunity, 
        market_condition: Dict[str, Any], 
        **kwargs
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """Mock method that validates opportunities."""
        self.called_count += 1
        logger.info(f"MockOpportunityValidator.validate_opportunity called (count: {self.called_count})")
        
        # Simple validation based on profit
        valid = opportunity.expected_profit > 0
        error_message = None if valid else "Opportunity has no profit"
        confidence = 0.9 if valid else 0.0
        
        return valid, error_message, confidence


class MockDiscoveryManager(MockableProtocol, OpportunityDiscoveryManager):
    """Mock implementation of OpportunityDiscoveryManager for testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.detectors = {}
        self.validators = {}
        
    async def register_detector(
        self, 
        detector: OpportunityDetector, 
        detector_id: str
    ) -> None:
        """Register a detector."""
        logger.info(f"MockDiscoveryManager.register_detector called with id {detector_id}")
        self.detectors[detector_id] = detector
        
    async def register_validator(
        self, 
        validator: OpportunityValidator, 
        validator_id: str
    ) -> None:
        """Register a validator."""
        logger.info(f"MockDiscoveryManager.register_validator called with id {validator_id}")
        self.validators[validator_id] = validator
        
    async def discover_opportunities(
        self, 
        max_results: int = 10, 
        min_profit_wei: int = 0, 
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """Discover opportunities using registered detectors and validators."""
        logger.info(f"MockDiscoveryManager.discover_opportunities called (max_results={max_results}, min_profit_wei={min_profit_wei})")
        
        # Create a mock market condition
        market_condition = {
            "timestamp": time.time(),
            "prices": {
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": 1800,  # WETH/USD
                "0x6B175474E89094C44Da98b954EedeAC495271d0F": 1,     # DAI/USD
            },
            "gas_price": 30000000000  # 30 gwei
        }
        
        # Get opportunities from detectors
        all_opportunities = []
        for detector_id, detector in self.detectors.items():
            opportunities = await detector.detect_opportunities(market_condition, **kwargs)
            for opp in opportunities:
                opp.detector_id = detector_id
                all_opportunities.append(opp)
        
        # Validate opportunities
        valid_opportunities = []
        for opp in all_opportunities:
            # Skip opportunities below min profit
            if opp.expected_profit < min_profit_wei:
                opp.status = OpportunityStatus.INVALID
                opp.error_message = f"Profit below threshold: {opp.expected_profit} < {min_profit_wei}"
                continue
            
            # Validate with each validator
            valid = True
            for validator_id, validator in self.validators.items():
                is_valid, error_message, confidence = await validator.validate_opportunity(
                    opp, market_condition, **kwargs
                )
                
                if not is_valid:
                    opp.status = OpportunityStatus.INVALID
                    opp.error_message = error_message
                    valid = False
                    break
                
                # Update confidence with minimum confidence from all validators
                if confidence is not None:
                    opp.confidence_score = min(opp.confidence_score, confidence)
                
                opp.validator_id = validator_id
            
            if valid:
                opp.status = OpportunityStatus.VALID
                valid_opportunities.append(opp)
        
        # Sort by profit and limit results
        valid_opportunities.sort(key=lambda o: o.expected_profit, reverse=True)
        return valid_opportunities[:max_results]


class MockExecutionStrategy(MockableProtocol):
    """Mock implementation of ExecutionStrategy for testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.called_count = 0
        
    async def execute_opportunity(
        self, 
        opportunity: ArbitrageOpportunity, 
        **kwargs
    ) -> ExecutionResult:
        """Mock method that executes opportunities."""
        self.called_count += 1
        logger.info(f"MockExecutionStrategy.execute_opportunity called (count: {self.called_count})")
        
        # Simulate transaction
        tx_hash = f"0x{uuid.uuid4().hex}"
        
        # Create transaction details
        transaction_details = TransactionDetails(
            hash=tx_hash,
            from_address="0x1234567890123456789012345678901234567890",
            to_address="0x0987654321098765432109876543210987654321",
            value=0,
            gas_limit=300000,
            gas_price=30000000000,  # 30 gwei
            nonce=123,
            data="0x12345678",
            chain_id=1,
            status=TransactionStatus.CONFIRMED,
            block_number=12345678,
            gas_used=200000,
            timestamp=time.time(),
            confirmation_time=time.time() + 30
        )
        
        # Create execution result
        execution_result = ExecutionResult(
            id=f"exec-{uuid.uuid4()}",
            opportunity_id=opportunity.id,
            status=ExecutionStatus.SUCCESS,
            timestamp=time.time(),
            transaction_hash=tx_hash,
            transaction_details=transaction_details,
            success=True,
            actual_profit=opportunity.expected_profit,
            expected_profit=opportunity.expected_profit,
            gas_used=200000,
            gas_price=30000000000,  # 30 gwei
            strategy_id="mock-strategy",
            confirmations=12
        )
        
        return execution_result


class MockTransactionMonitor(MockableProtocol):
    """Mock implementation of TransactionMonitor for testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.called_count = 0
        
    async def monitor_transaction(
        self, 
        transaction_hash: str, 
        **kwargs
    ) -> TransactionStatus:
        """Mock method that monitors transactions."""
        self.called_count += 1
        logger.info(f"MockTransactionMonitor.monitor_transaction called (count: {self.called_count})")
        
        # Always return confirmed for simplicity
        return TransactionStatus.CONFIRMED


class MockExecutionManager(MockableProtocol, ExecutionManager):
    """Mock implementation of ExecutionManager for testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.strategies = {}
        self.monitors = {}
        self.executions = {}
        
    async def register_strategy(
        self, 
        strategy: ExecutionStrategy, 
        strategy_id: str
    ) -> None:
        """Register a strategy."""
        logger.info(f"MockExecutionManager.register_strategy called with id {strategy_id}")
        self.strategies[strategy_id] = strategy
        
    async def register_monitor(
        self, 
        monitor: TransactionMonitor, 
        monitor_id: str
    ) -> None:
        """Register a monitor."""
        logger.info(f"MockExecutionManager.register_monitor called with id {monitor_id}")
        self.monitors[monitor_id] = monitor
        
    async def execute_opportunity(
        self, 
        opportunity: ArbitrageOpportunity,
        strategy_id: str = "default", 
        **kwargs
    ) -> ExecutionResult:
        """Execute an opportunity using a registered strategy."""
        logger.info(f"MockExecutionManager.execute_opportunity called with strategy {strategy_id}")
        
        # Get strategy
        strategy = self.strategies.get(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")
        
        # Execute opportunity
        execution_result = await strategy.execute_opportunity(opportunity, **kwargs)
        
        # Store execution result
        self.executions[execution_result.id] = execution_result
        
        # Monitor transaction if available
        if execution_result.transaction_hash and self.monitors:
            monitor_id, monitor = next(iter(self.monitors.items()))
            status = await monitor.monitor_transaction(execution_result.transaction_hash)
            if status != TransactionStatus.CONFIRMED:
                execution_result.status = ExecutionStatus.FAILED
                execution_result.success = False
        
        return execution_result
        
    async def get_execution_status(
        self, 
        execution_id: str
    ) -> ExecutionStatus:
        """Get the status of an execution."""
        logger.info(f"MockExecutionManager.get_execution_status called for id {execution_id}")
        
        # Get execution
        execution = self.executions.get(execution_id)
        if not execution:
            return ExecutionStatus.FAILED
        
        return execution.status


class MockAnalyticsManager(MockableProtocol, ArbitrageAnalytics):
    """Mock implementation of ArbitrageAnalytics for testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.opportunities = []
        self.executions = []
        
    async def record_opportunity(
        self, 
        opportunity: ArbitrageOpportunity
    ) -> None:
        """Record an opportunity."""
        logger.info(f"MockAnalyticsManager.record_opportunity called for id {opportunity.id}")
        self.opportunities.append(opportunity)
        
    async def record_execution(
        self, 
        execution_result: ExecutionResult
    ) -> None:
        """Record an execution result."""
        logger.info(f"MockAnalyticsManager.record_execution called for id {execution_result.id}")
        self.executions.append(execution_result)
        
    async def get_performance_metrics(
        self,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics."""
        logger.info(f"MockAnalyticsManager.get_performance_metrics called (time_period_days={time_period_days})")
        
        # Calculate metrics
        total_profit = sum(e.actual_profit or 0 for e in self.executions if e.success)
        total_gas_used = sum(e.gas_used or 0 for e in self.executions if e.success)
        successful_count = sum(1 for e in self.executions if e.success)
        failed_count = sum(1 for e in self.executions if not e.success)
        
        # Create metrics dictionary
        metrics = {
            "opportunities_found": len(self.opportunities),
            "opportunities_valid": sum(1 for o in self.opportunities if o.status == OpportunityStatus.VALID),
            "opportunities_invalid": sum(1 for o in self.opportunities if o.status == OpportunityStatus.INVALID),
            "executions_attempted": len(self.executions),
            "executions_successful": successful_count,
            "executions_failed": failed_count,
            "total_profit": total_profit,
            "total_profit_eth": total_profit / 10**18,
            "total_gas_used": total_gas_used,
            "success_rate": successful_count / len(self.executions) if self.executions else 0.0,
            "timestamp": time.time()
        }
        
        if successful_count > 0:
            metrics["average_profit_per_execution"] = total_profit / successful_count
            metrics["average_gas_per_execution"] = total_gas_used / successful_count
        
        return metrics
        
    async def get_recent_opportunities(
        self,
        max_results: int = 100,
        min_profit_eth: float = 0.0
    ) -> List[ArbitrageOpportunity]:
        """Get recent opportunities."""
        logger.info(f"MockAnalyticsManager.get_recent_opportunities called (max_results={max_results}, min_profit_eth={min_profit_eth})")
        
        # Filter by profit
        min_profit_wei = int(min_profit_eth * 10**18)
        filtered = [o for o in self.opportunities if o.expected_profit >= min_profit_wei]
        
        # Sort by timestamp (most recent first) and limit results
        sorted_opps = sorted(filtered, key=lambda o: o.timestamp, reverse=True)
        return sorted_opps[:max_results]
        
    async def get_recent_executions(
        self,
        max_results: int = 100
    ) -> List[ExecutionResult]:
        """Get recent executions."""
        logger.info(f"MockAnalyticsManager.get_recent_executions called (max_results={max_results})")
        
        # Sort by timestamp (most recent first) and limit results
        sorted_execs = sorted(self.executions, key=lambda e: e.timestamp, reverse=True)
        return sorted_execs[:max_results]


class MockMarketDataProvider(MockableProtocol, MarketDataProvider):
    """Mock implementation of MarketDataProvider for testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.callbacks = []
        self._monitoring = False
        self._update_task = None
        
    async def get_current_market_condition(
        self
    ) -> Dict[str, Any]:
        """Get the current market condition."""
        logger.info("MockMarketDataProvider.get_current_market_condition called")
        
        # Create mock market condition
        market_condition = {
            "timestamp": time.time(),
            "prices": {
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": 1800,  # WETH/USD
                "0x6B175474E89094C44Da98b954EedeAC495271d0F": 1,     # DAI/USD
            },
            "pools": {
                "0xa478c2975ab1ea89e8196811f51a7b7ade33eb11": {
                    "token0": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                    "token1": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                    "reserve0": 1000000000000000000000,  # 1000 WETH
                    "reserve1": 1800000000000000000000000,  # 1,800,000 DAI
                    "fee": 0.003
                },
                "0xc3d03e4f041fd4cd388c549ee2a29a9e5075882f": {
                    "token0": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                    "token1": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                    "reserve0": 500000000000000000000,   # 500 WETH
                    "reserve1": 910000000000000000000000,  # 910,000 DAI
                    "fee": 0.003
                }
            },
            "gas_price": 30000000000,  # 30 gwei
            "block_number": 12345678
        }
        
        return market_condition
        
    async def register_market_update_callback(
        self,
        callback: callable
    ) -> None:
        """Register a callback for market updates."""
        logger.info("MockMarketDataProvider.register_market_update_callback called")
        self.callbacks.append(callback)
        
    async def start_monitoring(
        self,
        update_interval_seconds: float = 60.0
    ) -> None:
        """Start monitoring market conditions."""
        if self._monitoring:
            logger.warning("Market monitoring already started")
            return
        
        logger.info(f"MockMarketDataProvider.start_monitoring called (update_interval_seconds={update_interval_seconds})")
        self._monitoring = True
        
        # Start update task
        self._update_task = asyncio.create_task(
            self._update_loop(update_interval_seconds)
        )
        
    async def stop_monitoring(
        self
    ) -> None:
        """Stop monitoring market conditions."""
        if not self._monitoring:
            logger.warning("Market monitoring not started")
            return
        
        logger.info("MockMarketDataProvider.stop_monitoring called")
        self._monitoring = False
        
        # Cancel update task
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None
            
    async def _update_loop(
        self,
        update_interval_seconds: float
    ) -> None:
        """
        Background task for updating market conditions.
        
        Args:
            update_interval_seconds: Time between updates in seconds
        """
        logger.info("Starting market update loop")
        
        while self._monitoring:
            try:
                # Get current market condition
                market_condition = await self.get_current_market_condition()
                
                # Call registered callbacks
                for callback in self.callbacks:
                    try:
                        await callback(market_condition)
                    except Exception as e:
                        logger.error(f"Error in market update callback: {e}", exc_info=True)
            
            except asyncio.CancelledError:
                logger.info("Market update loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in market update loop: {e}", exc_info=True)
            
            # Wait for next update
            try:
                await asyncio.sleep(update_interval_seconds)
            except asyncio.CancelledError:
                break
        
        logger.info("Market update loop stopped")


# Test Functions
@pytest.mark.asyncio
async def test_arbitrage_system_creation():
    """Test creating an arbitrage system."""
    # Create components
    discovery_manager = MockDiscoveryManager()
    execution_manager = MockExecutionManager()
    analytics_manager = MockAnalyticsManager()
    market_data_provider = MockMarketDataProvider()
    
    # Create config
    config = {
        "arbitrage": {
            "auto_execute": False,
            "min_profit_threshold_eth": 0.01,
            "max_opportunities_per_cycle": 5,
            "discovery_interval_seconds": 30.0,
            "execution_interval_seconds": 60.0,
            "min_confidence_threshold": 0.7,
            "max_slippage_percent": 0.5,
            "max_gas_price_gwei": 50.0
        }
    }
    
    # Create arbitrage system
    arbitrage_system = BaseArbitrageSystem(
        discovery_manager=discovery_manager,
        execution_manager=execution_manager,
        analytics_manager=analytics_manager,
        market_data_provider=market_data_provider,
        config=config
    )
    
    # Basic assertions
    assert arbitrage_system is not None
    assert not arbitrage_system.is_running
    assert arbitrage_system.uptime_seconds == 0.0


@pytest.mark.asyncio
async def test_arbitrage_system_lifecycle():
    """Test the full lifecycle of an arbitrage system."""
    # Create components
    discovery_manager = MockDiscoveryManager()
    execution_manager = MockExecutionManager()
    analytics_manager = MockAnalyticsManager()
    market_data_provider = MockMarketDataProvider()
    
    # Register mock detector and validator
    await discovery_manager.register_detector(
        MockOpportunityDetector(),
        "mock-detector"
    )
    
    await discovery_manager.register_validator(
        MockOpportunityValidator(),
        "mock-validator"
    )
    
    # Register mock strategy and monitor
    await execution_manager.register_strategy(
        MockExecutionStrategy(),
        "mock-strategy"
    )
    
    await execution_manager.register_monitor(
        MockTransactionMonitor(),
        "mock-monitor"
    )
    
    # Create config
    config = {
        "arbitrage": {
            "auto_execute": False,
            "min_profit_threshold_eth": 0.01,
            "max_opportunities_per_cycle": 5,
            "discovery_interval_seconds": 30.0,
            "execution_interval_seconds": 60.0,
            "min_confidence_threshold": 0.7,
            "max_slippage_percent": 0.5,
            "max_gas_price_gwei": 50.0
        }
    }
    
    # Create arbitrage system
    arbitrage_system = BaseArbitrageSystem(
        discovery_manager=discovery_manager,
        execution_manager=execution_manager,
        analytics_manager=analytics_manager,
        market_data_provider=market_data_provider,
        config=config
    )
    
    try:
        # Start the system
        await arbitrage_system.start()
        
        # Verify system is running
        assert arbitrage_system.is_running
        assert arbitrage_system.uptime_seconds > 0.0
        
        # Discover opportunities
        opportunities = await arbitrage_system.discover_opportunities(
            max_results=3,
            min_profit_eth=0.01
        )
        
        assert len(opportunities) > 0
        assert isinstance(opportunities[0], ArbitrageOpportunity)
        assert opportunities[0].status == OpportunityStatus.VALID
        
        # Execute opportunity
        execution_result = await arbitrage_system.execute_opportunity(
            opportunity=opportunities[0],
            strategy_id="mock-strategy"
        )
        
        assert isinstance(execution_result, ExecutionResult)
        assert execution_result.status == ExecutionStatus.SUCCESS
        assert execution_result.success
        
        # Wait a moment for background tasks
        await asyncio.sleep(1)
        
        # Get recent opportunities
        recent_opps = await arbitrage_system.get_recent_opportunities(max_results=5)
        assert len(recent_opps) > 0
        
        # Get recent executions
        recent_execs = await arbitrage_system.get_recent_executions(max_results=5)
        assert len(recent_execs) > 0
        
        # Get performance metrics
        metrics = await arbitrage_system.get_performance_metrics()
        assert "total_profit_eth" in metrics
        assert metrics["opportunities_found"] > 0
        assert metrics["executions_successful"] > 0
        
    finally:
        # Stop the system
        await arbitrage_system.stop()
        
        # Verify system is stopped
        assert not arbitrage_system.is_running


@pytest.mark.asyncio
async def test_factory_functions():
    """Test the factory functions for creating arbitrage systems."""
    # Create config
    config = {
        "arbitrage": {
            "auto_execute": False,
            "min_profit_threshold_eth": 0.01,
            "max_opportunities_per_cycle": 5,
            "discovery_interval_seconds": 30.0,
            "execution_interval_seconds": 60.0,
            "min_confidence_threshold": 0.7,
            "max_slippage_percent": 0.5,
            "max_gas_price_gwei": 50.0
        },
        "discovery": {
            "detectors": [
                {"type": "triangular", "id": "triangular-detector"},
                {"type": "cross_dex", "id": "cross-dex-detector"}
            ],
            "validators": [
                {"type": "basic", "id": "basic-validator"}
            ]
        },
        "execution": {
            "strategies": [
                {"type": "standard", "id": "standard-strategy"},
                {"type": "flashbots", "id": "flashbots-strategy"}
            ],
            "monitors": [
                {"type": "standard", "id": "standard-monitor"}
            ]
        }
    }
    
    # Create temp file for config
    temp_config_path = "temp_config.json"
    with open(temp_config_path, "w") as f:
        json.dump(config, f)
    
    try:
        # Test create_arbitrage_system
        with mock.patch("arbitrage_bot.core.arbitrage.factory.create_discovery_manager", 
                       return_value=MockDiscoveryManager()), \
             mock.patch("arbitrage_bot.core.arbitrage.factory.create_execution_manager", 
                       return_value=MockExecutionManager()), \
             mock.patch("arbitrage_bot.core.arbitrage.factory.create_analytics_manager", 
                       return_value=MockAnalyticsManager()), \
             mock.patch("arbitrage_bot.core.arbitrage.factory.create_market_data_provider", 
                       return_value=MockMarketDataProvider()):
            
            arbitrage_system = await create_arbitrage_system(config)
            assert isinstance(arbitrage_system, BaseArbitrageSystem)
            assert not arbitrage_system.is_running
        
        # Test create_arbitrage_system_from_config
        with mock.patch("arbitrage_bot.core.arbitrage.factory.create_discovery_manager", 
                       return_value=MockDiscoveryManager()), \
             mock.patch("arbitrage_bot.core.arbitrage.factory.create_execution_manager", 
                       return_value=MockExecutionManager()), \
             mock.patch("arbitrage_bot.core.arbitrage.factory.create_analytics_manager", 
                       return_value=MockAnalyticsManager()), \
             mock.patch("arbitrage_bot.core.arbitrage.factory.create_market_data_provider", 
                       return_value=MockMarketDataProvider()):
            
            arbitrage_system = await create_arbitrage_system_from_config(temp_config_path)
            assert isinstance(arbitrage_system, BaseArbitrageSystem)
            assert not arbitrage_system.is_running
        
        # Test legacy mode
        with mock.patch("arbitrage_bot.core.arbitrage.factory.create_legacy_discovery_manager", 
                       return_value=MockDiscoveryManager()), \
             mock.patch("arbitrage_bot.core.arbitrage.factory.create_legacy_execution_manager", 
                       return_value=MockExecutionManager()), \
             mock.patch("arbitrage_bot.core.arbitrage.factory.create_legacy_analytics_manager", 
                       return_value=MockAnalyticsManager()), \
             mock.patch("arbitrage_bot.core.arbitrage.factory.create_legacy_market_data_provider", 
                       return_value=MockMarketDataProvider()):
            
            arbitrage_system = await create_arbitrage_system(config, use_legacy=True)
            assert isinstance(arbitrage_system, BaseArbitrageSystem)
            assert not arbitrage_system.is_running
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_config_path):
            os.remove(temp_config_path)


if __name__ == "__main__":
    """Run tests directly."""
    asyncio.run(test_arbitrage_system_creation())
    asyncio.run(test_arbitrage_system_lifecycle())
    asyncio.run(test_factory_functions())
    print("All tests passed!")