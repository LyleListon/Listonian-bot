# Testing Framework

The testing framework for the Listonian Arbitrage Bot ensures code quality, reliability, and correctness. It includes unit tests, integration tests, and end-to-end tests for all components of the system.

## Testing Structure

The tests are organized by module and test type:

```
tests/
├── core/                 # Core module tests
│   ├── finance/          # Financial components tests
│   ├── memory/           # Memory management tests
│   └── web3/             # Web3 interaction tests
├── dex/                  # DEX integration tests
│   ├── uniswap/          # Uniswap-specific tests
│   ├── pancakeswap/      # PancakeSwap-specific tests
│   └── ...
├── integration/          # Integration module tests
├── utils/                # Utility function tests
├── conftest.py           # Pytest configuration and fixtures
└── test_integration.py   # System-wide integration tests
```

## Test Types

### Unit Tests

Unit tests verify the functionality of individual components in isolation:

```python
@pytest.mark.asyncio
async def test_calculate_profit(enhanced_manager):
    """Test profit calculation logic."""
    # Arrange
    token_pair = TokenPair(token0="0xToken1", token1="0xToken2")
    amount = 100 * 10**18
    prices = {"dex1": Decimal("1000"), "dex2": Decimal("1010")}
    
    # Act
    profit = await enhanced_manager._calculate_profit(token_pair, amount, prices)
    
    # Assert
    assert profit > 0, "Should calculate positive profit"
    assert isinstance(profit, int), "Profit should be an integer"
```

### Integration Tests

Integration tests verify that different components work together correctly:

```python
@pytest.mark.asyncio
async def test_flash_loan_execution(setup_components):
    """Test end-to-end flash loan execution."""
    flash_loan_manager, path_finder, flashbots_provider = setup_components
    
    # Arrange
    token_pair = TokenPair(token0="0xWETH", token1="0xUSDC")
    amount = 10 * 10**18
    prices = {"uniswap_v3": Decimal("1800"), "sushiswap": Decimal("1805")}
    
    # Act
    bundle = await flash_loan_manager.prepare_flash_loan_bundle(token_pair, amount, prices)
    result = await flashbots_provider.simulate_bundle(bundle.transactions)
    
    # Assert
    assert result["success"], "Bundle simulation should succeed"
    assert result["profitability"] > 0, "Bundle should be profitable"
```

### Mock Objects

The testing framework uses extensive mocking to isolate components and simulate external dependencies:

```python
@pytest.fixture
def mock_web3():
    """Mock Web3 client."""
    w3 = MagicMock()
    w3.eth = MagicMock()
    w3.eth.default_account = "0xTestAccount"
    w3.eth.gas_price = 50 * 10**9
    w3.to_checksum_address = lambda x: x
    return w3

@pytest.fixture
def mock_dex_manager():
    """Mock DEX manager."""
    manager = AsyncMock(spec=DexManager)
    manager.get_dex = AsyncMock(return_value=AsyncMock())
    manager.get_active_dexes = AsyncMock(return_value=[
        AsyncMock(name="MockDex1"),
        AsyncMock(name="MockDex2")
    ])
    return manager
```

## Running Tests

### Running All Tests

```bash
python -m pytest arbitrage_bot/tests/
```

### Running Specific Test Modules

```bash
# Run core module tests
python -m pytest arbitrage_bot/tests/core/

# Run DEX integration tests
python -m pytest arbitrage_bot/tests/dex/

# Run a specific test file
python -m pytest arbitrage_bot/tests/test_integration.py
```

### Test Options

```bash
# Run tests with verbose output
python -m pytest -v arbitrage_bot/tests/

# Run tests with code coverage
python -m pytest --cov=arbitrage_bot arbitrage_bot/tests/

# Generate HTML coverage report
python -m pytest --cov=arbitrage_bot --cov-report=html arbitrage_bot/tests/
```

## Fixtures

The testing framework provides several fixtures to simplify test setup:

### Web3 Fixtures

```python
@pytest.fixture
def web3_manager():
    """Create a Web3Manager instance for testing."""
    # Implementation
```

### DEX Fixtures

```python
@pytest.fixture
async def uniswap_v3():
    """Create a UniswapV3 instance for testing."""
    # Implementation
```

### Flash Loan Fixtures

```python
@pytest.fixture
async def enhanced_manager(web3_manager, flashbots_provider, memory_bank):
    """Create an EnhancedFlashLoanManager instance for testing."""
    # Implementation
```

## Testing Best Practices

1. **Isolation**: Each test should be independent and not rely on the state from other tests
2. **Mocking**: Use mocks for external dependencies to ensure tests are reliable and fast
3. **Async Testing**: Use `pytest_asyncio` for testing async functions
4. **Parameterization**: Use `@pytest.mark.parametrize` for testing multiple scenarios
5. **Fixtures**: Use fixtures for common setup and teardown
6. **Coverage**: Aim for high test coverage, especially for critical components

## Continuous Integration

The tests are automatically run in the CI/CD pipeline on every pull request and merge to the main branch. The pipeline includes:

1. Running all tests
2. Measuring code coverage
3. Static code analysis
4. Performance benchmarks

## Adding New Tests

When adding new functionality, follow these steps:

1. Create a new test file in the appropriate directory
2. Write tests for all public methods and edge cases
3. Use existing fixtures where possible
4. Run the tests to ensure they pass
5. Check code coverage to ensure adequate test coverage