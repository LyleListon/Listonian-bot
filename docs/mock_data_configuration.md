# Mock Data Configuration Guide

## Overview

The Listonian-bot project includes several components that can operate in either real data mode or mock data mode. Mock data mode is useful for development and testing, but should **never** be used in production environments.

This guide explains how to properly configure the environment variables to ensure that mock data is not used in production.

## Environment Variables

### `USE_MOCK_DATA`

This environment variable controls whether the system uses mock data or real blockchain data:

- `USE_MOCK_DATA=true`: Enables mock data mode (for development and testing only)
- `USE_MOCK_DATA=false`: Disables mock data mode (default, for production use)

### `ENVIRONMENT`

This environment variable indicates the current deployment environment:

- `ENVIRONMENT=production`: Indicates a production environment
- `ENVIRONMENT=development`: Indicates a development environment
- `ENVIRONMENT=testing`: Indicates a testing environment

## Production Safety Mechanism

To prevent accidental use of mock data in production, a safety mechanism has been implemented:

1. If `ENVIRONMENT=production`, the system will **always** set `USE_MOCK_DATA=false`, regardless of the actual value of the `USE_MOCK_DATA` environment variable.
2. If `USE_MOCK_DATA=true` is detected in a production environment, a critical warning will be logged, and the value will be overridden to `false`.

## Deployment Configuration

### For Production Environments

When deploying to production, always set:

```
ENVIRONMENT=production
USE_MOCK_DATA=false
```

This ensures that real blockchain data is used and provides an additional safety layer.

### For Development/Testing Environments

For development or testing, you can use:

```
ENVIRONMENT=development
USE_MOCK_DATA=true
```

or

```
ENVIRONMENT=testing
USE_MOCK_DATA=true
```

## Warning Signs

The system will display prominent warnings when mock data is being used:

- Console warnings with ⚠️ symbols
- Log entries with WARNING or CRITICAL level
- Visual indicators in the dashboard UI

If you see these warnings in a production environment, it indicates a configuration issue that should be addressed immediately.

## Affected Components

The following components use the mock data configuration:

1. `run_base_dex_scanner_mcp.py` - Base DEX Scanner MCP Server
2. `run_base_dex_scanner_mcp_with_api.py` - Base DEX Scanner MCP Server with HTTP API
3. `run_base_dex_scanner_example.py` - Example script for Base DEX Scanner
4. `arbitrage_bot/integration/base_dex_scanner_mcp.py` - Base DEX Scanner MCP integration

## Verification

To verify that your system is using real data:

1. Check the logs for any mock data warnings
2. Verify that the `ENVIRONMENT` and `USE_MOCK_DATA` environment variables are set correctly
3. Confirm that the data being processed matches real blockchain data

## Troubleshooting

If you encounter issues with the mock data configuration:

1. Verify that all environment variables are set correctly
2. Check the logs for any warnings or errors related to mock data
3. Restart the services after changing environment variables
4. Ensure that all components are using the same configuration

## Best Practices

1. Always set `ENVIRONMENT=production` in production environments
2. Use a deployment checklist that includes verification of the mock data configuration
3. Include monitoring for mock data warnings in your alerting system
4. Regularly audit your environment variables to ensure they are set correctly