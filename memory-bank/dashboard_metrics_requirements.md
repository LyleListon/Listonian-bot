# Dashboard Metrics Requirements

## Overview
Comprehensive metrics tracking system for the arbitrage bot, focusing on key performance indicators across multiple domains.

## Core Metric Categories

### 1. Profitability Metrics
- Net profit after all fees by token pair
- ROI percentage per trade type
- Profit per gas unit (efficiency metric)
- Profit distribution by strategy type

### 2. DEX Performance
- Success rate by DEX pair (Aerodrome/Baseswap, Pancake/Uni, etc.)
- Cross-DEX arbitrage frequency and profitability
- DEX-specific slippage patterns
- Liquidity depth correlation with success

### 3. Flash Loan Metrics
- Balancer vs Aave success rate on Base
- Provider reliability during peak periods
- Flash loan cost impact on net profitability
- Maximum effective loan size by token

### 4. Execution Metrics
- Gas usage by strategy type
- MEV protection effectiveness
- Path length vs success rate correlation
- Execution time from discovery to completion

### 5. Token Performance
- cbETH/ETH opportunities across DEXes
- USDbC/USDC stability pair arbitrage frequency
- Base ecosystem tokens migration patterns
- Token volatility impact on success rate

### 6. System Performance
- Network congestion vs success rate
- Opportunity discovery rate by time of day
- NetworkX graph patterns for recurring opportunities
- Success rate with multi-path vs simple arbitrage

## Implementation Requirements

### Data Collection
- Real-time metrics gathering
- Efficient storage and retrieval
- Historical data aggregation
- Performance impact monitoring

### Visualization
- Interactive charts and graphs
- Real-time updates via WebSocket
- Customizable time ranges
- Drill-down capabilities

### Technical Considerations
- Memory-efficient storage
- Proper async handling
- Thread safety
- Resource cleanup

### Performance Goals
- Update latency < 100ms
- Minimal CPU overhead
- Efficient memory usage
- Clean resource management

## Implementation Phases

### Phase 1: Core Profitability
- Net profit tracking
- ROI calculations
- Gas efficiency metrics
- Strategy performance

### Phase 2: DEX & Flash Loans
- DEX success rates
- Flash loan analytics
- Cross-DEX metrics
- Provider reliability

### Phase 3: Advanced Analytics
- Token performance
- System metrics
- Network analysis
- Pattern recognition

## Success Criteria
- All metrics accurately tracked
- Real-time updates working
- Performance goals met
- Resource usage optimized