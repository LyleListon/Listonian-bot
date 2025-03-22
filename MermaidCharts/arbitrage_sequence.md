sequenceDiagram
    participant MA as Market Analyzer
    participant ML as ML System
    participant MB as Memory Bank
    participant EX as Executor
    participant FL as Flash Loan Manager
    participant FB as Flashbots Provider
    participant BC as Blockchain

    %% Opportunity Discovery
    MA->>ML: Request opportunity scoring
    ML->>MB: Get historical data
    MB-->>ML: Return token metrics
    ML-->>MA: Return scored opportunities

    %% Execution Preparation
    MA->>EX: Submit best opportunity
    EX->>FL: Request flash loan bundle
    FL->>FB: Create transaction bundle

    %% Bundle Simulation
    FB->>BC: Simulate bundle
    BC-->>FB: Simulation results
    FB-->>FL: Bundle validation
    FL-->>EX: Loan + trade bundle

    %% Execution
    EX->>FB: Submit bundle
    FB->>BC: Private transaction
    BC-->>FB: Transaction receipt
    FB-->>EX: Execution status

    %% Update State
    EX->>MB: Store trade result
    MB->>ML: Update model
    ML-->>MA: Update strategy

    %% Feedback Loop
    Note over MA,BC: Continuous Monitoring & Learning
    MA->>MA: Monitor new opportunities
    ML->>ML: Refine predictions
    MB->>MB: Update metrics