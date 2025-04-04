# Dashboard Integration Guide

## Overview

The Listonian-bot project includes two dashboard implementations:

1. **Legacy Dashboard** - Located in `arbitrage_bot/dashboard/`
2. **New Dashboard** - Located in `new_dashboard/`

This guide explains how these dashboards are integrated and how to avoid common issues with mismatched function and file names.

## Key Components

### MetricsService

There are two implementations of `MetricsService`:

1. **Legacy MetricsService** (`arbitrage_bot/dashboard/metrics_service.py`)
   - Constructor takes no parameters: `def __init__(self):`
   - Uses a collector-based approach with `register_collector`
   - Designed for the legacy dashboard

2. **New MetricsService** (`new_dashboard/dashboard/services/metrics_service.py`)
   - Constructor requires a memory_service parameter: `def __init__(self, memory_service: MemoryService):`
   - Integrates with MemoryService for state management
   - Designed for the new dashboard

### MemoryService

The `MemoryService` class (`new_dashboard/dashboard/services/memory_service.py`) provides:
- File-based state persistence
- Subscription mechanism for real-time updates
- Integration with MetricsService

### Component Integration

The `components.py` file creates production system components:
- Web3Manager
- EnhancedFlashLoanManager
- MarketAnalyzer
- ArbitrageExecutor
- MemoryBank

## Common Issues and Solutions

### 1. Conflicting Imports

**Issue**: Importing both versions of `MetricsService` causes conflicts.

```python
# Incorrect
from arbitrage_bot.dashboard.metrics_service import MetricsService
from ..dashboard.services.metrics_service import MetricsService  # via dependencies
```

**Solution**: Use only one version of `MetricsService`.

```python
# Correct
from .core.dependencies import register_services, lifespan  # This imports the new MetricsService
```

### 2. Incompatible Service Interfaces

**Issue**: The two `MetricsService` classes have different interfaces.

**Solution**: Ensure you're using the correct version for your context:
- For the new dashboard, use the version that takes a `memory_service` parameter
- For legacy code, use the version with no parameters

### 3. Incorrect Import Paths

**Issue**: Relative imports may not resolve correctly.

**Solution**: Use absolute imports when possible, or ensure relative paths are correct:

```python
# Correct relative import
from ..dashboard.services.memory_service import MemoryService
```

## Best Practices

1. **Single Source of Truth**: Prefer the new dashboard components when possible
2. **Dependency Injection**: Use the dependency system in `new_dashboard/core/dependencies.py`
3. **Service Registration**: Register services before use with `register_services()`
4. **Consistent Naming**: Maintain consistent naming across files and functions
5. **Documentation**: Document any deviations from standard patterns

## Migration Path

When working with dashboard components:

1. First check if the component exists in `new_dashboard/dashboard/services/`
2. If not, fall back to the legacy implementation in `arbitrage_bot/dashboard/`
3. Document any dependencies on legacy components for future migration

## Testing Dashboard Integration

To test that the dashboard integration is working correctly:

1. Start the dashboard with `python run_dashboard.py`
2. Check the logs for any import or initialization errors
3. Verify that metrics are being displayed correctly
4. Confirm that real-time updates are working

If you encounter issues, check the import paths and service initialization order.