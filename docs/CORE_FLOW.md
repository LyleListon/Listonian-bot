# Core Components Flow

```mermaid
graph TD
    %% Main Entry Points
    main[main.py] --> exec[ArbitrageExecutor]
    main --> dash[run_dashboard.py]

    %% Core Components
    exec --> risk[RiskManager]
    exec --> dex[DexInterface]
    exec --> market[MarketAnalyzer]

    %% External Data
    market --> mcp1[crypto-price MCP]
    market --> mcp2[market-analysis MCP]
    
    %% Contract Interaction
    dex --> web3[Web3Utils]
    dex --> rate[RateLimiter]

    %% Style Definitions
    classDef core fill:#e1f5fe,stroke:#01579b
    classDef mcp fill:#e8f5e9,stroke:#2e7d32
    classDef util fill:#fff3e0,stroke:#ef6c00

    %% Apply Styles
    class exec,risk,dex,market core
    class mcp1,mcp2 mcp
    class web3,rate util
```

This diagram shows:
- Entry points (main.py and dashboard)
- Core business logic components
- External data sources (MCP servers)
- Utility classes

Key relationships:
1. ArbitrageExecutor coordinates all operations
2. MarketAnalyzer gets data from MCP servers
3. DexInterface handles all blockchain interactions
4. RiskManager validates operations

If this renders well, we can create more detailed diagrams for other components.
