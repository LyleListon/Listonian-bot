# Context7 MCP Server

This is the Context7 MCP server implementation for the Listonian bot. It provides documentation and context for Base chain DEXes and DeFi protocols.

## Setup

1. Ensure you have Node.js and npm installed
2. Install dependencies:
```bash
npm install
```

## Running the Server

Start the server using:
```bash
python run_context7_mcp.py
```

Or using npm:
```bash
npm start
```

## Configuration

The server uses the default Context7 configuration with enhanced support for Base chain DEXes:
- BaseSwap
- Aerodrome
- SwapBased

## Testing

You can test the server by making documentation requests for various DeFi protocols. For example:

```python
from mcp_client import MCPClient

client = MCPClient()
docs = client.get_documentation("@baseswap/v3-core")
print(docs)
```
