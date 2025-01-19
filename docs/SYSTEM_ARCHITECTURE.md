# System Architecture

The project is organized into several key components and layers, each responsible for specific functionalities within the arbitrage trading system.

## Blockchain Layer

- **Smart Contracts**: These are the blockchain-based contracts deployed on various networks. They handle on-chain logic required for executing trades and interacting with decentralized exchanges (DEXes).
- **DEX Registry**: A component that interacts with different DEXes, maintaining a list of available exchanges. It facilitates the discovery and utilization of multiple DEX platforms for trading.
- **Price Feed Registry**: Manages connections to external price oracles and data feeds. It provides up-to-date pricing information essential for making informed trading decisions.

## Trading Execution

- **Arbitrage Detector**: Monitors the market across multiple exchanges to identify arbitrage opportunities where price discrepancies exist.
- **Trade Router**: Responsible for routing trade instructions to the appropriate exchanges based on the opportunities identified by the Arbitrage Detector.
- **Risk Manager**: Validates proposed trades against risk management criteria to ensure they meet safety and compliance standards before execution.

## Machine Learning

- **Predictive Models**: Employs machine learning algorithms to predict market movements and trends, aiding in proactive decision-making.
- **Reinforcement Learning Models**: Uses reinforcement learning to adapt and optimize trading strategies over time based on market feedback.
- **Evolutionary Optimizer**: Utilizes evolutionary algorithms to fine-tune model parameters and improve the performance of predictive models.

## Monitoring Dashboard

- **Real-time Price Monitoring**: 
  - Tracks prices across multiple DEXes (BaseSwap, Aerodrome)
  - Displays live price comparisons for key trading pairs (WETH/USDC, WETH/DAI, USDC/DAI)
  - Calculates and shows real-time spread percentages
  - Updates automatically via WebSocket connection

- **System Status Monitoring**:
  - CPU and Memory usage tracking
  - Network statistics and connection monitoring
  - System health indicators with warning thresholds
  - Real-time performance metrics

- **Trading Performance**:
  - Total opportunities tracked
  - Average spread calculations
  - Profit monitoring (potential and realized)
  - Trade execution statistics

- **Technical Implementation**:
  - Flask-based web server with SocketIO for real-time updates
  - Modular architecture with separate monitoring and data collection components
  - Efficient data caching using TokenOptimizer
  - Responsive web interface with real-time data updates

## Configuration

- **Config Loader**: Handles the loading and management of configuration settings for all system components, ensuring consistency and flexibility.
- **Network Config**: Contains configuration details specific to different blockchain networks, such as RPC endpoints and network IDs.

## Interactions Between Components

- The **Smart Contracts** interact with both the **DEX Registry** and **Price Feed Registry** to execute trades and obtain necessary market data.
- The **Arbitrage Detector** continuously scans for opportunities and communicates viable trades to the **Trade Router**.
- The **Trade Router** consults the **Risk Manager** to validate trades before execution, adhering to defined risk parameters.
- **Predictive Models** and **Reinforcement Learning Models** provide strategic insights to the **Arbitrage Detector**, enhancing its ability to identify opportunities.
- The **Evolutionary Optimizer** works to improve the **Predictive Models** by optimizing their parameters.
- The **Monitoring Dashboard** interfaces with all components to provide real-time visibility into system operations and performance.

## Additional Notes

- **Blockchain Layer**: Supports multi-chain and cross-DEX operations, enabling broad market access.
- **Machine Learning Components**: Implement advanced strategies for market prediction and strategy optimization.
- **Dashboard**: Offers a user-friendly interface for monitoring and controlling the system.
- **Modularity**: The system's modular design allows for easy maintenance and scalability.

## Running the System

1. Start the main arbitrage bot:
   ```bash
   python run.py
   ```

2. Launch the monitoring dashboard:
   ```bash
   python -m dashboard.enhanced_app
   ```

3. Access the dashboard at http://localhost:5002 to view:
   - Real-time price monitoring
   - System status and health
   - Trading performance metrics
   - Network statistics
