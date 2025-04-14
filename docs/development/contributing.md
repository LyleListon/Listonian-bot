# Contributing to Listonian Bot

Thank you for your interest in contributing to the Listonian Bot project! This guide will help you get started with contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Environment](#development-environment)
4. [Coding Standards](#coding-standards)
5. [Git Workflow](#git-workflow)
6. [Pull Request Process](#pull-request-process)
7. [Testing](#testing)
8. [Documentation](#documentation)
9. [Issue Reporting](#issue-reporting)
10. [Feature Requests](#feature-requests)

## Code of Conduct

Our project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Node.js 14 or higher
- Git
- Basic knowledge of blockchain and DeFi concepts

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/Listonian-bot.git
   cd Listonian-bot
   ```
3. Add the original repository as an upstream remote:
   ```bash
   git remote add upstream https://github.com/original-owner/Listonian-bot.git
   ```

## Development Environment

### Setting Up

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. Install Node.js dependencies:
   ```bash
   npm install
   ```

4. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Environment Variables

Create a `.env.development` file in the root directory with the following variables:

```
# Blockchain Providers
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_API_KEY
BSC_RPC_URL=https://bsc-dataseed.binance.org/
BASE_RPC_URL=https://mainnet.base.org

# Wallet Configuration (Use a development wallet with test funds)
WALLET_PRIVATE_KEY=your_private_key_here
WALLET_ADDRESS=your_wallet_address_here

# API Keys
INFURA_API_KEY=your_infura_api_key

# Bot Configuration
MIN_PROFIT_THRESHOLD=0.5
MAX_SLIPPAGE=1.0
GAS_PRICE_MULTIPLIER=1.1
MAX_TRADE_AMOUNT=0.1

# Dashboard Configuration
DASHBOARD_PORT=8080
API_PORT=8000
ENABLE_AUTHENTICATION=false

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=logs/bot.log
```

## Coding Standards

### Python

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use [Black](https://github.com/psf/black) for code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use [flake8](https://flake8.pycqa.org/) for linting
- Use [mypy](http://mypy-lang.org/) for type checking

### JavaScript

- Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use [ESLint](https://eslint.org/) for linting
- Use [Prettier](https://prettier.io/) for code formatting

### General Guidelines

- Write clear, readable, and maintainable code
- Include docstrings and comments where necessary
- Keep functions and methods small and focused
- Follow the DRY (Don't Repeat Yourself) principle
- Write unit tests for new code
- Update documentation when changing functionality

## Git Workflow

We follow a feature branch workflow:

1. Ensure your fork is up to date:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

3. Make your changes and commit them:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

4. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

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

## Pull Request Process

1. Create a pull request from your feature branch to the upstream main branch
2. Fill in the pull request template with all required information
3. Ensure all CI checks pass
4. Request a review from a maintainer
5. Address any feedback from reviewers
6. Once approved, a maintainer will merge your pull request

### Pull Request Template

```markdown
## Description
[Describe the changes you've made]

## Related Issue
[Link to the related issue, if applicable]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Other (please describe)

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] I have updated the documentation accordingly
- [ ] My changes generate no new warnings
- [ ] All tests pass locally
```

## Testing

### Running Tests

Run the test suite:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=arbitrage_bot
```

### Writing Tests

- Write unit tests for all new code
- Use pytest fixtures for test setup
- Mock external dependencies
- Aim for high test coverage
- Include both positive and negative test cases

Example test:
```python
def test_calculate_profit():
    # Arrange
    input_amount = 1.0
    output_amount = 1.05
    gas_cost = 0.01
    
    # Act
    profit = calculate_profit(input_amount, output_amount, gas_cost)
    
    # Assert
    assert profit == 0.04
    assert profit > 0
```

## Documentation

### Code Documentation

- Use docstrings for all public modules, functions, classes, and methods
- Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) for docstrings

Example:
```python
def calculate_profit(input_amount, output_amount, gas_cost):
    """Calculate the net profit from a trade.
    
    Args:
        input_amount (float): The amount of tokens used as input
        output_amount (float): The amount of tokens received as output
        gas_cost (float): The gas cost in the same unit as input_amount
        
    Returns:
        float: The net profit (output_amount - input_amount - gas_cost)
    """
    return output_amount - input_amount - gas_cost
```

### Project Documentation

- Update the README.md when adding new features
- Update API documentation when changing endpoints
- Add examples for new functionality
- Keep the documentation up to date with the code

## Issue Reporting

### Bug Reports

When reporting a bug, please include:

1. A clear and descriptive title
2. Steps to reproduce the bug
3. Expected behavior
4. Actual behavior
5. Screenshots or logs (if applicable)
6. Environment information (OS, Python version, etc.)
7. Any additional context

### Security Vulnerabilities

For security vulnerabilities, please do not create a public issue. Instead, email security@listonian-bot.com with the details.

## Feature Requests

When suggesting a feature, please include:

1. A clear and descriptive title
2. A detailed description of the proposed feature
3. The problem it solves
4. Any alternatives you've considered
5. Any additional context or examples

## Recognition

Contributors will be recognized in the following ways:

1. Added to the CONTRIBUTORS.md file
2. Mentioned in release notes for significant contributions
3. Potential invitation to become a maintainer for consistent contributors

Thank you for contributing to the Listonian Bot project! Your efforts help make this project better for everyone.
