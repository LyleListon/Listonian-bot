# Listonian Bot Testing Guide

This guide provides comprehensive information about testing the Listonian Bot codebase. It covers the testing philosophy, different types of tests, and practical examples.

## Testing Philosophy

The Listonian Bot project follows these testing principles:

1. **Test-Driven Development (TDD)**: Write tests before implementing features
2. **Comprehensive Coverage**: Aim for high test coverage across all components
3. **Fast Feedback**: Tests should run quickly to provide immediate feedback
4. **Isolation**: Tests should be independent and not affect each other
5. **Realistic Scenarios**: Tests should reflect real-world usage patterns
6. **Continuous Testing**: Tests run automatically on every code change

## Testing Pyramid

We follow the testing pyramid approach with:

1. **Unit Tests**: Many small, focused tests for individual functions and classes
2. **Integration Tests**: Medium number of tests for component interactions
3. **End-to-End Tests**: Few comprehensive tests for complete workflows
4. **Performance Tests**: Specialized tests for performance characteristics

## Test Types

### Unit Tests

Unit tests verify the behavior of individual functions, methods, or classes in isolation.

**Characteristics:**
- Fast execution (milliseconds)
- No external dependencies (databases, APIs, etc.)
- Mock or stub all dependencies
- Focus on a single unit of functionality
- High coverage of code paths

**Example:**

```python
# arbitrage_bot/core/arbitrage/profit_calculator.py
def calculate_profit(input_amount, output_amount, gas_cost, flash_loan_fee=0):
    """Calculate the net profit from a trade.
    
    Args:
        input_amount (float): The amount of tokens used as input
        output_amount (float): The amount of tokens received as output
        gas_cost (float): The gas cost in the same unit as input_amount
        flash_loan_fee (float, optional): The flash loan fee if applicable
        
    Returns:
        float: The net profit (output_amount - input_amount - gas_cost - flash_loan_fee)
    """
    return output_amount - input_amount - gas_cost - flash_loan_fee
```

```python
# tests/unit/core/arbitrage/test_profit_calculator.py
import pytest
from arbitrage_bot.core.arbitrage.profit_calculator import calculate_profit

def test_calculate_profit_positive():
    # Arrange
    input_amount = 1.0
    output_amount = 1.05
    gas_cost = 0.01
    
    # Act
    profit = calculate_profit(input_amount, output_amount, gas_cost)
    
    # Assert
    assert profit == 0.04
    assert profit > 0

def test_calculate_profit_negative():
    # Arrange
    input_amount = 1.0
    output_amount = 1.01
    gas_cost = 0.02
    
    # Act
    profit = calculate_profit(input_amount, output_amount, gas_cost)
    
    # Assert
    assert profit == -0.01
    assert profit < 0

def test_calculate_profit_with_flash_loan_fee():
    # Arrange
    input_amount = 1.0
    output_amount = 1.05
    gas_cost = 0.01
    flash_loan_fee = 0.003
    
    # Act
    profit = calculate_profit(input_amount, output_amount, gas_cost, flash_loan_fee)
    
    # Assert
    assert profit == 0.037
    assert profit > 0
```

### Integration Tests

Integration tests verify that different components work together correctly.

**Characteristics:**
- Medium execution speed (seconds)
- Test interactions between components
- May use test doubles for external systems
- Focus on component interfaces
- Verify correct data flow between components

**Example:**

