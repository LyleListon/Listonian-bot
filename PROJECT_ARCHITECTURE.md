# Arbitrage Bot System Architecture

This document provides a comprehensive overview of the entire arbitrage bot system architecture, with special focus on how the dashboard and the core bot components interact with each other.

## System Overview

```mermaid
graph TB
    %% Main components
    User["User"]
    Bot["Arbitrage Bot"]
    Dashboard["Dashboard"]
    Blockchain["Blockchain\n(Base Network)"]
    
    %% Configuration and data stores
    Config["Configuration Files"]
    LogStore["Log Files"]
    DataStore["Data Storage"]
    
    %% Connections
    User -->|"Starts/Configures"| Bot
    User -->|"Monitors via"| Dashboard
    Bot -->|"Interacts with"| Blockchain
    Dashboard -->|"Reads from"| Blockchain
    
    %% Shared resources
    Config -->|"Configures"| Bot
    Config -->|"Configures"| Dashboard
    Bot -->|"Writes to"| LogStore
    Bot -->|"Stores data in"| DataStore
    LogStore -->|"Read by"| Dashboard
    DataStore -->|"Read by"| Dashboard
    
    %% Legend
    subgraph Legend
        UserAction["User Action"]
        DataFlow["Data Flow"]
    end
    
    %% Styles
    classDef primary fill:#4287f5,stroke:#2956a3,color:white;
    classDef secondary fill:#42c5f5,stroke:#2994a3,color:white;
    classDef store fill:#f542a7,stroke:#a32956,color:white;
    
    class Bot,Dashboard primary;
    class Blockchain,User secondary;
    class Config,LogStore,DataStore store;
```

## Detailed Component Architecture

```mermaid
graph TD
    %% Main System Components
    user[User]
    
    %% Core Bot Components
    subgraph "Arbitrage Bot Core"
        main["main.py\n(Entry point)"]
        run_bot["run_bot.py\n(Bot runner)"]
        
        subgraph "Core Logic"
            path_finder["PathFinder\narbitrage_bot/core/path_finder.py"]
            balance_allocator["BalanceAllocator\narbitrage_bot/core/balance_allocator.py"]
            flash_loan["AsyncFlashLoanManager\narbitrage_bot/core/flash_loan_manager_async.py"]
            mev_protection["MEV Protection\narbitrage_bot/integration/mev_protection.py"]
        end
        
        subgraph "Infrastructure"
            dex_manager["DexManager\narbitrage_bot/core/dex/dex_manager.py"]
            web3_manager["Web3Manager\narbitrage_bot/core/web3/web3_manager.py"]
        end
        
        subgraph "DEX Implementations"
            base_dex["BaseDEX\n(Abstract)"]
            base_dex_v2["BaseDEXV2"]
            base_dex_v3["BaseDEXV3"]
            specific_dexes["Specific DEXes\n(BaseSwap, PancakeSwap, etc.)"]
        end
    end
    
    %% Dashboard Components
    subgraph "Dashboard System"
        old_dashboard["minimal_dashboard.py\n(Old Flask Dashboard)"]
        
        subgraph "New Dashboard"
            new_dashboard_app["app.py\n(FastAPI Application)"]
            templates["HTML Templates"]
            static_files["Static Files\n(CSS/JS)"]
            api_endpoints["API Endpoints"]
        end
    end
    
    %% External Systems
    subgraph "External Systems"
        blockchain["Blockchain\n(Base Network)"]
        dexes["DEXes"]
    end
    
    %% Shared Resources
    subgraph "Shared Resources"
        config_files["Configuration Files\n(configs/*.json)"]
        logs["Log Files\n(logs/)"]
        data_storage["Data Storage\n(data/)"]
    end
    
    %% Connections
    user -->|"Starts/Configures"| main
    user -->|"Monitors via"| old_dashboard
    user -->|"Monitors via"| new_dashboard_app
    
    main --> run_bot
    run_bot --> path_finder
    run_bot --> balance_allocator
    run_bot --> flash_loan
    run_bot --> mev_protection
    
    path_finder --> dex_manager
    balance_allocator --> dex_manager
    flash_loan --> dex_manager
    mev_protection --> dex_manager
    
    dex_manager --> web3_manager
    dex_manager --> base_dex
    
    base_dex --> base_dex_v2
    base_dex --> base_dex_v3
    base_dex_v2 --> specific_dexes
    base_dex_v3 --> specific_dexes
    
    web3_manager -->|"Interacts with"| blockchain
    specific_dexes -->|"Integrates with"| dexes
    dexes -->|"Part of"| blockchain
    
    %% Dashboard connections
    old_dashboard -->|"Uses"| web3_manager
    old_dashboard -->|"Monitors"| dex_manager
    
    new_dashboard_app -->|"Direct Web3 connection"| blockchain
    new_dashboard_app --> templates
    new_dashboard_app --> static_files
    new_dashboard_app --> api_endpoints
    
    %% Shared resource connections
    config_files -->|"Configures"| main
    config_files -->|"Configures"| old_dashboard
    config_files -->|"Configures"| new_dashboard_app
    
    run_bot -->|"Writes to"| logs
    run_bot -->|"Stores data in"| data_storage
    
    old_dashboard -->|"Reads from"| logs
    old_dashboard -->|"Reads from"| data_storage
    
    new_dashboard_app -->|"Reads from"| logs
    new_dashboard_app -->|"Reads from"| data_storage
```

