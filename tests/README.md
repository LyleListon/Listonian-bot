# Arbitrage Bot Test Suite

This directory contains the test suite for the arbitrage bot project. The tests are organized to ensure comprehensive coverage of all system components and integration points.

## Directory Structure

```
tests/
├── core/                  # Core functionality tests
│   ├── test_async_core.py    # Async patterns and resource management
│   └── test_web3.py         # Web3 interaction tests
├── integration/           # Integration tests
│   ├── test_structure.py    # Project structure validation
│   ├── test_system_health.py # System health monitoring
│   └── test_swapbased_v3.py # SwapBased V3 integration
├── environment/          # Environment tests
│   └── check_python.py     # Python environment validation
├── data/                # Test data and fixtures
│   ├── monitoring_sample.json
│   ├── test_config.json
│   ├── dex_response_baseswap.json
│   └── sample_transactions.json
├── conftest.py         # Shared test fixtures
├── pytest.ini          # Test configuration
└── README.md           # This file
```

## Test Categories

### Core Tests
- Async functionality and patterns
- Thread safety and resource management
- Web3 interaction layer
- Cache and storage implementations

### Integration Tests
- DEX interactions
- System health monitoring
- Project structure validation
- Cross-component functionality

### Environment Tests
- Python version compatibility
- Required package availability
- System resource access
- Configuration validation

## Running Tests

### All Tests
```bash
pytest
```

### Specific Categories
```bash
# Run integration tests
pytest -m integration

# Run core tests
pytest -m core

# Run environment tests
pytest tests/environment/

# Run specific test file
pytest tests/integration/test_swapbased_v3.py
```

### With Coverage
```bash
pytest --cov=arbitrage_bot
```

## Test Data

The `data/` directory contains mock data and fixtures used across tests:

- `monitoring_sample.json`: Sample monitoring metrics
- `test_config.json`: Test configuration parameters
- `dex_response_baseswap.json`: Mock DEX API responses
- `sample_transactions.json`: Sample transaction data

## Writing Tests

### Best Practices

1. Use appropriate markers:
   ```python
   @pytest.mark.integration
   @pytest.mark.async_test
   async def test_feature():
       pass
   ```

2. Use shared fixtures from conftest.py:
   ```python
   async def test_feature(mock_web3_provider, test_config):
       pass
   ```

3. Follow naming conventions:
   - Test files: `test_*.py`
   - Test classes: `Test*`
   - Test functions: `test_*`

4. Include docstrings:
   ```python
   async def test_feature():
       """Test specific feature behavior.
       
       This test verifies:
       1. Initial state
       2. State transitions
       3. Final state
       """
   ```

### Mock Objects

Common mock objects are available in conftest.py:
- `mock_web3_provider`
- `mock_contract`
- `mock_pool`
- `mock_cache`
- `mock_db`

### Async Testing

Use pytest-asyncio for async tests:
```python
@pytest.mark.asyncio
async def test_async_feature():
    result = await async_function()
    assert result
```

## Test Configuration

See pytest.ini for:
- Test discovery rules
- Marker definitions
- Coverage settings
- Environment variables
- Custom settings

## Dependencies

Required packages for testing are in requirements-dev.txt:
```bash
pip install -r requirements-dev.txt
```

## Continuous Integration

Tests are run automatically on:
- Pull requests
- Main branch commits
- Release tags

See .github/workflows for CI configuration.