```python
# tests/integration/test_arbitrage_workflow.py
import pytest
from unittest.mock import Mock, patch
from arbitrage_bot.core.arbitrage.arbitrage_engine import ArbitrageEngine
from arbitrage_bot.core.market.market_monitor import MarketMonitor
from arbitrage_bot.common.events.event_bus import EventBus

@pytest.fixture
def event_bus():
    return EventBus()

@pytest.fixture
def market_data():
    return {
        "pairs": [
            {
                "dex": "uniswap_v3",
                "base_token": "ETH",
                "quote_token": "USDC",
                "price": 3500.0,
                "liquidity": 1000000.0
            },
            {
                "dex": "sushiswap",
                "base_token": "ETH",
                "quote_token": "USDC",
                "price": 3520.0,
                "liquidity": 800000.0
            }
        ]
    }

@pytest.fixture
def mock_market_monitor(market_data):
    monitor = Mock(spec=MarketMonitor)
    monitor.get_market_data.return_value = market_data
    return monitor

@pytest.fixture
def arbitrage_engine(event_bus, mock_market_monitor):
    # Create real dependencies with test configurations
    path_finder = PathFinder(max_path_length=3)
    profit_calculator = ProfitCalculator(min_profit_threshold=0.1)
    risk_analyzer = RiskAnalyzer(max_risk_score=3)
    
    # Create the arbitrage engine with real and mock dependencies
    engine = ArbitrageEngine(
        path_finder=path_finder,
        profit_calculator=profit_calculator,
        risk_analyzer=risk_analyzer,
        event_bus=event_bus
    )
    
    # Inject the mock market monitor
    engine.market_monitor = mock_market_monitor
    
    return engine

def test_opportunity_detection(arbitrage_engine, event_bus):
    # Arrange
    opportunity_detected = False
    
    def on_opportunity_detected(event):
        nonlocal opportunity_detected
        opportunity_detected = True
        assert event.data["profit_percentage"] > 0
        assert "ETH" in event.data["path"]
        assert "USDC" in event.data["path"]
    
    event_bus.subscribe("opportunity_detected", on_opportunity_detected)
    
    # Act
    arbitrage_engine.find_opportunities()
    
    # Assert
    assert opportunity_detected
```

### End-to-End Tests

End-to-end tests verify complete workflows from start to finish.

**Characteristics:**
- Slower execution (minutes)
- Test the entire system
- Use test environments for external systems
- Focus on user scenarios
- Verify system behavior as a whole

**Example:**

```python
# tests/e2e/test_arbitrage_execution.py
import pytest
import time
from arbitrage_bot.main import ArbitrageBot
from arbitrage_bot.common.config.config_loader import load_config

@pytest.fixture
def config():
    # Load test configuration
    return load_config(environment="test")

@pytest.fixture
def bot(config):
    # Initialize the bot with test configuration
    bot = ArbitrageBot(config)
    bot.start(block=False)
    yield bot
    bot.stop()

@pytest.mark.e2e
def test_arbitrage_execution(bot):
    # Arrange
    # Wait for the bot to initialize and connect to services
    time.sleep(5)
    
    # Get initial metrics
    initial_metrics = bot.get_metrics()
    initial_trade_count = initial_metrics["trading"]["total_trades"]
    
    # Act
    # Create a known arbitrage opportunity in the test environment
    # This could involve manipulating test DEX contracts or mock services
    create_test_arbitrage_opportunity()
    
    # Wait for the bot to detect and execute the trade
    # This might take some time depending on the system
    timeout = 60  # seconds
    start_time = time.time()
    trade_executed = False
    
    while time.time() - start_time < timeout and not trade_executed:
        current_metrics = bot.get_metrics()
        if current_metrics["trading"]["total_trades"] > initial_trade_count:
            trade_executed = True
        time.sleep(1)
    
    # Assert
    assert trade_executed, "Trade was not executed within the timeout period"
    
    # Get the latest trade
    trades = bot.get_recent_trades(limit=1)
    latest_trade = trades[0]
    
    # Verify trade details
    assert latest_trade["status"] == "success"
    assert latest_trade["profit_usd"] > 0
    assert latest_trade["transaction_hash"] is not None
```

### Performance Tests

Performance tests verify that the system meets performance requirements.

**Characteristics:**
- Focus on speed, throughput, and resource usage
- Run in isolated environments
- Measure specific performance metrics
- Compare against baseline performance
- Identify performance bottlenecks

**Example:**

