# Modular Architecture Plan for Listonian Bot

This plan outlines the steps to refactor the Listonian Bot into a modular architecture consisting of a DEX Scanner MCP, an Arbitrage Bot, and a Dashboard, communicating via Inter-Process Communication (IPC).

## Goals

1.  **Decouple Components:** Separate the DEX scanning, arbitrage logic, and dashboard into independent processes.
2.  **Improve Scalability & Maintainability:** Allow individual components to be updated, restarted, and scaled independently.
3.  **Centralized Monitoring:** Provide a dashboard that aggregates metrics and status from all components.
4.  **Clear Logging:** Implement separate log files for each component for easier debugging.

## Architecture Overview

```mermaid
graph LR
    subgraph System Components
        direction LR
        MCP[DEX Scanner MCP<br>(run_base_dex_scanner_mcp_with_api.py<br>Logs: logs/mcp.log)]
        Bot[Arbitrage Bot<br>(run_bot.py<br>Logs: logs/bot.log)]
        Dash[Dashboard<br>(run_dashboard.py<br>Logs: logs/dashboard.log)]
        IPC[Inter-Process Communication<br>(e.g., Shared Memory/Queue/API)]
    end

    subgraph User Interaction
        direction TB
        User((User)) --> DashUI[Dashboard UI<br>(localhost:9051)]
    end

    %% Data Flow
    MCP -- DEX/Pool Data API --> Bot
    Bot -- Metrics/Status --> IPC
    IPC -- Metrics/Status --> Dash
    Dash -- WebSocket --> DashUI

    %% Logging
    MCP --> Log1[logs/mcp.log]
    Bot --> Log2[logs/bot.log]
    Dash --> Log3[logs/dashboard.log]

    %% Startup
    StartScript[Windows Start Script<br>(.bat/.ps1)] --> MCP
    StartScript --> Bot
    StartScript --> Dash

    style IPC fill:#ccf,stroke:#333,stroke-width:2px
```

## Implementation Steps

1.  **Establish Inter-Process Communication (IPC):**
    *   Choose and implement an IPC mechanism (e.g., adapt `MemoryBank`, use a file-based queue, or a simple local API). This mechanism will transfer metrics and status updates from the Bot to the Dashboard.
    *   Define the data structure for metrics (Opportunities Detected, Profitable Trades Executed, Error Log Summary, Gas Used Per Hour (ETH)).

2.  **Modify Arbitrage Bot (`run_bot.py`):**
    *   Remove direct DEX scanning logic.
    *   Integrate with the DEX Scanner MCP's API to fetch market data (DEXes, pools, prices).
    *   Implement logic to calculate the required metrics.
    *   Publish calculated metrics and operational status (e.g., 'Running', 'Error', 'Idle') via the chosen IPC mechanism.
    *   Configure logging to output to `logs/bot.log`.

3.  **Modify Dashboard (`run_dashboard.py` / `new_dashboard/`):**
    *   Remove internal arbitrage bot logic and direct blockchain interaction.
    *   Implement logic to consume metrics and status updates from the IPC mechanism.
    *   Update the dashboard UI (`new_dashboard/static/index.html` and associated JS) to display the new metrics:
        *   Opportunities Detected
        *   Profitable Trades Executed
        *   Error Log Summary (potentially a count or list of recent errors)
        *   Gas Used Per Hour (ETH)
        *   Component Status (MCP, Bot, Dashboard)
    *   Configure logging to output to `logs/dashboard.log`.

4.  **Refine DEX Scanner MCP (`run_base_dex_scanner_mcp_with_api.py`):**
    *   Review and address existing warnings related to pool counting (`Contract logic error`, `Could not find a known function`, `Bad function call output`). This might involve updating ABIs, checking contract addresses, or adjusting logic for specific DEX factories.
    *   Ensure logging is directed to `logs/mcp.log`.
    *   Verify the API endpoints (`/api/v1/scan_dexes`, `/api/v1/get_factory_pools`, etc.) are robust and provide necessary data to the Arbitrage Bot.

5.  **Create Startup Script:**
    *   Develop a Windows batch (`.bat`) or PowerShell (`.ps1`) script (`Listonian-bot/scripts/start_production.bat` or `start_production.ps1`).
    *   The script should:
        *   Activate the Python virtual environment (`venv`).
        *   Start the DEX Scanner MCP (`run_base_dex_scanner_mcp_with_api.py`).
        *   Start the Arbitrage Bot (`run_bot.py`).
        *   Start the Dashboard (`run_dashboard.py`).
        *   Ensure each process runs in the background or in separate terminal windows.

6.  **Update Documentation (`README_PRODUCTION.md`):**
    *   Document the new modular architecture.
    *   Provide clear instructions on how to use the new startup script to run the entire system.
    *   Explain the purpose of each component and the log files.