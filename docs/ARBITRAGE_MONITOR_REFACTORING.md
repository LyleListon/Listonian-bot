# ArbitrageMonitor Refactoring Plan

## Current Architecture Analysis

The current arbitrage system is divided across multiple components, each handling different aspects of the arbitrage workflow. However, based on the memory bank records, these components may not have clear boundaries and responsibilities, leading to a complex, hard-to-maintain system.

### Key Components in Current Architecture

1. **PathFinder**: 
   - Responsible for finding arbitrage paths across multiple DEXs
   - Contains basic path evaluation but limited execution capability
   - Lacks robust profitability analysis

2. **ArbitrageExecutor**:
   - Executes identified arbitrage opportunities
   - Handles transaction submission and monitoring
   - Contains business logic for determining when to execute

3. **OpportunityTracker**:
   - Tracks arbitrage opportunities over time
   - Performs analytics on historical opportunities
   - Manages the persistence of opportunity data

4. **TriangularArbitrage / StatisticalArbitrage**:
   - Specialized opportunity detection strategies
   - Duplicates some functionality from PathFinder
   - Lacks standardized interfaces with other components

5. **Event System**:
   - Provides communication between components
   - Lacks clear protocols for the arbitrage workflow

6. **Transaction & DEX Monitors**:
   - Monitors blockchain events and transactions
   - Dispersed across multiple components

## Issues with Current Architecture

1. **Unclear Responsibilities**:
   - Overlapping functionality between components
   - No clear workflow for the arbitrage process
   - Difficult to understand how components interact

2. **Tight Coupling**:
   - Components depend directly on each other
   - Changes in one component ripple through the system
   - Difficult to test components in isolation

3. **Inconsistent Interfaces**:
   - No standardized interfaces for opportunity detection
   - Different components use different data structures
   - Difficult to add new strategies or extensions

4. **Scattered Business Logic**:
   - Arbitrage decisions spread across multiple components
   - Risk management spread across components
   - No centralized strategy management

## Proposed Architecture

We will refactor the arbitrage system into a more modular architecture with clear boundaries and responsibilities:

```
┌───────────────────────────────────────────────────────────────────┐
│                       ArbitrageSystem                             │
│                                                                   │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────────┐    │
│  │ Opportunity   │   │ Execution     │   │ Analytics &       │    │
│  │ Discovery     │   │ Engine        │   │ Reporting         │    │
│  └───────┬───────┘   └───────┬───────┘   └─────────┬─────────┘    │
│          │                   │                     │              │
│  ┌───────┴───────┐   ┌───────┴───────┐   ┌─────────┴─────────┐    │
│  │ Strategy      │   │ Transaction   │   │ Performance       │    │
│  │ Manager       │   │ Manager       │   │ Monitor          │    │
│  └───────────────┘   └───────────────┘   └───────────────────┘    │
│                                                                   │
│                  ┌───────────────────────┐                        │
│                  │ Shared Event Bus      │                        │
│                  └───────────────────────┘                        │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### 1. Opportunity Discovery Subsystem

```
┌─────────────────────────────────────────────┐
│         OpportunityDiscoveryManager         │
│                                             │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │ PathFinder  │  │ OpportunityDetector │   │
│  └─────────────┘  └─────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ Strategy Implementation (Interface) │    │
│  │                                     │    │
│  │  ┌────────────────┐ ┌────────────┐  │    │
│  │  │ Triangular     │ │ Statistical │  │    │
│  │  │ Arbitrage      │ │ Arbitrage   │  │    │
│  │  └────────────────┘ └────────────┘  │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

**Key components:**
- **OpportunityDiscoveryManager**: Coordinates different strategies and provides a unified interface
- **PathFinder**: Refactored to focus only on path discovery, not execution or evaluation
- **OpportunityDetector**: Evaluates paths for potential profitability (initial screening)
- **Strategy Interface**: Common interface for different arbitrage strategies
- **Strategy Implementations**: Specific strategies with standardized interfaces

### 2. Execution Engine Subsystem