## Communication Diagram

```mermaid
sequenceDiagram
    participant User
    participant Bot as Arbitrage Bot
    participant OldDash as Old Dashboard
    participant NewDash as New Dashboard
    participant Blockchain
    participant Config as Config Files
    participant Log as Log Files
    participant Data as Data Storage

    %% Initial setup
    User->>Bot: Start system
    User->>Config: Edit configuration
    Config->>Bot: Configure bot
    Config->>OldDash: Configure dashboard
    Config->>NewDash: Configure dashboard
    
    %% Bot operation
    loop Arbitrage Process
        Bot->>Blockchain: Check prices
        Blockchain-->>Bot: Return price data
        Bot->>Bot: Find arbitrage opportunity
        Bot->>Blockchain: Execute transaction
        Blockchain-->>Bot: Transaction result
        Bot->>Log: Log activity
        Bot->>Data: Store performance data
    end
    
    %% Dashboard monitoring
    User->>OldDash: Open dashboard
    OldDash->>Bot: Connect to Web3Manager
    Bot-->>OldDash: Share Web3 connection
    OldDash->>Log: Read logs
    OldDash->>Data: Read performance data
    OldDash-->>User: Display status
    
    %% New dashboard operation
    User->>NewDash: Open new dashboard
    NewDash->>Blockchain: Direct Web3 connection
    Blockchain-->>NewDash: Network status
    NewDash->>Log: Read logs
    NewDash->>Data: Read performance data
    NewDash->>Config: Read configuration
    NewDash-->>User: Display status
    
    %% Real-time updates
    loop Dashboard Updates
        Blockchain-->>Bot: New block/price changes
        Bot->>Log: Update logs
        Bot->>Data: Update performance data
        
        Blockchain-->>NewDash: New block/price changes
        Log-->>OldDash: Updated log data
        Data-->>OldDash: Updated performance data
        
        Log-->>NewDash: Updated log data
        Data-->>NewDash: Updated performance data
        
        OldDash-->>User: Update display
        NewDash-->>User: Update display
    end
```

## Directory Structure

