#!/usr/bin/env python
"""
GitHub Strategy Tracker Example

This example demonstrates how to use the GitHub MCP server to track arbitrage strategies,
analyze performance, and manage strategy versions.

Before running this example:
1. Set up GitHub credentials using setup_mcp_keys.bat
2. Start the GitHub MCP server using run_github_tracker.bat

Usage:
    python github_tracker_example.py
"""

import asyncio
import json
import logging
import datetime
import random
from decimal import Decimal
from typing import Dict, List, Any, Optional
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("github_tracker_example")


class GitHubClient:
    """
    Client for interacting with the GitHub MCP server.
    
    This class provides methods to:
    1. Save strategy configurations and results to GitHub
    2. Retrieve strategy history and performance metrics
    3. Compare different strategies
    4. Deploy strategies to production
    """
    
    def __init__(self):
        """Initialize the GitHub client."""
        self.logger = logging.getLogger(__name__)
        
        # In a real implementation, this would connect to the MCP server
        # For this example, we'll simulate the responses
        self.logger.info("Initialized GitHub client")
    
    async def save_strategy(self, strategy_name: str, config: Dict[str, Any], 
                           performance: Dict[str, Any], branch: str = "main") -> Dict[str, Any]:
        """
        Save a strategy configuration and performance metrics to GitHub.
        
        Args:
            strategy_name: Name of the strategy
            config: Strategy configuration parameters
            performance: Performance metrics
            branch: GitHub branch to save to (default: main)
            
        Returns:
            Response with commit information
        """
        self.logger.info(f"Saving strategy '{strategy_name}' to GitHub ({branch} branch)")
        
        # In a real implementation, this would call the GitHub MCP server
        # For this example, we'll simulate the response
        
        # Generate a fake commit hash
        commit_hash = uuid.uuid4().hex[:7]
        
        # Simulated response
        response = {
            "success": True,
            "commit_hash": commit_hash,
            "branch": branch,
            "repository": "user/arbitrage-strategies",
            "file_path": f"strategies/{strategy_name}/config.json",
            "performance_path": f"strategies/{strategy_name}/performance/{datetime.datetime.now().strftime('%Y-%m-%d')}.json",
            "timestamp": datetime.datetime.now().isoformat(),
            "message": f"Update {strategy_name} strategy and performance metrics"
        }
        
        self.logger.info(f"Strategy saved successfully. Commit: {commit_hash}")
        return response
    
    async def get_strategy(self, strategy_name: str, commit_hash: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve a strategy configuration from GitHub.
        
        Args:
            strategy_name: Name of the strategy to retrieve
            commit_hash: Optional specific commit hash to retrieve
            
        Returns:
            Strategy configuration
        """
        self.logger.info(f"Retrieving strategy '{strategy_name}'" + 
                        (f" at commit {commit_hash}" if commit_hash else ""))
        
        # In a real implementation, this would call the GitHub MCP server
        # For this example, we'll simulate the response
        
        # Simulated strategy configuration
        strategy_config = {
            "name": strategy_name,
            "version": "1.0.0",
            "base_token": "WETH",
            "quote_tokens": ["USDC", "USDT", "DAI", "WBTC"],
            "dexes": ["Uniswap V3", "SushiSwap", "PancakeSwap V3"],
            "parameters": {
                "min_profit_threshold": "0.05",
                "max_gas_price": "100",
                "slippage_tolerance": "0.5",
                "use_flashbots": True,
                "flash_loan_enabled": True,
                "flash_loan_provider": "Balancer"
            },
            "created_at": (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "commit_hash": commit_hash or uuid.uuid4().hex[:7]
        }
        
        return strategy_config
    
    async def get_strategy_history(self, strategy_name: str, days: int = 30) -> Dict[str, Any]:
        """
        Get historical performance for a strategy.
        
        Args:
            strategy_name: Name of the strategy
            days: Number of days of history to retrieve
            
        Returns:
            Dictionary with historical performance data
        """
        self.logger.info(f"Retrieving {days} days of history for strategy '{strategy_name}'")
        
        # In a real implementation, this would call the GitHub MCP server
        # For this example, we'll simulate the response
        
        # Generate daily performance data
        history = {
            "strategy": strategy_name,
            "days": days,
            "start_date": (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d"),
            "end_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "performance": []
        }
        
        # Generate random daily performance data
        for i in range(days):
            date = (datetime.datetime.now() - datetime.timedelta(days=days-i)).strftime("%Y-%m-%d")
            
            # Simulate varying performance
            profit_factor = 1.0 + (i / days) * 0.5  # Gradually improving performance
            
            # Randomize daily results
            daily_data = {
                "date": date,
                "trades": random.randint(5, 50),
                "successful_trades": random.randint(3, 45),
                "profit_eth": str(round(random.uniform(0.1, 2.0) * profit_factor, 4)),
                "gas_used_eth": str(round(random.uniform(0.01, 0.2), 4)),
                "net_profit_eth": str(round(random.uniform(0.05, 1.8) * profit_factor, 4)),
                "largest_profit_eth": str(round(random.uniform(0.1, 0.5) * profit_factor, 4)),
                "average_profit_eth": str(round(random.uniform(0.01, 0.1) * profit_factor, 4)),
                "success_rate": str(round(random.uniform(60, 95), 2)),
                "avg_execution_time_ms": random.randint(200, 1500),
                "total_flashloan_fees_eth": str(round(random.uniform(0.005, 0.05), 4)),
                "total_gas_saved_flashbots": str(round(random.uniform(0.001, 0.02), 4)),
                "commit_hash": uuid.uuid4().hex[:7]
            }
            
            history["performance"].append(daily_data)
        
        # Sort by date
        history["performance"].sort(key=lambda x: x["date"])
        
        # Calculate aggregated stats
        total_profit = sum(Decimal(day["profit_eth"]) for day in history["performance"])
        total_gas = sum(Decimal(day["gas_used_eth"]) for day in history["performance"])
        total_net_profit = sum(Decimal(day["net_profit_eth"]) for day in history["performance"])
        total_trades = sum(day["trades"] for day in history["performance"])
        successful_trades = sum(day["successful_trades"] for day in history["performance"])
        
        history["summary"] = {
            "total_profit_eth": str(round(total_profit, 4)),
            "total_gas_used_eth": str(round(total_gas, 4)),
            "total_net_profit_eth": str(round(total_net_profit, 4)),
            "total_trades": total_trades,
            "successful_trades": successful_trades,
            "overall_success_rate": f"{round((successful_trades / total_trades) * 100, 2)}%"
        }
        
        return history
    
    async def compare_strategies(self, strategy_names: List[str], days: int = 30) -> Dict[str, Any]:
        """
        Compare performance of multiple strategies.
        
        Args:
            strategy_names: List of strategy names to compare
            days: Number of days to compare
            
        Returns:
            Comparison results
        """
        self.logger.info(f"Comparing strategies: {', '.join(strategy_names)} over {days} days")
        
        # In a real implementation, this would call the GitHub MCP server
        # For this example, we'll simulate the response
        
        strategies_data = {}
        
        # Get history for each strategy
        for strategy_name in strategy_names:
            history = await self.get_strategy_history(strategy_name, days)
            strategies_data[strategy_name] = history["summary"]
            strategies_data[strategy_name]["daily"] = history["performance"]
        
        # Calculate which strategy performed best
        best_strategy = max(strategy_names, 
                           key=lambda s: Decimal(strategies_data[s]["total_net_profit_eth"]))
        
        comparison = {
            "strategies": strategy_names,
            "days_compared": days,
            "best_strategy": best_strategy,
            "data": strategies_data,
            "relative_performance": {},
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Calculate relative performance (percentage better/worse than baseline)
        baseline = strategy_names[0]
        baseline_profit = Decimal(strategies_data[baseline]["total_net_profit_eth"])
        
        for strategy in strategy_names:
            if strategy == baseline:
                comparison["relative_performance"][strategy] = "baseline"
            else:
                strategy_profit = Decimal(strategies_data[strategy]["total_net_profit_eth"])
                percentage_diff = ((strategy_profit / baseline_profit) - 1) * 100
                comparison["relative_performance"][strategy] = f"{round(percentage_diff, 2)}%"
        
        return comparison
    
    async def deploy_strategy(self, strategy_name: str, commit_hash: Optional[str] = None, 
                             environment: str = "production") -> Dict[str, Any]:
        """
        Deploy a strategy to a specific environment.
        
        Args:
            strategy_name: Name of the strategy to deploy
            commit_hash: Optional specific commit to deploy
            environment: Environment to deploy to (default: production)
            
        Returns:
            Deployment result
        """
        self.logger.info(f"Deploying strategy '{strategy_name}' to {environment}" +
                        (f" at commit {commit_hash}" if commit_hash else ""))
        
        # In a real implementation, this would call the GitHub MCP server
        # For this example, we'll simulate the response
        
        # Get the strategy configuration first
        strategy = await self.get_strategy(strategy_name, commit_hash)
        
        # Simulated deployment response
        deployment_id = uuid.uuid4().hex[:10]
        
        response = {
            "success": True,
            "deployment_id": deployment_id,
            "strategy": strategy_name,
            "environment": environment,
            "commit_hash": commit_hash or strategy["commit_hash"],
            "deployed_by": "user@example.com",
            "deployed_at": datetime.datetime.now().isoformat(),
            "status": "active",
            "config_snapshot": strategy
        }
        
        self.logger.info(f"Strategy deployed successfully. Deployment ID: {deployment_id}")
        return response
    
    async def create_report(self, strategy_name: str, days: int = 30) -> Dict[str, Any]:
        """
        Create a markdown report of strategy performance.
        
        Args:
            strategy_name: Name of the strategy
            days: Number of days to include
            
        Returns:
            Report content
        """
        self.logger.info(f"Creating report for strategy '{strategy_name}' covering {days} days")
        
        # In a real implementation, this would call the GitHub MCP server
        # For this example, we'll simulate the response
        
        # Get the strategy history
        history = await self.get_strategy_history(strategy_name, days)
        strategy = await self.get_strategy(strategy_name)
        
        # Generate a markdown report
        report_content = f"""# Performance Report: {strategy_name}

## Overview

- **Period**: {history["start_date"]} to {history["end_date"]} ({days} days)
- **Strategy Version**: {strategy["version"]}
- **Base Token**: {strategy["base_token"]}
- **Quote Tokens**: {", ".join(strategy["quote_tokens"])}
- **DEXes**: {", ".join(strategy["dexes"])}

## Summary Metrics

- **Total Net Profit**: {history["summary"]["total_net_profit_eth"]} ETH
- **Total Gross Profit**: {history["summary"]["total_profit_eth"]} ETH
- **Total Gas Used**: {history["summary"]["total_gas_used_eth"]} ETH
- **Total Trades**: {history["summary"]["total_trades"]}
- **Successful Trades**: {history["summary"]["successful_trades"]}
- **Success Rate**: {history["summary"]["overall_success_rate"]}

## Performance Chart

```
Performance visualization would be here in the actual report
```

## Daily Breakdown

| Date | Trades | Success Rate | Net Profit (ETH) | Gas Used (ETH) |
|------|--------|-------------|-----------------|---------------|
"""
        
        # Add daily data rows
        for day in history["performance"][-7:]:  # Show last 7 days in the table
            report_content += f"| {day['date']} | {day['trades']} | {day['success_rate']}% | {day['net_profit_eth']} | {day['gas_used_eth']} |\n"
        
        report_content += """
## Recommendations

- Continue using Flashbots for MEV protection
- Consider adjusting gas price strategy for higher profit margins
- Explore additional DEXes for more arbitrage opportunities
- Monitor slippage parameters for optimal trade execution

## Next Steps

- Test strategy with increased capital allocation
- Implement multi-path arbitrage enhancements
- Integrate with Glama AI for enhanced market analysis
- Deploy to additional networks for cross-chain opportunities
"""
        
        # Simulated response
        response = {
            "success": True,
            "strategy": strategy_name,
            "report_type": "performance",
            "days": days,
            "report_content": report_content,
            "timestamp": datetime.datetime.now().isoformat(),
            "format": "markdown"
        }
        
        self.logger.info(f"Report created successfully")
        return response


async def demonstrate_save_strategy():
    """Demonstrate saving a strategy to GitHub."""
    logger.info("Demonstrating saving a strategy to GitHub...")
    
    # Initialize the GitHub client
    github_client = GitHubClient()
    
    # Create a sample strategy configuration
    strategy_name = "FlashLoanMultiPath"
    
    strategy_config = {
        "name": strategy_name,
        "version": "1.0.0",
        "base_token": "WETH",
        "quote_tokens": ["USDC", "USDT", "DAI", "WBTC"],
        "dexes": ["Uniswap V3", "SushiSwap", "PancakeSwap V3"],
        "parameters": {
            "min_profit_threshold": "0.05",
            "max_gas_price": "100",
            "slippage_tolerance": "0.5",
            "use_flashbots": True,
            "flash_loan_enabled": True,
            "flash_loan_provider": "Balancer"
        }
    }
    
    # Create sample performance metrics
    performance_metrics = {
        "timestamp": datetime.datetime.now().isoformat(),
        "period": "24h",
        "trades": 42,
        "successful_trades": 38,
        "profit_eth": "1.25",
        "gas_used_eth": "0.15",
        "net_profit_eth": "1.10",
        "success_rate": "90.48%",
        "avg_execution_time_ms": 750
    }
    
    # Save the strategy to GitHub
    result = await github_client.save_strategy(
        strategy_name=strategy_name,
        config=strategy_config,
        performance=performance_metrics,
        branch="production"
    )
    
    logger.info(f"Strategy saved to GitHub. Commit: {result['commit_hash']}")
    logger.info(f"Strategy file: {result['file_path']}")
    logger.info(f"Performance data: {result['performance_path']}")


async def demonstrate_strategy_history():
    """Demonstrate retrieving strategy history from GitHub."""
    logger.info("Demonstrating retrieving strategy history...")
    
    # Initialize the GitHub client
    github_client = GitHubClient()
    
    # Get history for a strategy
    strategy_name = "FlashLoanMultiPath"
    days = 30
    
    history = await github_client.get_strategy_history(
        strategy_name=strategy_name,
        days=days
    )
    
    logger.info(f"Retrieved {days} days of history for {strategy_name}")
    logger.info(f"Total profit: {history['summary']['total_profit_eth']} ETH")
    logger.info(f"Total gas used: {history['summary']['total_gas_used_eth']} ETH")
    logger.info(f"Net profit: {history['summary']['total_net_profit_eth']} ETH")
    logger.info(f"Success rate: {history['summary']['overall_success_rate']}")
    
    # Show the last 3 days of performance
    logger.info("\nRecent daily performance:")
    for day in history["performance"][-3:]:
        logger.info(f"- {day['date']}: {day['profit_eth']} ETH profit ({day['success_rate']}% success rate)")


async def demonstrate_strategy_comparison():
    """Demonstrate comparing multiple strategies."""
    logger.info("Demonstrating strategy comparison...")
    
    # Initialize the GitHub client
    github_client = GitHubClient()
    
    # Compare multiple strategies
    strategy_names = ["FlashLoanMultiPath", "BasicArbitrage", "FlashbotsProtected"]
    
    comparison = await github_client.compare_strategies(
        strategy_names=strategy_names,
        days=14
    )
    
    logger.info(f"Compared {len(strategy_names)} strategies over {comparison['days_compared']} days")
    logger.info(f"Best performing strategy: {comparison['best_strategy']}")
    
    logger.info("\nRelative performance:")
    for strategy, performance in comparison["relative_performance"].items():
        logger.info(f"- {strategy}: {performance}")
    
    logger.info("\nNet profit comparison:")
    for strategy in strategy_names:
        profit = comparison["data"][strategy]["total_net_profit_eth"]
        logger.info(f"- {strategy}: {profit} ETH")


async def demonstrate_strategy_deployment():
    """Demonstrate deploying a strategy to production."""
    logger.info("Demonstrating strategy deployment...")
    
    # Initialize the GitHub client
    github_client = GitHubClient()
    
    # Deploy a strategy to production
    strategy_name = "FlashLoanMultiPath"
    
    deployment = await github_client.deploy_strategy(
        strategy_name=strategy_name,
        environment="production"
    )
    
    logger.info(f"Deployed {strategy_name} to {deployment['environment']}")
    logger.info(f"Deployment ID: {deployment['deployment_id']}")
    logger.info(f"Deployed at: {deployment['deployed_at']}")
    logger.info(f"Status: {deployment['status']}")


async def demonstrate_report_generation():
    """Demonstrate generating a strategy performance report."""
    logger.info("Demonstrating report generation...")
    
    # Initialize the GitHub client
    github_client = GitHubClient()
    
    # Generate a report for a strategy
    strategy_name = "FlashLoanMultiPath"
    
    report = await github_client.create_report(
        strategy_name=strategy_name,
        days=30
    )
    
    logger.info(f"Generated {report['report_type']} report for {strategy_name}")
    
    # Display a preview of the report
    report_lines = report["report_content"].split("\n")
    preview_lines = report_lines[:10] + ["..."] + report_lines[-5:]
    
    logger.info("\nReport preview:")
    for line in preview_lines:
        logger.info(line)


async def main():
    """Main function demonstrating GitHub strategy tracking."""
    logger.info("Starting GitHub Strategy Tracker Example")
    
    try:
        # Demonstrate saving a strategy
        await demonstrate_save_strategy()
        
        logger.info("\n" + "="*50 + "\n")
        
        # Demonstrate retrieving strategy history
        await demonstrate_strategy_history()
        
        logger.info("\n" + "="*50 + "\n")
        
        # Demonstrate comparing strategies
        await demonstrate_strategy_comparison()
        
        logger.info("\n" + "="*50 + "\n")
        
        # Demonstrate deploying a strategy
        await demonstrate_strategy_deployment()
        
        logger.info("\n" + "="*50 + "\n")
        
        # Demonstrate report generation
        await demonstrate_report_generation()
        
        logger.info("\nExample completed successfully")
    except Exception as e:
        logger.error(f"Error in example: {str(e)}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())