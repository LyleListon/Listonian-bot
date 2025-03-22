flowchart TD
    %% Main Components
    Web3[Web3 Manager] --> |Chain Interaction| Executor
    Flash[Flash Loan Manager] --> |Loan Operations| Executor
    Market[Market Analyzer] --> |Opportunities| Executor
    ML[ML System] --> |Opportunity Scoring| Market
    Memory[Memory Bank] --> |Historical Data| ML
    DEX[DEX Manager] --> |Pool Data| Market
    Gas[Gas Optimizer] --> |Gas Strategy| Executor
    Flash[Flash Loan Manager] --> |Bundle Creation| Flashbots
    
    %% Core Components
    subgraph Core ["Core Components"]
        Executor[Arbitrage Executor]
        Flashbots[Flashbots Provider]
        Flash
        Market
    end

    %% Analytics Components
    subgraph Analytics ["Analytics & ML"]
        ML
        Memory
        Gas
    end

    %% DEX Integration
    subgraph DEX Integration ["DEX Integration"]
        DEX --> |Price Data| Market
        DEX --> |Pool Access| Flash
        DEX --> |Trade Execution| Executor
    end

    %% Data Flow
    Executor --> |Trade Results| Memory
    Flashbots --> |Bundle Results| Memory
    Market --> |Price Updates| Memory
    Memory --> |Success Rates| Market
    Gas --> |Gas Estimates| Flashbots
    
    %% External Interactions
    Blockchain((Blockchain))
    Web3 --> Blockchain
    Flashbots --> |Bundle Submission| Blockchain
    DEX --> |Contract Calls| Blockchain

    %% Styling
    classDef core fill:#f9f,stroke:#333,stroke-width:2px
    classDef analytics fill:#bbf,stroke:#333,stroke-width:2px
    classDef dex fill:#bfb,stroke:#333,stroke-width:2px
    classDef external fill:#ddd,stroke:#333,stroke-width:2px
    
    class Executor,Flashbots,Flash,Market core
    class ML,Memory,Gas analytics
    class DEX dex
    class Blockchain external