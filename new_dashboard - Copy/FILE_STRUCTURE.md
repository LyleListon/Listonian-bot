# Arbitrage Bot Project File Structure

This document provides a visual representation of the project's file structure and the relationships between components.

## Directory Structure

```mermaid
graph TD
    subgraph "Root Directory"
        start_new_dashboard.bat["start_new_dashboard.bat\n(Entry point - batch)"]
        start_new_dashboard.ps1["start_new_dashboard.ps1\n(Entry point - PowerShell)"]
        
        subgraph "Main Project"
            main.py["main.py\n(Main application)"]
            run_bot.py["run_bot.py\n(Bot runner)"]
            deploy_production.ps1["deploy_production.ps1\n(Deployment script)"]
            requirements.txt["requirements.txt\n(Main dependencies)"]
            
            subgraph "Core Modules"
                arbitrage_bot["arbitrage_bot/\n(Core package)"]
                arbitrage_bot_core["arbitrage_bot/core/\n(Core functionality)"]
                arbitrage_bot_dex["arbitrage_bot/core/dex/\n(DEX implementations)"]
                arbitrage_bot_web3["arbitrage_bot/core/web3/\n(Blockchain interactions)"]
                arbitrage_bot_flash["arbitrage_bot/core/flash_loan_manager_async.py\n(Flash loan handling)"]
                arbitrage_bot_mev["arbitrage_bot/integration/mev_protection.py\n(MEV protection)"]
            end
            
            configs_dir["configs/\n(Configuration files)"]
            configs_prod["configs/production.json\n(Production config)"]
            configs_main["configs/config.json\n(Main config)"]
            
            old_dashboard_files["minimal_dashboard.py\n(Old dashboard)"]
            old_dashboard_dir["minimal_dashboard/\n(Old dashboard files)"]
            start_dashboard_script["start_dashboard.bat/.ps1\n(Old dashboard starters)"]
        end
        
        subgraph "New Dashboard"
            dashboard_dir["new_dashboard/\n(New dashboard package)"]
            app["new_dashboard/app.py\n(FastAPI application)"]
            dashboard_start_bat["new_dashboard/start_dashboard.bat\n(Dashboard starter - batch)"]
            dashboard_start_ps1["new_dashboard/start_dashboard.ps1\n(Dashboard starter - PowerShell)"]
            dashboard_reqs["new_dashboard/dashboard_requirements.txt\n(Dashboard dependencies)"]
            dashboard_readme["new_dashboard/README.md\n(Dashboard documentation)"]
            
            subgraph "Static Files"
                static["new_dashboard/static/\n(Static files directory)"]
                css["new_dashboard/static/css/styles.css\n(CSS styles)"]
                js["new_dashboard/static/js/\n(JavaScript files)"]
            end
            
            subgraph "Templates"
                templates["new_dashboard/templates/\n(Template directory)"]
                index["new_dashboard/templates/index.html\n(Dashboard UI template)"]
            end
        end
    end
    
    %% Relationships
    start_new_dashboard.bat --> dashboard_start_bat
    start_new_dashboard.ps1 --> dashboard_start_ps1
    
    dashboard_start_bat --> app
    dashboard_start_ps1 --> app
    
    app --> static
    app --> templates
    app --> configs_main
    app --> configs_prod
    
    static --> css
    static --> js
    
    templates --> index
    
    app -. "Reads configuration from" .-> configs_main
    app -. "Reads configuration from" .-> configs_prod
    
    %% Old dashboard relationship to new
    old_dashboard_files -. "Replaced by" .-> app
    old_dashboard_dir -. "Replaced by" .-> dashboard_dir
    start_dashboard_script -. "Replaced by" .-> dashboard_start_bat
    start_dashboard_script -. "Replaced by" .-> dashboard_start_ps1
```

## Component Relationships

```mermaid
flowchart TD
    subgraph "User Interaction"
        User["User"]
        Scripts["Start Scripts\n(.bat/.ps1)"]
        Dashboard["Dashboard UI"]
        Config["Configuration\n(JSON/ENV)"]
    end
    
    subgraph "Dashboard Components"
        FastAPI["FastAPI Backend\n(app.py)"]
        Templates["HTML Templates\n(index.html)"]
        CSS["CSS Styling\n(styles.css)"]
        API["REST API\n(/api/status)"]
    end
    
    subgraph "External Connections"
        Web3["Web3 Connection"]
        DEXes["DEX Status"]
        Blockchain["Blockchain\n(Base Network)"]
    end
    
    User --> Scripts
    Scripts --> FastAPI
    FastAPI --> Templates
    Templates --> CSS
    FastAPI --> API
    Dashboard --> API
    User --> Dashboard
    User --> Config
    Config --> FastAPI
    
    FastAPI --> Web3
    Web3 --> Blockchain
    FastAPI --> DEXes
    
    %% Feedback loop
    Blockchain --> API
    API --> Dashboard
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant StartScript as Start Script (.bat/.ps1)
    participant Dashboard as Dashboard (app.py)
    participant Web3 as Web3 Connection
    participant Blockchain as Blockchain
    participant ConfigFile as Configuration Files
    
    User->>StartScript: Execute script
    StartScript->>Dashboard: Launch application
    Dashboard->>ConfigFile: Load configuration
    Dashboard->>Web3: Initialize connection
    Web3->>Blockchain: Connect to network
    Blockchain-->>Web3: Return network status
    Web3-->>Dashboard: Connection status & data
    
    loop Every 30 seconds
        Dashboard->>Web3: Request updates
        Web3->>Blockchain: Fetch current data
        Blockchain-->>Web3: Return blockchain data
        Web3-->>Dashboard: Send updated data
        Dashboard-->>User: Display updated UI
    end
    
    User->>Dashboard: Request data refresh
    Dashboard->>Web3: Request data
    Web3->>Blockchain: Fetch data
    Blockchain-->>Web3: Return data
    Web3-->>Dashboard: Process data
    Dashboard-->>User: Display refreshed data
```

## File Descriptions

### Entry Points
- `start_new_dashboard.bat` / `start_new_dashboard.ps1`: Root-level scripts to launch the dashboard
- `new_dashboard/start_dashboard.bat` / `new_dashboard/start_dashboard.ps1`: Internal scripts for dashboard startup

### Dashboard Core
- `new_dashboard/app.py`: Main FastAPI application that processes requests and serves the dashboard
- `new_dashboard/dashboard_requirements.txt`: Lists all Python dependencies for the dashboard
- `new_dashboard/README.md`: Documentation for the dashboard setup and usage

### UI Components
- `new_dashboard/templates/index.html`: HTML template for the dashboard UI
- `new_dashboard/static/css/styles.css`: CSS styling for the dashboard

### Configuration
- `configs/config.json`: Main configuration file for the arbitrage system
- `configs/production.json`: Production-specific configuration

### Old Dashboard (Being Replaced)
- `minimal_dashboard.py`: Old Flask-based dashboard implementation
- `start_dashboard.bat` / `start_dashboard.ps1`: Old dashboard startup scripts

## Implementation Notes

1. The new dashboard is a standalone component that reads from the same configuration files as the main arbitrage system.

2. It connects directly to the blockchain using Web3.py rather than relying on the main system's components.

3. This approach increases reliability by reducing dependencies and simplifying the architecture.

4. Data is refreshed automatically every 30 seconds, with an option for manual refresh.

5. The modular design allows for easier maintenance and extension.