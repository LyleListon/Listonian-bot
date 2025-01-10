# Dashboard Components Flow

```mermaid
graph TD
    %% Entry Point
    run[run_dashboard.py] --> app[DashboardApp]

    %% Main Components
    app --> routes[Routes]
    app --> perf[PerformanceTracker]
    app --> monitor[SystemMonitor]

    %% Templates and Static Files
    routes --> |renders| trade[trade_feed.html]
    routes --> |renders| perform[performance.html]
    routes --> |renders| system[system.html]
    routes --> |renders| settings[settings.html]

    %% Static Assets
    trade --> |uses| js[dashboard.js]
    perform --> |uses| js
    system --> |uses| js
    
    %% Data Flow
    perf --> db[(Database)]
    monitor --> core[Core Components]
    
    %% Core Component Details
    core --> exec[ArbitrageExecutor]
    core --> risk[RiskManager]

    %% WebSocket Updates
    js --> |real-time updates| routes
    
    %% Style Definitions
    classDef frontend fill:#e3f2fd,stroke:#1565c0
    classDef backend fill:#e8f5e9,stroke:#2e7d32
    classDef data fill:#fff3e0,stroke:#ef6c00
    classDef core fill:#f3e5f5,stroke:#6a1b9a

    %% Apply Styles
    class run,app,routes backend
    class trade,perform,system,settings,js frontend
    class db data
    class exec,risk,core,perf,monitor core
```

Key Features:
1. Real-time updates via WebSocket
2. Performance tracking and historical data
3. System monitoring integration
4. Configuration management

Dashboard Pages:
- trade_feed.html: Live trading activity
- performance.html: Historical performance metrics
- system.html: System health and status
- settings.html: Configuration management

Data Flow:
1. Core components generate events
2. Events stored in database
3. Dashboard queries and displays data
4. WebSocket provides real-time updates
5. User can modify settings through interface
