# CI/CD Setup

## Overview
The project uses GitHub Actions for continuous integration and deployment, with a focus on:
- Code quality (linting, formatting)
- Type checking
- Test coverage
- Automated deployment

## Test Infrastructure

### Test Organization
- `tests/test_core.py`: Core functionality tests
- `tests/conftest.py`: Shared fixtures and configurations
- `pytest.ini`: Test configuration and coverage settings

### Test Categories
1. **Unit Tests**
   - Core component tests
   - Utility function tests
   - Configuration tests

2. **Integration Tests** (marked with @pytest.mark.integration)
   - Web3 connection tests
   - MCP server integration tests
   - Database interaction tests

3. **Performance Tests** (marked with @pytest.mark.slow)
   - Trade execution timing
   - System monitoring
   - Network latency tests

## CI Pipeline Steps

1. **Setup**
   - Python environment setup
   - Dependency installation
   - Cache configuration

2. **Code Quality**
   - Black formatting check
   - Flake8 linting
   - MyPy type checking

3. **Testing**
   - Unit tests
   - Integration tests
   - Coverage reporting

4. **Deployment** (main branch only)
   - Environment validation and configuration
   - Load mainnet deployment configuration
   - Execute deployment script
   - Monitor deployment stability (5 minutes)
   - Verify process health
   - Upload deployment logs

## Required Secrets

The following secrets must be configured in GitHub repository settings:

1. `RPC_URL`: Ethereum mainnet RPC endpoint URL
2. `PRIVATE_KEY`: Deployment wallet private key

## Deployment Process

1. **Environment Setup**
   - Sets required environment variables from secrets
   - Configures network and trading parameters
   - Creates necessary directories

2. **Configuration**
   - Loads mainnet deployment configuration
   - Sets up environment variables
   - Initializes database

3. **Process Management**
   - Starts monitoring service
   - Launches web dashboard
   - Initiates arbitrage bot
   - Monitors process health

4. **Verification**
   - Checks process status
   - Verifies PID file existence
   - Monitors logs for errors
   - Uploads deployment artifacts

## Configuration Files

### GitHub Actions (`ci.yml`)
```yaml
name: Arbitrage Bot CI/CD
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
...
```

### Pytest Configuration (`pytest.ini`)
```ini
[pytest]
markers =
    integration: marks tests requiring blockchain connection
    slow: marks tests that are particularly slow
    mcp: marks tests requiring MCP servers
...
```

### Coverage Configuration (`setup.cfg`)
```ini
[coverage:run]
source = arbitrage_bot
omit = */tests/*
...
```

## Running Tests Locally

1. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Run all tests:
   ```bash
   pytest
   ```

3. Run specific test categories:
   ```bash
   pytest -m "not integration"  # Skip integration tests
   pytest -m slow  # Run only slow tests
   pytest -m "not mcp"  # Skip MCP-dependent tests
   ```

4. Generate coverage report:
   ```bash
   pytest --cov=arbitrage_bot --cov-report=html
   ```

## Common Issues and Solutions

### Test Database Issues
- Ensure test database is properly cleaned up
- Use test fixtures for database operations
- Avoid modifying production database in tests

### Web3 Connection Issues
- Use mock Web3 provider in tests
- Handle network timeouts gracefully
- Test with local blockchain when possible

### MCP Server Integration
- Use mock MCP servers in unit tests
- Test error handling for server failures
- Validate response formats

## Adding New Tests

1. Create test file in `tests/` directory
2. Import fixtures from `conftest.py`
3. Use appropriate markers for test categories
4. Ensure proper mocking of external dependencies
5. Add coverage for error cases

## Best Practices

1. **Test Independence**
   - Each test should be independent
   - Use fixtures for setup/teardown
   - Avoid test interdependencies

2. **Mock External Services**
   - Use fixtures for Web3, MCP servers
   - Mock network calls
   - Control test environment

3. **Coverage Goals**
   - Maintain 80% minimum coverage
   - Focus on critical paths
   - Document uncovered code

4. **Documentation**
   - Document test purposes
   - Explain complex fixtures
   - Note any special requirements
