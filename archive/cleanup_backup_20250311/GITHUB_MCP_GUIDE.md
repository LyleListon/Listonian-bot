# GitHub MCP Integration Guide

## Overview

This guide explains how to integrate the GitHub MCP (Model Context Protocol) server with the Listonian Arbitrage Bot. The GitHub MCP server enables the bot to interact with GitHub repositories for version control, performance tracking, and collaborative development.

## Prerequisites

- Docker installed on your system
- GitHub account with a Personal Access Token (PAT)
- Basic understanding of Git and GitHub

## Setup Instructions

### 1. Configure API Keys

Run the setup script to configure your GitHub Personal Access Token:

```bash
setup_mcp_keys.bat
```

Follow the prompts to enter your GitHub Personal Access Token. If you don't have a token:

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" (classic)
3. Give your token a name (e.g., "Listonian Bot")
4. Select the scopes: `repo`, `workflow`, `read:org`
5. Click "Generate token" and copy your new PAT

### 2. Test the GitHub MCP Connection

After configuring your token, test the connection with:

```bash
run_github_tracker.bat
```

## GitHub MCP Capabilities

The GitHub MCP server provides the following capabilities for the Listonian Arbitrage Bot:

### 1. Version Control

- **Repository Management**: Create, clone, and manage Git repositories
- **Commit & Push**: Track code changes with detailed commit messages
- **Branch Management**: Create feature branches for new strategies
- **Pull Requests**: Review code changes before merging to production

### 2. Strategy Performance Tracking

- **Performance Metrics**: Track arbitrage strategy performance metrics
- **Historical Data**: Store historical performance data in GitHub
- **Trend Analysis**: Analyze performance trends over time
- **Strategy Comparison**: Compare different arbitrage strategies

### 3. Collaboration

- **Team Collaboration**: Collaborate with team members on code
- **Issue Tracking**: Track bugs and feature requests
- **Documentation**: Maintain project documentation on GitHub
- **Code Reviews**: Review code changes before deployment

## Integration with Arbitrage Strategies

The GitHub MCP server can be integrated with arbitrage strategies to:

1. **Track Strategy Versions**: Maintain different versions of arbitrage strategies
2. **Log Performance Data**: Store performance metrics for each strategy
3. **Revert to Previous Versions**: Easily revert to previous strategy versions if needed
4. **A/B Test Strategies**: Compare different strategies side by side

## Example: Github Strategy Tracker

The `github_strategy_tracker.py` script demonstrates how to use the GitHub MCP to track strategy performance:

```python
import asyncio
import datetime
import logging
from arbitrage_bot.utils.config import Config
from arbitrage_bot.core.arbitrage.strategies.base_strategy import ArbitrageStrategy

class GithubStrategyTracker:
    """
    Tracks arbitrage strategy performance using GitHub MCP.
    Stores performance metrics in GitHub repositories for analysis.
    """
    
    def __init__(self, config: Config, strategy: ArbitrageStrategy):
        self.config = config
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)
        
    async def log_execution(self, opportunity, result, gas_used, profit):
        """
        Log strategy execution details to GitHub.
        
        Args:
            opportunity: The arbitrage opportunity that was executed
            result: The execution result
            gas_used: Gas used for the transaction
            profit: Actual profit realized
        """
        try:
            # Format the data for GitHub storage
            timestamp = datetime.datetime.now().isoformat()
            execution_data = {
                "timestamp": timestamp,
                "strategy": self.strategy.__class__.__name__,
                "tokens": [token.symbol for token in opportunity.path],
                "dexes": [dex.name for dex in opportunity.dexes],
                "expected_profit": str(opportunity.expected_profit),
                "actual_profit": str(profit),
                "gas_used": str(gas_used),
                "success": result.success,
                "transaction_hash": result.tx_hash if result.success else None,
                "error": str(result.error) if not result.success else None
            }
            
            # Store in GitHub repo (could be a performance database)
            # This would be implemented using the GitHub MCP
            self.logger.info(f"Logging execution data to GitHub: {execution_data}")
            
            # Example of using GitHub MCP to store data
            # In actual implementation, this would call the GitHub MCP
            
            return True
        except Exception as e:
            self.logger.error(f"Error logging execution to GitHub: {str(e)}")
            return False
    
    async def compare_strategies(self, strategy_names, time_period_days=30):
        """
        Compare multiple strategy performances over a time period.
        
        Args:
            strategy_names: List of strategy names to compare
            time_period_days: Number of days to analyze
            
        Returns:
            Dictionary with comparison metrics
        """
        try:
            # This would query the GitHub repo for stored performance data
            # and generate comparison metrics
            self.logger.info(f"Comparing strategies: {strategy_names} over {time_period_days} days")
            
            # Example return data - in actual implementation, 
            # this would be real data from GitHub
            return {
                "strategies": strategy_names,
                "period_days": time_period_days,
                "metrics": {
                    "execution_count": {strategy: 100 for strategy in strategy_names},
                    "success_rate": {strategy: 0.95 for strategy in strategy_names},
                    "avg_profit": {strategy: 0.5 for strategy in strategy_names},
                    "total_profit": {strategy: 50.0 for strategy in strategy_names},
                    "avg_gas_cost": {strategy: 0.05 for strategy in strategy_names}
                }
            }
        except Exception as e:
            self.logger.error(f"Error comparing strategies: {str(e)}")
            return None
```

## Troubleshooting

If you encounter the "Overloaded" error or other issues with the GitHub MCP, refer to the troubleshooting guide:

```
memory-bank/mcp_integration_troubleshooting.md
```

## Best Practices

1. **Commit Regularly**: Make regular commits to track strategy changes
2. **Meaningful Commit Messages**: Write descriptive commit messages
3. **Branch for Features**: Create branches for new strategies or features
4. **Pull Before Push**: Always pull latest changes before pushing
5. **Track Performance**: Log strategy performance after each execution
6. **Analyze Trends**: Regularly analyze performance trends
7. **Document Changes**: Document strategy changes in commit messages
8. **Backup Important Data**: Use GitHub as a backup for critical data

## Profit Maximization Opportunities

Integrating GitHub with the Listonian Arbitrage Bot enables several profit maximization opportunities:

1. **Strategy Versioning**: Quickly revert to higher-performing strategy versions
2. **Performance Analytics**: Identify the most profitable strategies through data analysis
3. **A/B Testing**: Compare different strategies under identical market conditions
4. **Collaboration**: Leverage team expertise to improve strategies
5. **Automated Testing**: Set up GitHub Actions to test strategies automatically
6. **Historical Analysis**: Correlate market conditions with strategy performance
7. **Code Quality**: Maintain higher code quality through pull requests and reviews
8. **Documentation**: Keep strategies well-documented for future optimization

## Next Steps

After setting up GitHub MCP:

1. Configure strategy performance tracking
2. Set up automated testing for strategies
3. Implement versioning for arbitrage strategies
4. Create performance dashboards for strategy analysis
5. Integrate with the Glama AI MCP for AI-powered analytics