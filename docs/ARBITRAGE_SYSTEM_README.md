# Listonian Arbitrage System

This document provides an overview of the refactored arbitrage system architecture and its components.

## Overview

The Listonian Arbitrage System is a modular, component-based system for discovering, validating, and executing arbitrage opportunities across multiple DEXs and blockchains. The system follows clean architecture principles with clear separation of concerns and well-defined interfaces.

## Key Components

![Arbitrage System Architecture](../static/images/arbitrage_system_architecture.png)

### Core Components

1. **BaseArbitrageSystem**
   - Central coordinator for the arbitrage workflow
   - Manages the interaction between discovery, execution, and analytics
   - Controls system lifecycle (start/stop)
   - Provides a unified interface for client code

2. **OpportunityDiscoveryManager**
   - Manages discovery and validation of arbitrage opportunities
   - Coordinates multiple detectors (e.g., PathFinder, Triangular)
   - Filters, ranks, and validates opportunities
   - Ensures opportunities meet minimum thresholds

3. **ExecutionManager**
   - Manages execution of arbitrage opportunities
   - Handles transaction monitoring and confirmation
   - Supports multiple execution strategies
   - Provides retry and error recovery mechanisms

4. **AnalyticsManager**
   - Records and analyzes arbitrage performance
   - Tracks historical opportunities and executions
   - Calculates performance metrics
   - Provides data for optimization

5. **MarketDataProvider**
   - Supplies current market conditions and prices
   - Monitors DEX liquidity and token prices
   - Notifies subscribers of significant market changes
   - Provides context for opportunity evaluation

### Adapters

The system includes adapters to integrate existing components with the new architecture:

1. **TriangularArbitrageDetector** - Adapts triangular arbitrage logic
2. **PathFinderDetector** - Adapts path finder for opportunity detection
3. **PathFinderValidator** - Adapts path finder for opportunity validation
4. **ArbitrageExecutorAdapter** - Adapts existing executor for the new system
5. **TransactionMonitorAdapter** - Adapts transaction monitoring functionality

## Key Interfaces

The system is built around these core interfaces (defined as Python Protocols):

```python
class OpportunityDetector(Protocol):
    """Interface for components that detect arbitrage opportunities."""
    async def detect_opportunities(self, market_condition, **kwargs): ...

class OpportunityValidator(Protocol):
    """Interface for components that validate arbitrage opportunities."""
    async def validate_opportunity(self, opportunity, market_condition, **kwargs): ...

class ExecutionStrategy(Protocol):
    """Interface for components that execute arbitrage opportunities."""
    async def execute_opportunity(self, opportunity, **kwargs): ...

class TransactionMonitor(Protocol):
    """Interface for components that monitor transaction execution."""
    async def monitor_transaction(self, transaction_hash, **kwargs): ...

class ArbitrageAnalytics(Protocol):
    """Interface for components that record and analyze arbitrage performance."""
    async def record_opportunity(self, opportunity): ...
    async def record_execution(self, execution_result): ...
    async def get_performance_metrics(self): ...
```

## Data Models

The system uses standardized data models for communication between components:

1. **ArbitrageOpportunity** - Represents a potential arbitrage opportunity
2. **ArbitrageRoute** - Represents the path of an arbitrage (sequence of trades)
3. **RouteStep** - Individual step in an arbitrage route
4. **ExecutionResult** - Result of an arbitrage execution
5. **MarketCondition** - Current market state and prices

## Getting Started

### Installation

```bash
pip install -e .
```

### Configuration

The system uses a JSON configuration file. Example:

```json
{
  "arbitrage": {
    "strategies": ["triangular", "cross_dex", "flash_loan"],
    "auto_execute": true,
    "min_profit_threshold_eth": 0.005,
    "max_opportunities_per_cycle": 5
  }
}
```

See `configs/test_config.json` for a complete example.

### Basic Usage

```python
from arbitrage_bot.core.arbitrage.factory import create_arbitrage_system_from_config

# Create system from config file
arbitrage_system = await create_arbitrage_system_from_config("configs/production_config.json")

# Start the system
await arbitrage_system.start()

# Discover opportunities
opportunities = await arbitrage_system.discover_opportunities(max_results=5)

# Execute opportunity
execution_result = await arbitrage_system.execute_opportunity(
    opportunity=opportunities[0],
    strategy_id="standard"
)

# Get performance metrics
metrics = await arbitrage_system.get_performance_metrics()

# Stop the system
await arbitrage_system.stop()
```

### Running Tests

```bash
# Run all tests
python -m tests.test_arbitrage_system

# Or use the batch file
run_arbitrage_test.bat
```

### Running in Production

```bash
# Run with new architecture
python -m arbitrage_bot.production

# Run with legacy architecture
python -m arbitrage_bot.production --legacy

# Or use the menu-driven batch file
run_arbitrage_system.bat
```

## Extending the System

### Creating a Custom Detector

```python
from arbitrage_bot.core.arbitrage.interfaces import OpportunityDetector
from arbitrage_bot.core.arbitrage.models import ArbitrageOpportunity, StrategyType

class CustomDetector(OpportunityDetector):
    """Custom opportunity detector."""
    
    async def detect_opportunities(self, market_condition, **kwargs):
        """Detect arbitrage opportunities."""
        # Implementation logic
        opportunities = []
        
        # Example opportunity creation
        opportunities.append(
            ArbitrageOpportunity(
                id=f"custom-{int(time.time())}",
                strategy_type=StrategyType.FLASH_LOAN,
                route=route,
                input_amount=input_amount,
                expected_output=expected_output,
                expected_profit=expected_profit,
                confidence_score=0.85
            )
        )
        
        return opportunities
```

### Registering Components

```python
# Create managers
discovery_manager = await create_opportunity_discovery_manager(market_data_provider, config)
execution_manager = await create_execution_manager(config)

# Create and register custom detector
custom_detector = CustomDetector(...)
await discovery_manager.register_detector(custom_detector, "custom")

# Create and register custom execution strategy
custom_strategy = CustomExecutionStrategy(...)
await execution_manager.register_strategy(custom_strategy, "custom")
```

## Performance Considerations

- Use batch operations for price fetching
- Implement caching for frequently accessed data
- Consider parallel processing for opportunity detection
- Monitor execution times for critical operations
- Use appropriate timeouts for network operations

## Troubleshooting

See [Migration Guide](ARBITRAGE_SYSTEM_MIGRATION.md) for common issues and solutions.

## Next Steps

To complete the implementation:

1. **Integration Tests**
   - Add comprehensive tests for the entire system
   - Test with different DEXs and token pairs
   - Validate profit calculations

2. **Dashboard Integration**
   - Update dashboard to display new metrics
   - Add visualization for opportunity discovery and execution

3. **Performance Optimization**
   - Optimize critical code paths
   - Implement advanced caching strategies
   - Add parallel processing for detectors

4. **Advanced Features**
   - Multi-path arbitrage optimization
   - Cross-chain arbitrage support
   - Advanced profit maximization

## Contributing

1. Follow the established architecture patterns
2. Ensure all code has comprehensive tests
3. Maintain backward compatibility where possible
4. Document all changes thoroughly

## License

See the LICENSE file for details.