```
d:/Listonian-bot/
│
├── main.py                        # Main entry point for the bot
├── run_bot.py                     # Bot runner script
├── minimal_dashboard.py           # Old dashboard implementation
├── start_dashboard.bat/.ps1       # Old dashboard starters
├── start_new_dashboard.bat/.ps1   # New dashboard starters
│
├── arbitrage_bot/                 # Core package
│   ├── __init__.py
│   ├── integration.py
│   │
│   ├── core/                      # Core bot functionality
│   │   ├── path_finder.py         # Finds arbitrage paths
│   │   ├── balance_allocator.py   # Manages balance allocation
│   │   ├── flash_loan_manager_async.py  # Flash loan handling
│   │   │
│   │   ├── dex/                   # DEX implementations
│   │   │   ├── __init__.py
│   │   │   ├── dex_manager.py     # Manages DEX connections
│   │   │   ├── base_dex.py        # Abstract base class
│   │   │   ├── base_dex_v2.py     # V2 DEX base class
│   │   │   ├── base_dex_v3.py     # V3 DEX base class
│   │   │   └── [specific DEXes]   # Individual DEX implementations
│   │   │
│   │   └── web3/                  # Web3 connectivity
│   │       ├── __init__.py
│   │       └── web3_manager.py    # Manages blockchain connections
│   │
│   ├── integration/               # Integration components
│   │   └── mev_protection.py      # MEV protection implementation
│   │
│   └── utils/                     # Utility modules
│       └── [utility modules]
│
├── configs/                       # Configuration
│   ├── config.json                # Main configuration
│   └── production.json            # Production configuration
│
├── new_dashboard/                 # New dashboard
│   ├── app.py                     # FastAPI application
│   ├── dashboard_requirements.txt # Dashboard dependencies
│   ├── start_dashboard.bat        # Dashboard starter (batch)
│   ├── start_dashboard.ps1        # Dashboard starter (PowerShell)
│   ├── README.md                  # Dashboard documentation
│   │
│   ├── templates/                 # HTML templates
│   │   └── index.html             # Main dashboard view
│   │
│   └── static/                    # Static files
│       ├── css/                   # CSS styles
│       │   └── styles.css         # Main stylesheet
│       └── js/                    # JavaScript files
│
├── logs/                          # Log files
│   ├── arbitrage.log              # Main bot logs
│   ├── new_dashboard.log          # New dashboard logs
│   └── minimal_dashboard.log      # Old dashboard logs
│
└── data/                          # Data storage
    ├── performance/               # Performance metrics
    ├── transactions/              # Transaction records
    └── market/                    # Market data
```

## Communication Mechanisms

### 1. Dashboard-Bot Communication

The most important relationships between the dashboard and the bot:

#### Old Dashboard
- **Direct Component Access**: The old dashboard directly uses the `Web3Manager` from the arbitrage bot package, creating a tight coupling.
- **Shared In-Memory State**: Because of this direct access, the old dashboard can access in-memory state of the bot components.
- **Disadvantage**: This tight coupling means errors in one component can affect the other, as seen in your troubleshooting.

#### New Dashboard
- **Loose Coupling**: The new dashboard doesn't directly access bot components.
- **Independent Web3 Connection**: Creates its own Web3 connection to the blockchain.
- **Shared Configuration**: Both systems read from the same configuration files.
- **Data Exchange via Files**: Both systems interact through shared log files and data storage.
- **Advantage**: Independence means failures in the bot won't affect dashboard functionality.

### 2. Shared Resources

Both the dashboard and bot share these resources:

- **Configuration Files**: Located in `configs/`, these JSON files configure both systems.
- **Log Files**: Bot writes to logs in `logs/`, both dashboards read from these.
- **Data Storage**: Bot stores performance and transaction data in `data/`, dashboards read from this.
- **Blockchain**: Both connect to the same blockchain network (Base).

### 3. Data Flow

The primary data flows in the system:

1. **Configuration Flow**:
   - User edits configuration files
   - Both bot and dashboards read configuration
   - Configuration dictates behavior of all components

2. **Operation Flow**:
   - Bot executes transactions and strategies
   - Bot writes logs and stores performance data
   - Dashboards read logs and data for display

3. **Monitoring Flow**:
   - Dashboards connect to blockchain
   - Dashboards read bot-generated data
   - Dashboards visualize state to user

## Key Architectural Decisions

1. **Old vs New Dashboard**:
   - Old dashboard: Tightly coupled with bot components
   - New dashboard: Independent implementation with loose coupling

2. **Communication Strategy**:
   - File-based communication (config, logs, data)
   - Independent blockchain access
   - No direct in-memory communication

3. **Resource Sharing**:
   - Configuration files for settings
   - Log files for activity records
   - Data storage for performance metrics
   - Blockchain for network state

4. **Separation of Concerns**:
   - Bot focuses on executing arbitrage strategies
   - Dashboard focuses on monitoring and visualization
   - Clear boundaries between components

This architecture allows for greater reliability and maintainability, reducing the chance of cascading failures that were observed with the previous dashboard implementation.