```
┌─────────────────────────────────────────────┐
│           ExecutionManager                  │
│                                             │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │ Opportunity │  │ Transaction         │   │
│  │ Validator   │  │ Builder             │   │
│  └─────────────┘  └─────────────────────┘   │
│                                             │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │ Flash Loan  │  │ Transaction         │   │
│  │ Manager     │  │ Monitor             │   │
│  └─────────────┘  └─────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ Execution Strategy (Interface)      │    │
│  │                                     │    │
│  │  ┌────────────────┐ ┌────────────┐  │    │
│  │  │ Standard       │ │ MEV        │  │    │
│  │  │ Execution      │ │ Protected  │  │    │
│  │  └────────────────┘ └────────────┘  │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

**Key components:**
- **ExecutionManager**: Coordinates the execution process
- **Opportunity Validator**: Performs detailed validation before execution
- **Transaction Builder**: Builds transaction data for execution 
- **Flash Loan Manager**: Manages flash loan operations (already unified)
- **Transaction Monitor**: Monitors transaction status and handles errors
- **Execution Strategy Interface**: Common interface for execution strategies
- **Execution Strategy Implementations**: Different execution approaches

### 3. Analytics & Reporting Subsystem

```
┌─────────────────────────────────────────────┐
│           AnalyticsManager                  │
│                                             │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │ Opportunity │  │ Performance         │   │
│  │ Tracker     │  │ Analyzer            │   │
│  └─────────────┘  └─────────────────────┘   │
│                                             │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │ Historical  │  │ Strategy            │   │
│  │ Data Store  │  │ Evaluator           │   │
│  └─────────────┘  └─────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ Reporting Interfaces                │    │
│  │                                     │    │
│  │  ┌────────────────┐ ┌────────────┐  │    │
│  │  │ Dashboard      │ │ Alerting   │  │    │
│  │  │ Reporter       │ │ System     │  │    │
│  │  └────────────────┘ └────────────┘  │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

**Key components:**
- **AnalyticsManager**: Coordinates analytics and reporting activities
- **Opportunity Tracker**: Tracks opportunity outcomes (refactored)
- **Performance Analyzer**: Analyzes system performance metrics
- **Historical Data Store**: Manages persistent storage of opportunity and performance data
- **Strategy Evaluator**: Evaluates strategy performance
- **Reporting Interfaces**: Standardized interfaces for different reporting methods

### 4. Shared Event Bus

The event bus will facilitate communication between components while maintaining loose coupling:

```
┌─────────────────────────────────────────────┐
│              EventBus                       │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ Event Types                         │    │
│  │                                     │    │
│  │ - OpportunityDiscovered             │    │
│  │ - OpportunityValidated              │    │
│  │ - ExecutionStarted                  │    │
│  │ - ExecutionCompleted                │    │
│  │ - ExecutionFailed                   │    │
│  │ - StrategyUpdated                   │    │
│  │ - MarketConditionChanged            │    │
│  └─────────────────────────────────────┘    │
│                                             │
└─────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Define Interfaces and Data Models

1. Define standardized interfaces for each component
2. Create common data models for sharing information
3. Define event types and payloads

### Phase 2: Implement Core Components

1. Implement the Opportunity Discovery subsystem
2. Implement the Execution Engine subsystem
3. Implement the Analytics & Reporting subsystem
4. Implement the Shared Event Bus

### Phase 3: Migrate Existing Code

1. Refactor existing components to match new interfaces
2. Create adapters where necessary for backward compatibility
3. Migrate business logic to appropriate components

### Phase 4: Integration and Testing

1. Integrate all components
2. Implement comprehensive testing
3. Performance testing and optimization

## Benefits of New Architecture

1. **Clear Separation of Concerns**:
   - Each component has a single responsibility
   - Easier to understand, maintain, and test
   - Easier to extend with new functionality

2. **Loose Coupling**:
   - Components communicate through well-defined interfaces
   - Changes in one component don't affect others
   - Easier to replace or upgrade components

3. **Standardized Interfaces**:
   - Consistent data models throughout the system
   - Easier to add new strategies or execution methods
   - Better interoperability between components

4. **Centralized Business Logic**:
   - Strategy decisions in dedicated components
   - Risk management in a single place
   - Clearer audit trail for decisions

5. **Better Testability**:
   - Components can be tested in isolation
   - Mock implementations for testing
   - Clearer success criteria for each component

6. **Improved Performance**:
   - Components can be optimized independently
   - Parallel processing where appropriate
   - Better resource management

This architecture provides a clear path for refactoring the ArbitrageMonitor functionality into a more maintainable and extensible system.