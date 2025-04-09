# Component Integration Guide

This document explains how all components of the Listonian Arbitrage Bot are integrated and how to ensure they work together properly.

## System Architecture

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│  Arbitrage Bot      │◄────►│  Memory Bank        │◄────►│  Dashboard          │
│  (run_bot.py)       │      │  (Shared Storage)   │      │  (run_dashboard.py) │
│                     │      │                     │      │                     │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
          ▲                             ▲                             ▲
          │                             │                             │
          ▼                             ▼                             ▼
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│  MCP Servers        │◄────►│  WebSocket Server   │◄────►│  Service Manager    │
│  (Data Providers)   │      │  (Real-time Comms)  │      │  (Coordination)     │
│                     │      │                     │      │                     │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
```

## Key Components

### 1. Arbitrage Bot (run_bot.py)

The arbitrage bot is the core component responsible for finding and executing arbitrage opportunities. It consists of:

- **Discovery Manager**: Finds arbitrage opportunities across DEXes
- **Execution Manager**: Executes trades using various strategies
- **Analytics Manager**: Records and analyzes trade performance
- **Market Data Provider**: Provides market data for decision making

The bot writes data to the memory bank and can be controlled through the dashboard.

### 2. Memory Bank (memory-bank/)

The memory bank serves as the central data store for both the arbitrage bot and dashboard. It consists of:

- **Trades**: Records of executed trades
- **Metrics**: Performance metrics
- **State**: System state information

The memory bank is a file-based storage system that both the bot and dashboard can access.

### 3. Dashboard (run_dashboard.py)

The dashboard provides a web interface for monitoring and controlling the bot. It consists of:

- **Service Manager**: Coordinates all dashboard services
- **Memory Service**: Reads data from the memory bank
- **Metrics Service**: Processes and displays metrics
- **System Service**: Monitors system status
- **Market Data Service**: Displays market information

The dashboard reads data from the memory bank and can send commands to the bot.

### 4. MCP Servers

The MCP (Master Control Program) servers provide data and analysis for the arbitrage bot:

- **Base DEX Scanner**: Monitors the Base blockchain for DEXes and pools
- **Crypto Price**: Provides cryptocurrency price data
- **Market Analysis**: Analyzes market conditions and trends

The MCP servers are accessed through the MCP client in the arbitrage bot.

### 5. WebSocket Server

The WebSocket server provides real-time communication between the bot and dashboard. It:

- Sends real-time updates from the bot to the dashboard
- Handles user commands from the dashboard to the bot

## Integration Points

### 1. Memory Bank Integration

The memory bank is the primary integration point between the bot and dashboard. Both components read from and write to the memory bank.

**Bot to Memory Bank**:
```python
# In arbitrage_bot/core/memory/memory_bank.py
async def add_trade(self, trade: Dict[str, Any]) -> None:
    """Add a trade to storage."""
    if not self._initialized:
        raise RuntimeError("Memory bank not initialized")
    
    async with self._lock:
        trade_id = trade['id']
        timestamp = datetime.fromisoformat(trade['timestamp'])
        
        # Add to trades list and index
        self._trades.append(trade)
        self._trade_index[trade_id] = trade
        
        # Persist trade to file
        file_path = self._trades_dir / f"trade_{int(timestamp.timestamp())}.json"
        await self._file_manager.write_json(file_path, trade)
```

**Dashboard to Memory Bank**:
```python
# In new_dashboard/dashboard/services/memory_service.py
async def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent trades from memory bank."""
    trades = []
    
    # Read trade files from memory bank
    trade_files = sorted(self._trades_dir.glob("trade_*.json"), reverse=True)
    
    for file_path in trade_files[:limit]:
        try:
            with open(file_path) as f:
                trade = json.load(f)
                trades.append(trade)
        except Exception as e:
            logger.error(f"Error reading trade file {file_path}: {e}")
    
    return trades
```

### 2. WebSocket Integration

The WebSocket server provides real-time communication between the bot and dashboard.

**Bot to WebSocket**:
```python
# In arbitrage_bot/dashboard/websocket_server.py
async def broadcast_update(self, update_type: str, data: Dict[str, Any]) -> None:
    """Broadcast an update to all connected clients."""
    message = {
        "type": update_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    
    await self.connection_manager.broadcast(message)
```

**Dashboard to WebSocket**:
```python
# In new_dashboard/dashboard/routes/websocket.py
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle commands from client
            if "command" in data:
                response = await handle_command(data["command"], data.get("params", {}))
                await websocket.send_json(response)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
```

### 3. MCP Server Integration

The MCP servers are integrated with the arbitrage bot through the MCP client.

**Bot to MCP Server**:
```python
# In arbitrage_bot/utils/mcp_helper.py
def call_mcp_tool(
    server_name: str, tool_name: str, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Call MCP tool with arguments."""
    try:
        client = get_mcp_client(server_name)
        response = client.call_tool(tool_name, arguments)
        return response
    except Exception as e:
        logger.error(f"Failed to call MCP tool {tool_name} on {server_name}: {e}")
        raise
```

## Configuration Integration

The configuration system uses a layered approach:

1. **Base Configuration**: `configs/default.json`
2. **User Configuration**: `config.json`
3. **Environment Variables**: `.env` and `.env.production`
4. **Dashboard Configuration**: `new_dashboard/config.json`
5. **MCP Configuration**: `.augment/mcp_config.json`

## Startup Sequence

The proper startup sequence is:

1. Initialize the memory bank
2. Start the MCP servers
3. Start the arbitrage bot
4. Start the dashboard

This sequence ensures that all dependencies are available when needed.

## Troubleshooting Integration Issues

### 1. Memory Bank Issues

If the dashboard cannot read data from the memory bank:

- Check that the memory bank directories exist
- Verify file permissions
- Ensure the memory bank path is correctly set in both the bot and dashboard
- Check for file locking issues

### 2. WebSocket Issues

If real-time updates are not working:

- Check that the WebSocket server is running
- Verify the WebSocket URL in the dashboard
- Check for network or firewall issues
- Look for errors in the WebSocket server logs

### 3. MCP Server Issues

If the MCP servers are not working:

- Check that the MCP servers are running
- Verify the MCP server URLs
- Check the MCP server logs for errors
- Ensure the MCP client is correctly configured

## Testing Integration

To test the integration between components:

1. Start all components using `scripts/start_all_components.ps1`
2. Open the dashboard at http://localhost:9051
3. Check that real-time updates are working
4. Verify that data from the memory bank is displayed
5. Test commands from the dashboard to the bot

## Next Steps

1. **Enhance Error Handling**: Improve error handling and recovery
2. **Add Authentication**: Implement authentication for dashboard access
3. **Optimize Data Flow**: Reduce latency in data exchange between components
4. **Implement Monitoring**: Add monitoring for all components
