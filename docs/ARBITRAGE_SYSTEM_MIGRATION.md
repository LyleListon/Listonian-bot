# Arbitrage System Migration Guide

This document provides guidance for migrating from the legacy arbitrage monitoring system to the new refactored architecture.

## Table of Contents

1. [Overview](#overview)
2. [Key Architecture Changes](#key-architecture-changes)
3. [Migration Process](#migration-process)
4. [Configuration Changes](#configuration-changes)
5. [Code Migration Examples](#code-migration-examples)
6. [Troubleshooting](#troubleshooting)

## Overview

The arbitrage system has been refactored to improve maintainability, extensibility, and performance. The new architecture provides:

- Clear separation of concerns with well-defined interfaces
- Enhanced testability and reliability
- Improved error handling and resource management
- Better extensibility for adding new strategies and components
- Comprehensive performance analytics
- Standardized communication between components

## Key Architecture Changes

### Legacy Architecture (ArbitrageMonitor)

The legacy system centered around the `ArbitrageMonitor` class with intermingled responsibilities:

```
ArbitrageMonitor
├── Discovery Logic
├── Execution Logic
├── Transaction Monitoring
├── Analytics
└── Price Monitoring
```

### New Architecture

The new system separates responsibilities into distinct components:

```
BaseArbitrageSystem
├── OpportunityDiscoveryManager
│   ├── Detectors (PathFinder, Triangular, etc.)
│   └── Validators
├── ExecutionManager
│   ├── Execution Strategies
│   └── Transaction Monitors
├── AnalyticsManager
└── MarketDataProvider
```

## Migration Process

The migration can be performed incrementally using the following steps:

1. **Preparation Phase**
   - Review existing code and dependencies
   - Ensure all tests for existing functionality pass
   - Make a backup of production settings

2. **Dual Operation Phase**
   - The system supports both legacy and new architectures simultaneously
   - Use command-line flag `--legacy` to run the legacy system
   - Test the new system thoroughly before full migration

3. **Complete Migration**
   - After validating the new system, migrate all dependent code
   - Update configurations to use new features
   - Remove legacy code references

## Configuration Changes

### Legacy Configuration

The legacy system used a flat configuration structure:

```json
{
  "arbitrage": {
    "min_profit_threshold": 0.001,
    "max_opportunities": 5,
    "execution_interval": 60
  }
}
```

### New Configuration

The new system uses a more structured configuration:

```json
{
  "arbitrage": {
    "strategies": ["triangular", "cross_dex", "flash_loan"],
    "auto_execute": true,
    "discovery_interval_seconds": 30,
    "execution_interval_seconds": 60,
    "min_profit_threshold_eth": 0.005,
    "max_opportunities_per_cycle": 5,
    "min_confidence_threshold": 0.7,
    "market_update_interval_seconds": 30
  },
  "analytics": {
    "enabled": true,
    "analytics_data_dir": "data/analytics",
    "persist_interval_seconds": 300,
    "auto_persist": true
  },
  "monitoring": {
    "enabled": true,
    "alert_threshold_profit_eth": 0.01,
    "performance_log_interval_seconds": 3600
  }
}
```

## Code Migration Examples

### Using the Legacy System

```python
from arbitrage_bot.core.arbitrage_monitor import ArbitrageMonitor
from arbitrage_bot.utils.config_loader import load_config
from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.core.dex.dex_manager import create_dex_manager

# Load configuration
config = load_config("configs/production_config.json")

# Create web3 manager
web3_manager = await create_web3_manager(config)

# Create dex manager
dex_manager = await create_dex_manager(web3_manager, config)

# Create arbitrage monitor
arbitrage_monitor = ArbitrageMonitor(
    dex_manager=dex_manager,
    web3_manager=web3_manager,
    config=config
)

# Start monitoring
await arbitrage_monitor.start()

# Get opportunities
opportunities = await arbitrage_monitor.detect_opportunities()

# Execute opportunity
result = await arbitrage_monitor.execute_arbitrage(opportunities[0])
```

### Using the New System

```python
from arbitrage_bot.core.arbitrage.factory import create_arbitrage_system_from_config

# Create arbitrage system from config
arbitrage_system = await create_arbitrage_system_from_config("configs/production_config.json")

# Start the system
await arbitrage_system.start()

# Discover opportunities
opportunities = await arbitrage_system.discover_opportunities(max_results=5)

# Execute opportunity
execution_result = await arbitrage_system.execute_opportunity(
    opportunity=opportunities[0],
    strategy_id="standard"  # Use the standard strategy
)

# Get performance metrics
metrics = await arbitrage_system.get_performance_metrics()
```

### Custom Detector Implementation

```python
from arbitrage_bot.core.arbitrage.interfaces import OpportunityDetector
from arbitrage_bot.core.arbitrage.models import ArbitrageOpportunity, StrategyType

class CustomDetector(OpportunityDetector):
    """Custom opportunity detector implementation."""
    
    async def detect_opportunities(self, market_condition, **kwargs):
        """Detect arbitrage opportunities."""
        # Implementation logic here
        opportunities = []
        
        # Add detected opportunities
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

## Troubleshooting

### Common Migration Issues

1. **Configuration Mismatches**
   - **Problem**: Missing or mismatched configuration fields
   - **Solution**: Compare your configuration against the `test_config.json` example file

2. **Import Errors**
   - **Problem**: References to moved or renamed modules
   - **Solution**: Update imports to reference the new module structure

3. **Interface Compatibility**
   - **Problem**: Custom implementations not matching new interfaces
   - **Solution**: Review the Protocol definitions in `interfaces.py` and ensure implementations conform

4. **Missing Dependencies**
   - **Problem**: New system requires additional dependencies
   - **Solution**: Check your environment against the requirements.txt file

### Logging and Debugging

The new system has enhanced logging capabilities. Set the log level in your configuration:

```json
{
  "general": {
    "log_level": "DEBUG"
  }
}
```

Log files are stored in the `logs/` directory and include component-specific logs.

### Performance Issues

If you encounter performance issues:

1. Check the `performance_metrics` log for bottlenecks
2. Review cache TTL settings if price fetching is slow
3. Adjust the discovery and execution intervals to balance CPU usage
4. Consider enabling the analytics persistence for offline analysis

## Support

For additional support:

- Review the complete documentation in the `docs/` directory
- Check the test files for example usage
- Update bug reports with full logs and configuration details (sanitized)