```python
# tests/performance/test_arbitrage_engine_performance.py
import pytest
import time
import statistics
from arbitrage_bot.core.arbitrage.arbitrage_engine import ArbitrageEngine

@pytest.fixture
def large_market_data():
    # Generate a large dataset with many trading pairs
    pairs = []
    for i in range(1000):
        pairs.append({
            "dex": "uniswap_v3",
            "base_token": f"TOKEN_{i % 100}",
            "quote_token": f"TOKEN_{(i + 1) % 100}",
            "price": 100.0 + (i % 10),
            "liquidity": 1000000.0
        })
    return {"pairs": pairs}

@pytest.fixture
def arbitrage_engine(large_market_data):
    # Create the arbitrage engine with performance-focused configuration
    engine = create_test_arbitrage_engine()
    engine.market_monitor.get_market_data.return_value = large_market_data
    return engine

@pytest.mark.performance
def test_opportunity_finding_performance(arbitrage_engine):
    # Arrange
    num_runs = 10
    execution_times = []
    
    # Act
    for _ in range(num_runs):
        start_time = time.time()
        opportunities = arbitrage_engine.find_opportunities()
        end_time = time.time()
        execution_times.append(end_time - start_time)
    
    # Assert
    avg_execution_time = statistics.mean(execution_times)
    max_execution_time = max(execution_times)
    
    print(f"Average execution time: {avg_execution_time:.4f} seconds")
    print(f"Maximum execution time: {max_execution_time:.4f} seconds")
    
    # Performance requirements
    assert avg_execution_time < 0.5, "Average execution time exceeds 500ms"
    assert max_execution_time < 1.0, "Maximum execution time exceeds 1 second"
```

## Mocking and Test Doubles

We use various test doubles to isolate the code being tested:

### Mocks

Mocks are objects that simulate the behavior of real objects and verify interactions.

```python
from unittest.mock import Mock, call

# Create a mock
mock_transaction_manager = Mock()

# Set return values
mock_transaction_manager.execute_trade.return_value = {
    "status": "success",
    "transaction_hash": "0x1234567890abcdef"
}

# Use the mock
result = mock_transaction_manager.execute_trade(trade_data)

# Verify interactions
mock_transaction_manager.execute_trade.assert_called_once_with(trade_data)
```

### Stubs

Stubs provide canned answers to calls made during the test.

```python
class PriceStub:
    def get_token_price(self, token_address):
        # Hardcoded prices for testing
        prices = {
            "0x123": 3500.0,  # ETH
            "0x456": 1.0,     # USDC
            "0x789": 50000.0  # BTC
        }
        return prices.get(token_address, 0.0)
```

### Fakes

Fakes are lightweight implementations of interfaces used in production.

```python
class InMemoryRepository:
    """A fake repository that stores data in memory."""
    
    def __init__(self):
        self.data = {}
    
    def save(self, key, value):
        self.data[key] = value
        return True
    
    def get(self, key):
        return self.data.get(key)
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
            return True
        return False
```

## Testing Tools

### pytest

We use pytest as our primary testing framework.

**Key features:**
- Fixture support for test setup and teardown
- Parameterized tests
- Powerful assertion introspection
- Plugin ecosystem

**Example:**

```python
import pytest

@pytest.fixture
def wallet():
    return {
        "address": "0x1234567890abcdef",
        "balance": 10.0
    }

@pytest.mark.parametrize("amount,expected", [
    (1.0, True),   # Sufficient balance
    (10.0, True),  # Exact balance
    (10.1, False), # Insufficient balance
])
def test_has_sufficient_balance(wallet, amount, expected):
    result = has_sufficient_balance(wallet, amount)
    assert result == expected
```

### pytest-mock

We use pytest-mock for mocking in tests.

**Example:**

```python
def test_execute_trade(mocker):
    # Mock dependencies
    mock_transaction_manager = mocker.patch("arbitrage_bot.core.transaction.transaction_manager.TransactionManager")
    mock_transaction_manager.return_value.execute_trade.return_value = {
        "status": "success",
        "transaction_hash": "0x1234567890abcdef"
    }
    
    # Test the function that uses the transaction manager
    result = execute_arbitrage_opportunity(opportunity_data)
    
    # Assertions
    assert result["status"] == "success"
    mock_transaction_manager.return_value.execute_trade.assert_called_once()
```

### pytest-cov

We use pytest-cov for measuring test coverage.

**Example:**

```bash
pytest --cov=arbitrage_bot --cov-report=term --cov-report=html
```

### pytest-benchmark

We use pytest-benchmark for performance testing.

**Example:**

```python
def test_path_finding_performance(benchmark):
    # Setup
    graph = create_test_graph()
    path_finder = PathFinder(graph)
    
    # Benchmark the function
    result = benchmark(path_finder.find_paths, "TOKEN_A", "TOKEN_B", max_length=3)
    
    # Assertions
    assert len(result) > 0
```

