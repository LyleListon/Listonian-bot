# Product Context

## Purpose
The Listonian-bot is an advanced arbitrage trading system designed to maximize profits by identifying and executing trading opportunities across multiple decentralized exchanges (DEXes) on the Base network, with comprehensive real-time reporting through its dashboard.

## Core Functions
1. **Profit Detection**
   - Real-time monitoring of price discrepancies across DEXes
   - Advanced arbitrage opportunity identification
   - Profit calculation with gas cost consideration
   - Multi-path opportunity analysis
   - Risk assessment and validation

2. **Trade Execution**
   - Automated trade execution on identified opportunities
   - Gas-optimized transaction handling
   - Multi-DEX routing for maximum profit
   - Real-time transaction monitoring
   - Slippage protection and validation

3. **Performance Reporting**
   - Real-time profit tracking dashboard
   - Trade execution analytics
   - Performance metrics visualization
   - System health monitoring
   - Gas optimization insights

## Problems Solved
1. Market Inefficiencies: Capitalizes on price discrepancies between different DEXes
2. Speed of Execution: Automates the detection and execution of profitable trades
3. Risk Management: Implements robust validation and safety checks
4. Market Analysis: Utilizes ML models for predictive analysis
5. Performance Monitoring: Provides real-time insights through a comprehensive dashboard

## Core Functionality
1. **Arbitrage Detection**
   - Monitors active DEXes:
     * BaseSwap (V2)
     * SwapBased (V2)
     * PancakeSwap (V3)
     * Aerodrome
   - Identifies price discrepancies
   - Calculates potential profit opportunities
   - Validates trade viability

2. **Trade Execution**
   - Smart contract interaction for trade execution
   - Configuration-based DEX management
   - Selective DEX initialization
   - Risk validation before trades
   - Multi-DEX routing capabilities

3. **Market Analysis**
   - Real-time price analysis
   - Profit opportunity identification
   - Market depth analysis
   - DEX-specific performance tracking

4. **System Monitoring**
   - Real-time profit monitoring dashboard
   - Trade execution tracking
   - Performance metrics and analytics
   - Success rate monitoring
   - Gas optimization tracking

## Success Criteria
1. Profitable Trades
   - Consistent identification of profitable opportunities
   - Successful trade execution
   - Positive ROI after gas costs
   - Optimal DEX selection
   - Maximum profit capture

2. System Performance
   - Minimal latency in opportunity detection
   - High reliability in trade execution
   - Robust error handling and recovery
   - Efficient DEX interaction
   - Real-time profit tracking

3. Risk Management
   - Effective validation of trade opportunities
   - Protection against market manipulation
   - Proper handling of failed transactions
   - DEX-specific risk assessment
   - Profit protection measures

## Integration Points
1. Blockchain Networks
   - Base Network (Chain ID: 8453)
   - Production smart contract deployment
   - Gas optimization
   - DEX protocol support (V2/V3)

2. External Services
   - Live price feed integration
   - Real-time market data
   - Analytics and monitoring tools
   - DEX status monitoring

## DEX Strategy
1. **Active DEXes**
   - BaseSwap: Primary V2 liquidity source
   - SwapBased: Additional V2 opportunities
   - PancakeSwap: V3 concentrated liquidity
   - Aerodrome: Additional liquidity source

2. **Configuration Management**
   - Dynamic DEX enablement
   - Protocol-specific implementations
   - Health monitoring and recovery
   - Performance optimization
   - Profit maximization settings

Last Updated: 2025-02-12
