# Development Guide

## Development Environment

### IDE Setup
- VSCode (recommended)
- PyCharm (supported)
- Required extensions:
  * Python
  * Pylance
  * Black Formatter
  * isort
  * Git Lens

### Code Quality Tools
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Tools included:
- black (code formatting)
- isort (import sorting)
- pylint (linting)
- mypy (type checking)
- pytest (testing)
```

## Code Standards

### Python Style Guide
- Follow PEP 8
- Use Black formatting
- Maximum line length: 88 characters
- Use type hints
- Document all public APIs

### Import Organization
```python
# Standard library
import os
import sys
from typing import List, Optional

# Third-party packages
import numpy as np
import web3
from web3.types import Wei

# Local imports
from core.models import Opportunity
from core.utils import calculate_profit
```

### Documentation Standards
```python
def calculate_arbitrage(
    path: List[str],
    amounts: List[Wei],
    slippage: float = 0.005
) -> Optional[Opportunity]:
    """Calculate potential arbitrage opportunity.

    Args:
        path: List of token addresses in the arbitrage path
        amounts: List of token amounts to trade
        slippage: Maximum allowed slippage (default: 0.5%)

    Returns:
        Opportunity object if profitable, None otherwise

    Raises:
        ValueError: If path and amounts lengths don't match
    """
    # Implementation
```

## Project Structure

### Core Components
```
src/core/
├── blockchain/  # Blockchain interactions
├── dex/        # DEX integrations
├── models/     # Data structures
└── utils/      # Shared utilities
```

### Feature Development
1. Create feature branch
2. Implement changes
3. Add tests
4. Update documentation
5. Create pull request

## Development Workflow

### 1. Branch Management
```bash
# Create feature branch
git checkout -b feature/new-feature

# Keep branch updated
git fetch origin
git rebase origin/main
```

### 2. Development Cycle
```bash
# Activate environment
source venv/bin/activate

# Run tests during development
pytest tests/unit/
pytest tests/integration/

# Format code
black src/
isort src/

# Type checking
mypy src/
```

### 3. Pre-commit Checks
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Testing

### Unit Tests
```python
def test_calculate_profit():
    """Test profit calculation logic."""
    # Arrange
    amounts = [1000, 1100, 1050]
    gas_cost = 100
    
    # Act
    profit = calculate_profit(amounts, gas_cost)
    
    # Assert
    assert profit > 0
    assert profit == 50  # Expected profit
```

### Integration Tests
```python
@pytest.mark.integration
async def test_dex_integration():
    """Test DEX interaction."""
    # Setup
    dex = BaseSwap(web3_provider)
    
    # Execute
    price = await dex.get_price("WETH", "USDC")
    
    # Verify
    assert price > 0
```

## Debugging

### Logging
```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Detailed information")
logger.info("General information")
logger.warning("Warning messages")
logger.error("Error messages")
```

### Debug Configuration
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```

## Performance

### Profiling
```bash
# Profile execution
python -m cProfile -o output.prof script.py

# Analyze results
snakeviz output.prof
```

### Optimization Tips
1. Use async/await for I/O operations
2. Implement caching where appropriate
3. Optimize database queries
4. Use connection pooling
5. Profile memory usage

## Deployment

### Local Testing
```bash
# Build distribution
python setup.py sdist bdist_wheel

# Test installation
pip install dist/package-name.whl
```

### Configuration
```bash
# Create local config
cp configs/default.json configs/local.json

# Edit configuration
nano configs/local.json
```

## Best Practices

### Code Organization
1. Keep functions small and focused
2. Use meaningful variable names
3. Comment complex logic
4. Write comprehensive tests
5. Document public APIs

### Error Handling
```python
try:
    result = await process_transaction()
except Web3Error as e:
    logger.error("Web3 error: %s", e)
    raise TransactionError(f"Failed to process: {e}")
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### Security
1. Never commit secrets
2. Validate all inputs
3. Use environment variables
4. Implement rate limiting
5. Follow security guidelines

Last Updated: 2025-02-10