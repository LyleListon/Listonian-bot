# Integration Module

The integration module provides connectors and adapters for integrating the Listonian Arbitrage Bot with external systems, APIs, and data sources. It serves as the bridge between the core bot functionality and the wider ecosystem.

## Components

### Base DEX Scanner MCP

The Base DEX Scanner MCP (Model Context Protocol) integration allows the bot to interact with the Base DEX Scanner service:

```python
from arbitrage_bot.integration.base_dex_scanner_mcp import BaseDexScannerMCP

# Initialize the MCP connector
scanner = BaseDexScannerMCP(
    endpoint="http://localhost:8000",
    api_key="your_api_key",
    config=scanner_config
)

# Get latest pool data
pools = await scanner.get_pools(
    dex="uniswap_v3",
    limit=100
)

# Get price data
prices = await scanner.get_prices(
    token_addresses=["0x...", "0x..."],
    vs_currency="usd"
)
```

### External Price Feeds

Connectors for external price feed services:

- **CoinGecko**: Market data and price information
- **CoinMarketCap**: Alternative market data source
- **ChainLink**: On-chain price oracles

```python
from arbitrage_bot.integration.price_feeds import CoinGeckoConnector

# Initialize the price feed
price_feed = CoinGeckoConnector(api_key="your_api_key")

# Get token prices
prices = await price_feed.get_prices(
    token_ids=["ethereum", "bitcoin"],
    vs_currencies=["usd", "eur"]
)
```

### Block Explorers

Integration with blockchain explorers for transaction monitoring and verification:

```python
from arbitrage_bot.integration.block_explorers import EtherscanConnector

# Initialize the explorer connector
explorer = EtherscanConnector(api_key="your_api_key")

# Get transaction details
tx_details = await explorer.get_transaction(tx_hash="0x...")

# Get contract ABI
contract_abi = await explorer.get_contract_abi(address="0x...")
```

### Data Export

Tools for exporting bot data to external systems:

```python
from arbitrage_bot.integration.exporters import CSVExporter

# Initialize the exporter
exporter = CSVExporter(output_dir="./data/exports")

# Export trade history
await exporter.export_trades(
    trades=trade_history,
    filename="trade_history.csv"
)
```

## Configuration

Integration components are configured through the `configs/integration_config.json` file:

```json
{
  "base_dex_scanner": {
    "endpoint": "http://localhost:8000",
    "api_key": "${BASE_DEX_SCANNER_API_KEY}",
    "timeout": 30,
    "retry_attempts": 3
  },
  "price_feeds": {
    "coingecko": {
      "enabled": true,
      "api_key": "${COINGECKO_API_KEY}",
      "rate_limit": 50
    },
    "chainlink": {
      "enabled": true,
      "rpc_url": "${CHAINLINK_RPC_URL}"
    }
  },
  "block_explorers": {
    "etherscan": {
      "enabled": true,
      "api_key": "${ETHERSCAN_API_KEY}"
    }
  }
}
```

Environment variables in the configuration (e.g., `${BASE_DEX_SCANNER_API_KEY}`) are automatically replaced with their values at runtime.

## Security

The integration module implements several security measures:

- **API Key Management**: Secure handling of API keys
- **Rate Limiting**: Respect for service rate limits
- **Retry Mechanisms**: Graceful handling of temporary failures
- **Timeout Handling**: Protection against hanging requests
- **Data Validation**: Validation of all external data

## Adding New Integrations

To add a new integration:

1. Create a new class in the appropriate subdirectory
2. Implement the required interface methods
3. Add configuration options to the integration config
4. Create unit tests for the new integration

Example of a new integration:

```python
from arbitrage_bot.integration.base import BaseIntegration

class NewServiceConnector(BaseIntegration):
    """Connector for NewService API."""
    
    def __init__(self, api_key, endpoint, config=None):
        super().__init__(config)
        self.api_key = api_key
        self.endpoint = endpoint
        self.client = self._create_client()
        
    def _create_client(self):
        """Create the API client."""
        # Implementation
        
    async def get_data(self, params):
        """Get data from the service."""
        # Implementation
```

## Testing

Each integration has dedicated tests:

```bash
python -m pytest arbitrage_bot/tests/integration/
```

The tests use mock servers to simulate external services, ensuring that tests can run without actual external dependencies.