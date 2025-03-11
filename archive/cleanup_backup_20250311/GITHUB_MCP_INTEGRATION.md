# GitHub MCP Integration for Listonian Arbitrage Bot

This guide explains how to integrate the GitHub Model Context Protocol (MCP) server with the Listonian Arbitrage Bot to enable strategy tracking, version control, and collaborative development.

## Overview

The GitHub MCP integration enables the arbitrage bot to:

1. Track profitable trading strategies in private GitHub repositories
2. Version control arbitrage strategies and configurations
3. Analyze historical performance by correlating strategies with profit records
4. Collaborate with team members through pull requests and code reviews
5. Deploy strategies directly from GitHub to production environments
6. Create automated reports of arbitrage performance

## Prerequisites

- Docker installed on your system
- GitHub account with access tokens configured
- Listonian Arbitrage Bot installed and configured

## Setup Instructions

### 1. Pull the GitHub MCP Docker Image

```bash
docker pull mcp/github:latest
```

### 2. Configure GitHub Credentials

Create a GitHub personal access token with the following permissions:
- `repo` (Full control of private repositories)
- `workflow` (For GitHub Actions workflows)
- `read:org` (Read organization data)

Store the token securely in the `secure/github_credentials.json` file:

```json
{
  "username": "your-github-username",
  "token": "your-personal-access-token",
  "default_repo": "your-username/arbitrage-strategies"
}
```

### 3. Run the GitHub MCP Server

Use the provided batch file to start the GitHub MCP server:

```bash
run_github_tracker.bat
```

Alternatively, run it manually:

```bash
docker run -d --name github-mcp \
  -p 8765:8765 \
  -v d:/Listonian-bot/secure/github_credentials.json:/app/credentials.json \
  -e GITHUB_TOKEN_FILE=/app/credentials.json \
  mcp/github:latest
```

### 4. Configure Listonian to Use GitHub MCP

Add the GitHub MCP server to your MCP configuration file:

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": ["exec", "-i", "github-mcp", "node", "/app/server.js"],
      "env": {},
      "disabled": false
    }
  }
}
```

## Usage Examples

### Tracking Strategies in GitHub

```python
from arbitrage_bot.utils.mcp import GitHubClient

async def track_strategy(strategy_name, config, performance_metrics):
    """Track a strategy in GitHub repository."""
    github_client = GitHubClient()
    
    # Save strategy to GitHub
    result = await github_client.save_strategy(
        strategy_name=strategy_name,
        config=config,
        performance=performance_metrics,
        branch="production"
    )
    
    return result
```

### Retrieving Historical Strategy Performance

```python
async def get_strategy_history(strategy_name, days=30):
    """Get historical performance of a strategy."""
    github_client = GitHubClient()
    
    # Get strategy history
    history = await github_client.get_strategy_history(
        strategy_name=strategy_name,
        days=days
    )
    
    return history
```

### Deploying a Strategy from GitHub

```python
async def deploy_strategy_from_github(strategy_name, commit_hash=None):
    """Deploy a strategy from GitHub to production."""
    github_client = GitHubClient()
    
    # Deploy strategy
    result = await github_client.deploy_strategy(
        strategy_name=strategy_name,
        commit_hash=commit_hash,  # Optional: specific version
        environment="production"
    )
    
    return result
```

## Example: GitHub Strategy Tracker

For a complete example implementation, see the included example file:

```
examples/github_tracker_example.py
```

This example demonstrates how to:
1. Track arbitrage strategies in a GitHub repository
2. Retrieve historical performance data
3. Compare different strategy versions
4. Deploy strategies to production

## Available MCP Tools

The GitHub MCP provides the following tools:

1. `save_strategy` - Save a strategy configuration to GitHub
2. `get_strategy` - Retrieve a strategy from GitHub
3. `get_strategy_history` - Get historical performance of a strategy
4. `deploy_strategy` - Deploy a strategy to production
5. `compare_strategies` - Compare performance of multiple strategies
6. `create_report` - Generate a Markdown report of strategy performance

## Security Considerations

- Store GitHub tokens securely in the `secure/` directory
- Use private repositories for sensitive strategies
- Consider using repository branch protection rules
- Rotate GitHub tokens periodically
- Use separate repositories for development and production strategies

## Troubleshooting

### Common Issues

1. **Connection refused errors**:
   - Ensure the Docker container is running
   - Check the port mapping is correct

2. **Authentication failures**:
   - Verify your GitHub token has the correct permissions
   - Check that the token has not expired

3. **Rate limiting**:
   - GitHub API has rate limits - implement exponential backoff
   - Consider using a GitHub App instead of personal tokens for higher limits

4. **Docker container crashes**:
   - Check Docker logs: `docker logs github-mcp`
   - Ensure credentials file is mounted correctly

## Further Resources

- [GitHub API Documentation](https://docs.github.com/en/rest)
- [Docker MCP GitHub Image Documentation](https://hub.docker.com/r/mcp/github)
- [Model Context Protocol Specification](https://github.com/anthropic/mcp-spec)