## Test Organization

Tests are organized to mirror the structure of the main codebase:

```
tests/
├── unit/                  # Unit tests
│   ├── core/              # Tests for core components
│   ├── integration/       # Tests for integrations
│   ├── api/               # Tests for API
│   └── ...
├── integration/           # Integration tests
├── e2e/                   # End-to-end tests
├── performance/           # Performance tests
├── conftest.py            # Shared fixtures
└── ...
```

## Test Fixtures

We use fixtures for test setup and teardown:

```python
# tests/conftest.py
import pytest
from arbitrage_bot.common.events.event_bus import EventBus
from arbitrage_bot.common.config.config_loader import load_config

@pytest.fixture(scope="session")
def test_config():
    """Load test configuration once per test session."""
    return load_config(environment="test")

@pytest.fixture
def event_bus():
    """Create a new event bus for each test."""
    return EventBus()

@pytest.fixture
def mock_market_data():
    """Provide mock market data for tests."""
    return {
        "pairs": [
            {
                "dex": "uniswap_v3",
                "base_token": "ETH",
                "quote_token": "USDC",
                "price": 3500.0,
                "liquidity": 1000000.0
            },
            {
                "dex": "sushiswap",
                "base_token": "ETH",
                "quote_token": "USDC",
                "price": 3520.0,
                "liquidity": 800000.0
            }
        ]
    }
```

## Parameterized Tests

We use parameterized tests to test multiple scenarios:

```python
import pytest
from arbitrage_bot.core.arbitrage.profit_calculator import calculate_profit

@pytest.mark.parametrize("input_amount,output_amount,gas_cost,flash_loan_fee,expected_profit", [
    (1.0, 1.05, 0.01, 0.0, 0.04),    # Profitable trade without flash loan
    (1.0, 1.05, 0.01, 0.003, 0.037), # Profitable trade with flash loan
    (1.0, 1.01, 0.02, 0.0, -0.01),   # Unprofitable trade due to gas
    (1.0, 1.02, 0.01, 0.02, -0.01),  # Unprofitable trade due to flash loan fee
])
def test_calculate_profit_scenarios(input_amount, output_amount, gas_cost, flash_loan_fee, expected_profit):
    profit = calculate_profit(input_amount, output_amount, gas_cost, flash_loan_fee)
    assert profit == pytest.approx(expected_profit, abs=1e-6)
```

## Test Tags

We use markers to categorize tests:

```python
# In tests/conftest.py
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: mark a test as a unit test")
    config.addinivalue_line("markers", "integration: mark a test as an integration test")
    config.addinivalue_line("markers", "e2e: mark a test as an end-to-end test")
    config.addinivalue_line("markers", "performance: mark a test as a performance test")
    config.addinivalue_line("markers", "slow: mark a test as slow")

# In a test file
@pytest.mark.unit
def test_something_fast():
    pass

@pytest.mark.slow
def test_something_slow():
    pass
```

To run tests with specific markers:

```bash
pytest -m "unit and not slow"
pytest -m "integration or e2e"
```

## Continuous Integration

Tests are automatically run in CI pipelines:

1. **Pull Request Checks**: All tests run when a PR is created or updated
2. **Main Branch Checks**: All tests run when code is merged to main
3. **Nightly Builds**: Slow tests run nightly

## Test Data Management

We use several approaches for test data:

1. **Fixtures**: For small, reusable data
2. **Factory Functions**: For generating test data
3. **Test Data Files**: For complex or large datasets

Example factory function:

```python
def create_test_opportunity(profit_percentage=1.0, risk_score=1):
    """Create a test arbitrage opportunity."""
    return {
        "id": f"opp-{uuid.uuid4()}",
        "path": ["ETH", "USDC", "WBTC", "ETH"],
        "addresses": [
            "0x0000000000000000000000000000000000000000",
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
            "0x0000000000000000000000000000000000000000"
        ],
        "expected_profit_percentage": profit_percentage,
        "expected_profit_usd": 42.15 * profit_percentage,
        "input_amount": "1.0",
        "input_token": "ETH",
        "estimated_gas_cost_usd": 12.34,
        "net_profit_usd": (42.15 * profit_percentage) - 12.34,
        "dexes": ["uniswap_v3", "sushiswap", "uniswap_v3"],
        "timestamp": int(time.time()),
        "risk_score": risk_score
    }
```

