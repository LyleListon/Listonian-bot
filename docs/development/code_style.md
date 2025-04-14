# Listonian Bot Code Style Guide

This document outlines the coding standards and style guidelines for the Listonian Bot project. Following these guidelines ensures consistency across the codebase and makes it easier for developers to read, understand, and maintain the code.

## Table of Contents

1. [General Principles](#general-principles)
2. [Python Style Guidelines](#python-style-guidelines)
3. [JavaScript Style Guidelines](#javascript-style-guidelines)
4. [HTML/CSS Style Guidelines](#htmlcss-style-guidelines)
5. [Documentation Guidelines](#documentation-guidelines)
6. [Commit Message Guidelines](#commit-message-guidelines)
7. [Code Review Guidelines](#code-review-guidelines)
8. [Automated Style Checking](#automated-style-checking)

## General Principles

### Readability

- Write code for humans, not computers
- Prioritize readability over cleverness
- Use descriptive names for variables, functions, and classes
- Keep functions and methods small and focused
- Follow the principle of least surprise

### Consistency

- Follow established conventions
- Be consistent within the codebase
- When modifying existing code, follow the style of the surrounding code
- When in doubt, follow the style of similar code in the project

### Maintainability

- Write code that is easy to maintain
- Avoid premature optimization
- Follow the DRY (Don't Repeat Yourself) principle
- Follow the SOLID principles for object-oriented design
- Write code that is easy to test

## Python Style Guidelines

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some project-specific additions.

### Formatting

- Use 4 spaces for indentation (no tabs)
- Maximum line length is 88 characters (compatible with Black)
- Use blank lines to separate logical sections
- Use parentheses for line continuation
- Add a blank line at the end of each file

```python
# Good
def long_function_name(
    var_one, var_two, var_three,
    var_four
):
    print(var_one)

# Bad
def long_function_name(var_one, var_two, var_three,
    var_four):
    print(var_one)
```

### Imports

- Group imports in the following order:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library specific imports
- Separate each group with a blank line
- Sort imports alphabetically within each group
- Use absolute imports for external packages
- Use relative imports for internal modules

```python
# Standard library imports
import os
import sys
from datetime import datetime

# Third-party imports
import numpy as np
import pandas as pd
from web3 import Web3

# Local imports
from arbitrage_bot.core.arbitrage import ArbitrageEngine
from arbitrage_bot.utils.logging import setup_logger
```

### Naming Conventions

- Use `snake_case` for variables, functions, and methods
- Use `PascalCase` for classes
- Use `UPPER_CASE` for constants
- Use descriptive names that reflect the purpose

```python
# Variables
user_balance = 100.0
is_active = True

# Functions
def calculate_profit(input_amount, output_amount):
    return output_amount - input_amount

# Classes
class ArbitrageEngine:
    def find_opportunities(self):
        pass

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
```

### Function and Method Definitions

- Keep functions and methods small and focused
- Use type hints for parameters and return values
- Include docstrings for all public functions and methods
- Use default parameter values instead of overloading

```python
def calculate_profit(
    input_amount: float,
    output_amount: float,
    gas_cost: float = 0.0
) -> float:
    """Calculate the net profit from a trade.
    
    Args:
        input_amount: The amount of tokens used as input
        output_amount: The amount of tokens received as output
        gas_cost: The gas cost in the same unit as input_amount
        
    Returns:
        The net profit (output_amount - input_amount - gas_cost)
    """
    return output_amount - input_amount - gas_cost
```

### Class Definitions

- Follow the single responsibility principle
- Use class docstrings to describe the purpose of the class
- Define `__init__` method first, followed by special methods, then public methods, then private methods
- Use properties for computed attributes

```python
class Trade:
    """Represents a completed trade with its results."""
    
    def __init__(
        self,
        input_token: str,
        output_token: str,
        input_amount: float,
        output_amount: float,
        gas_cost: float
    ):
        """Initialize a new Trade.
        
        Args:
            input_token: Symbol of the input token
            output_token: Symbol of the output token
            input_amount: Amount of input token
            output_amount: Amount of output token
            gas_cost: Gas cost in input token units
        """
        self.input_token = input_token
        self.output_token = output_token
        self.input_amount = input_amount
        self.output_amount = output_amount
        self.gas_cost = gas_cost
        self.timestamp = datetime.now()
    
    def __str__(self) -> str:
        return f"Trade: {self.input_amount} {self.input_token} -> {self.output_amount} {self.output_token}"
    
    @property
    def profit(self) -> float:
        """Calculate the profit from this trade."""
        if self.input_token == self.output_token:
            return self.output_amount - self.input_amount - self.gas_cost
        return None  # Cannot calculate profit for different tokens
    
    def to_dict(self) -> dict:
        """Convert the trade to a dictionary."""
        return {
            "input_token": self.input_token,
            "output_token": self.output_token,
            "input_amount": self.input_amount,
            "output_amount": self.output_amount,
            "gas_cost": self.gas_cost,
            "timestamp": self.timestamp.isoformat(),
            "profit": self.profit
        }
```

### Comments and Docstrings

- Write docstrings for all public modules, functions, classes, and methods
- Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) for docstrings
- Use comments to explain "why", not "what" or "how"
- Keep comments up to date with the code

```python
def execute_trade(
    trade_data: dict,
    max_slippage: float = 0.01,
    deadline: int = None
) -> dict:
    """Execute a trade on the blockchain.
    
    This function prepares and submits a transaction to execute a trade
    based on the provided trade data. It handles slippage protection and
    transaction deadlines.
    
    Args:
        trade_data: Dictionary containing trade parameters
        max_slippage: Maximum allowed slippage as a decimal (default: 0.01 = 1%)
        deadline: Transaction deadline in Unix timestamp (default: 10 minutes from now)
    
    Returns:
        Dictionary with transaction details and status
    
    Raises:
        InsufficientBalanceError: If the wallet has insufficient balance
        TransactionFailedError: If the transaction fails to execute
    """
    # Default deadline is 10 minutes from now
    if deadline is None:
        deadline = int(time.time()) + 600
    
    # Implementation details...
```

### Error Handling

- Use exceptions for exceptional conditions
- Create custom exception classes for specific error cases
- Handle exceptions at the appropriate level
- Include context in exception messages

```python
class InsufficientBalanceError(Exception):
    """Raised when the wallet has insufficient balance for a transaction."""
    pass

class TransactionFailedError(Exception):
    """Raised when a transaction fails to execute."""
    pass

def check_balance(wallet_address: str, required_amount: float) -> bool:
    """Check if the wallet has sufficient balance.
    
    Args:
        wallet_address: The wallet address to check
        required_amount: The required amount
        
    Returns:
        True if the wallet has sufficient balance, False otherwise
        
    Raises:
        ConnectionError: If unable to connect to the blockchain
    """
    try:
        balance = get_wallet_balance(wallet_address)
        return balance >= required_amount
    except ConnectionError as e:
        # Re-raise with more context
        raise ConnectionError(f"Failed to check balance for {wallet_address}: {str(e)}")
```

### Testing

- Write tests for all code
- Use descriptive test names that explain what is being tested
- Follow the Arrange-Act-Assert pattern
- Keep tests independent and idempotent

```python
def test_calculate_profit_with_gas_cost():
    # Arrange
    input_amount = 1.0
    output_amount = 1.05
    gas_cost = 0.01
    
    # Act
    profit = calculate_profit(input_amount, output_amount, gas_cost)
    
    # Assert
    assert profit == 0.04
```

## JavaScript Style Guidelines

We follow the [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript) with some project-specific additions.

### Formatting

- Use 2 spaces for indentation (no tabs)
- Maximum line length is 100 characters
- Use semicolons at the end of statements
- Use single quotes for strings
- Add a blank line at the end of each file

```javascript
// Good
function calculateProfit(inputAmount, outputAmount, gasCost) {
  return outputAmount - inputAmount - gasCost;
}

// Bad
function calculateProfit(inputAmount, outputAmount, gasCost)
{
    return outputAmount - inputAmount - gasCost
}
```

### Variables

- Use `const` for variables that don't change
- Use `let` for variables that change
- Avoid using `var`
- Declare one variable per line
- Use descriptive variable names

```javascript
// Good
const MAX_RETRIES = 3;
let retryCount = 0;

// Bad
var x = 3, y = 4;
```

### Functions

- Use arrow functions for anonymous functions
- Use function declarations for named functions
- Use default parameters instead of conditionals
- Keep functions small and focused

```javascript
// Function declaration
function calculateProfit(inputAmount, outputAmount, gasCost = 0) {
  return outputAmount - inputAmount - gasCost;
}

// Arrow function
const trades = tradeHistory.map((trade) => ({
  profit: trade.outputAmount - trade.inputAmount - trade.gasCost,
  timestamp: trade.timestamp,
}));
```

### Classes

- Use ES6 class syntax
- Use constructor property promotion when possible
- Define methods using shorthand syntax
- Use getters and setters for computed properties

```javascript
class Trade {
  constructor(
    public inputToken: string,
    public outputToken: string,
    public inputAmount: number,
    public outputAmount: number,
    public gasCost: number
  ) {
    this.timestamp = new Date();
  }
  
  get profit() {
    if (this.inputToken === this.outputToken) {
      return this.outputAmount - this.inputAmount - this.gasCost;
    }
    return null; // Cannot calculate profit for different tokens
  }
  
  toJSON() {
    return {
      inputToken: this.inputToken,
      outputToken: this.outputToken,
      inputAmount: this.inputAmount,
      outputAmount: this.outputAmount,
      gasCost: this.gasCost,
      timestamp: this.timestamp.toISOString(),
      profit: this.profit,
    };
  }
}
```

### Imports and Exports

- Use ES6 import/export syntax
- Import only what you need
- Group imports by type
- Export at the end of the file

```javascript
// Imports
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { formatCurrency, formatPercentage } from '../utils/formatters';

// Component definition
function ProfitDisplay({ profit, percentage }) {
  // Implementation...
}

// PropTypes
ProfitDisplay.propTypes = {
  profit: PropTypes.number.isRequired,
  percentage: PropTypes.number.isRequired,
};

// Export
export default ProfitDisplay;
```

### Async/Await

- Prefer async/await over promises
- Use try/catch blocks for error handling
- Avoid mixing async/await with .then()/.catch()

```javascript
async function fetchTradeHistory() {
  try {
    const response = await fetch('/api/trades');
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    const data = await response.json();
    return data.trades;
  } catch (error) {
    console.error('Failed to fetch trade history:', error);
    return [];
  }
}
```

## HTML/CSS Style Guidelines

### HTML

- Use HTML5 doctype
- Use lowercase for element names, attributes, and values
- Use double quotes for attribute values
- Use semantic HTML elements
- Include appropriate ARIA attributes for accessibility

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Listonian Bot Dashboard</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header>
    <h1>Listonian Bot Dashboard</h1>
    <nav aria-label="Main Navigation">
      <ul>
        <li><a href="#overview">Overview</a></li>
        <li><a href="#trades">Trades</a></li>
        <li><a href="#settings">Settings</a></li>
      </ul>
    </nav>
  </header>
  
  <main>
    <section id="overview">
      <h2>System Overview</h2>
      <!-- Content here -->
    </section>
  </main>
  
  <footer>
    <p>&copy; 2025 Listonian Bot</p>
  </footer>
  
  <script src="app.js"></script>
</body>
</html>
```

### CSS

- Use CSS variables for colors, fonts, and other repeated values
- Use a consistent naming convention (we use BEM)
- Use shorthand properties where appropriate
- Group related properties together
- Add comments for complex selectors or rules

```css
/* Variables */
:root {
  --primary-color: #3498db;
  --secondary-color: #2ecc71;
  --text-color: #333333;
  --background-color: #f5f5f5;
  --font-family: 'Roboto', sans-serif;
}

/* Base styles */
body {
  font-family: var(--font-family);
  color: var(--text-color);
  background-color: var(--background-color);
  line-height: 1.6;
  margin: 0;
  padding: 0;
}

/* BEM example */
.card {
  background-color: white;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 20px;
}

.card__title {
  font-size: 1.5rem;
  margin-top: 0;
  color: var(--primary-color);
}

.card__content {
  margin-bottom: 15px;
}

.card--highlighted {
  border-left: 4px solid var(--secondary-color);
}
```

## Documentation Guidelines

### Code Documentation

- Document all public APIs
- Keep documentation close to the code
- Update documentation when code changes
- Include examples where appropriate

### Project Documentation

- Use Markdown for documentation files
- Organize documentation in a logical structure
- Include a README.md file in each directory
- Keep documentation up to date with the code

### README Files

Each README.md should include:

1. Purpose of the module/directory
2. Installation/setup instructions (if applicable)
3. Usage examples
4. Dependencies
5. Contributing guidelines (or link to them)

Example:
```markdown
# Arbitrage Engine

The Arbitrage Engine is responsible for identifying profitable trading opportunities across multiple DEXs.

## Installation

```bash
pip install -e .
```

## Usage

```python
from arbitrage_bot.core.arbitrage import ArbitrageEngine

engine = ArbitrageEngine()
opportunities = engine.find_opportunities()
```

## Dependencies

- `networkx` for graph algorithms
- `web3` for blockchain interaction

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines on contributing to this module.
```

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: Code changes that neither fix a bug nor add a feature
- `perf`: Performance improvements
- `test`: Adding or correcting tests
- `chore`: Changes to the build process or auxiliary tools

Examples:
```
feat(arbitrage): add support for new DEX
fix(dashboard): correct profit calculation display
docs(api): update endpoint documentation
```

## Code Review Guidelines

### For Authors

- Keep pull requests small and focused
- Provide a clear description of the changes
- Link to relevant issues
- Respond to feedback promptly
- Be open to suggestions

### For Reviewers

- Be respectful and constructive
- Focus on the code, not the author
- Provide specific feedback
- Suggest alternatives when rejecting a solution
- Approve only when all issues are addressed

## Automated Style Checking

We use several tools to enforce code style:

### Python

- [Black](https://github.com/psf/black) for code formatting
- [isort](https://pycqa.github.io/isort/) for import sorting
- [flake8](https://flake8.pycqa.org/) for linting
- [mypy](http://mypy-lang.org/) for type checking

Configuration in `pyproject.toml`:
```toml
[tool.black]
line-length = 88
target-version = ['py39']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 88
multi_line_output = 3

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
```

### JavaScript

- [ESLint](https://eslint.org/) for linting
- [Prettier](https://prettier.io/) for code formatting

Configuration in `.eslintrc.js`:
```javascript
module.exports = {
  extends: ['airbnb', 'prettier'],
  plugins: ['prettier'],
  rules: {
    'prettier/prettier': ['error'],
    'react/jsx-filename-extension': [1, { extensions: ['.js', '.jsx'] }],
    'import/prefer-default-export': 'off',
  },
};
```

### Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to run style checks before commits:

Configuration in `.pre-commit-config.yaml`:
```yaml
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files

-   repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
    -   id: black

-   repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
    -   id: isort

-   repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
    -   id: flake8
        additional_dependencies: [flake8-docstrings]

-   repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
    -   id: mypy
        additional_dependencies: [types-requests]

-   repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.40.0
    hooks:
    -   id: eslint
        files: \.(js|jsx)$
        types: [file]
        additional_dependencies:
        -   eslint@8.40.0
        -   eslint-config-airbnb@19.0.4
        -   eslint-config-prettier@8.8.0
        -   eslint-plugin-import@2.27.5
        -   eslint-plugin-jsx-a11y@6.7.1
        -   eslint-plugin-prettier@4.2.1
        -   eslint-plugin-react@7.32.2
        -   prettier@2.8.8
```

## Conclusion

Following these style guidelines ensures consistency across the codebase and makes it easier for developers to read, understand, and maintain the code. If you have questions or suggestions about these guidelines, please open an issue or pull request.