## Property-Based Testing

We use property-based testing for complex algorithms:

```python
import hypothesis
from hypothesis import given, strategies as st

@given(
    input_amount=st.floats(min_value=0.1, max_value=1000.0),
    profit_percentage=st.floats(min_value=0.1, max_value=10.0),
    gas_cost=st.floats(min_value=0.01, max_value=50.0),
    flash_loan_fee_percentage=st.floats(min_value=0.0, max_value=0.5)
)
def test_profit_calculation_properties(input_amount, profit_percentage, gas_cost, flash_loan_fee_percentage):
    # Calculate expected values
    output_amount = input_amount * (1 + profit_percentage / 100)
    flash_loan_fee = input_amount * flash_loan_fee_percentage / 100
    
    # Calculate profit
    profit = calculate_profit(input_amount, output_amount, gas_cost, flash_loan_fee)
    
    # Properties that should hold
    if profit > 0:
        # If profitable, output must exceed input plus costs
        assert output_amount > input_amount + gas_cost + flash_loan_fee
    
    # Profit should increase if gas cost decreases
    lower_gas_profit = calculate_profit(input_amount, output_amount, gas_cost * 0.9, flash_loan_fee)
    assert lower_gas_profit > profit
    
    # Profit should decrease if flash loan fee increases
    higher_fee_profit = calculate_profit(input_amount, output_amount, gas_cost, flash_loan_fee * 1.1)
    assert higher_fee_profit < profit
```

## Test Environment Management

We use different environments for testing:

1. **Local**: For development and unit tests
2. **Test**: For integration and end-to-end tests
3. **Staging**: For performance and load tests

Environment configuration is managed through:

```python
# tests/conftest.py
import os
import pytest

@pytest.fixture(scope="session")
def test_environment():
    """Set up the test environment."""
    # Store original environment variables
    original_env = dict(os.environ)
    
    # Set test environment variables
    os.environ["ETHEREUM_RPC_URL"] = "http://localhost:8545"  # Local Ganache
    os.environ["BSC_RPC_URL"] = "http://localhost:8546"       # Local BSC node
    os.environ["WALLET_PRIVATE_KEY"] = "0x1234567890abcdef"   # Test private key
    os.environ["MIN_PROFIT_THRESHOLD"] = "0.1"                # Lower threshold for tests
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
```

## Running Tests

### Basic Test Run

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/core/arbitrage/test_profit_calculator.py

# Run specific test
pytest tests/unit/core/arbitrage/test_profit_calculator.py::test_calculate_profit_positive
```

### Test Selection

```bash
# Run unit tests only
pytest tests/unit/

# Run tests by marker
pytest -m "unit"
pytest -m "not slow"
pytest -m "integration and not slow"
```

### Test Output

```bash
# Verbose output
pytest -v

# Show print statements
pytest -s

# Show slowest tests
pytest --durations=10
```

### Coverage

```bash
# Generate coverage report
pytest --cov=arbitrage_bot

# Generate HTML coverage report
pytest --cov=arbitrage_bot --cov-report=html

# Generate XML coverage report for CI
pytest --cov=arbitrage_bot --cov-report=xml
```

## Best Practices

1. **Write Tests First**: Follow TDD principles
2. **Keep Tests Simple**: Each test should verify one thing
3. **Use Descriptive Names**: Test names should describe what they're testing
4. **Isolate Tests**: Tests should not depend on each other
5. **Clean Up**: Tests should clean up after themselves
6. **Don't Test Implementation Details**: Test behavior, not implementation
7. **Test Edge Cases**: Include boundary conditions and error cases
8. **Keep Tests Fast**: Slow tests discourage frequent testing
9. **Use Appropriate Assertions**: Use specific assertions for better error messages
10. **Maintain Tests**: Update tests when requirements change

## Conclusion

Testing is a critical part of the Listonian Bot development process. By following the guidelines in this document, we ensure that the system remains reliable, maintainable, and performant as it evolves.
