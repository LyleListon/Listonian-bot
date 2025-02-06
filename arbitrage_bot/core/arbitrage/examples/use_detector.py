"""Example script demonstrating arbitrage detection with ML predictions."""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.core.dex.dex_manager import create_dex_manager
from arbitrage_bot.core.data_collection.coordinator import DataCollectionCoordinator
from arbitrage_bot.core.ml.feature_pipeline.pipeline import FeaturePipeline
from arbitrage_bot.core.ml.models.manager import ModelManager
from arbitrage_bot.core.arbitrage.detector import AggressiveArbitrageDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def load_configs() -> Dict[str, Any]:
    """Load all configuration files."""
    configs = {}
    
    # Load feature pipeline config
    pipeline_config_path = Path(__file__).parent.parent.parent / 'ml' / 'feature_pipeline' / 'config' / 'default_config.yaml'
    with open(pipeline_config_path) as f:
        configs['pipeline'] = yaml.safe_load(f)
        
    # Load model config
    model_config_path = Path(__file__).parent.parent.parent / 'ml' / 'models' / 'config' / 'default_config.yaml'
    with open(model_config_path) as f:
        configs['model'] = yaml.safe_load(f)
        
    # Load arbitrage config
    arbitrage_config_path = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
    with open(arbitrage_config_path) as f:
        configs['arbitrage'] = yaml.safe_load(f)
        
    return configs

class OpportunityTracker:
    """Track and analyze arbitrage opportunities."""
    
    def __init__(self):
        self.opportunities = []
        self.trades = []
        self.profits = []
        
    def add_opportunity(self, opportunity: Dict[str, Any]):
        """Add new opportunity."""
        self.opportunities.append({
            'timestamp': datetime.utcnow(),
            'profit': opportunity['expected_profit'],
            'confidence': opportunity['confidence'],
            'path': opportunity['path']
        })
        
    def add_trade(self, trade: Dict[str, Any]):
        """Add executed trade."""
        self.trades.append({
            'timestamp': datetime.utcnow(),
            'profit': trade['profit'],
            'gas_cost': trade['gas_cost'],
            'execution_time': trade['execution_time']
        })
        self.profits.append(trade['profit'])
        
    def plot_performance(self):
        """Plot performance metrics."""
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Plot cumulative profits
        cumulative_profits = pd.Series(self.profits).cumsum()
        ax1.plot(cumulative_profits, label='Cumulative Profit')
        ax1.set_title('Cumulative Profit Over Time')
        ax1.set_xlabel('Trade Number')
        ax1.set_ylabel('Profit (USD)')
        ax1.legend()
        ax1.grid(True)
        
        # Plot opportunity vs execution scatter
        if self.opportunities and self.trades:
            opportunities_df = pd.DataFrame(self.opportunities)
            trades_df = pd.DataFrame(self.trades)
            
            ax2.scatter(
                opportunities_df['profit'],
                trades_df['profit'],
                alpha=0.5,
                label='Trades'
            )
            ax2.plot([0, max(opportunities_df['profit'])],
                    [0, max(opportunities_df['profit'])],
                    'r--', label='Perfect Execution')
            ax2.set_title('Expected vs Actual Profit')
            ax2.set_xlabel('Expected Profit (USD)')
            ax2.set_ylabel('Actual Profit (USD)')
            ax2.legend()
            ax2.grid(True)
            
        plt.tight_layout()
        plt.savefig('arbitrage_performance.png')
        plt.close()

async def main():
    """Run arbitrage detection example."""
    try:
        # Load configurations
        configs = await load_configs()
        logger.info("Configurations loaded")
        
        # Initialize managers
        web3_manager = await create_web3_manager()
        await web3_manager.connect()
        logger.info("Web3 manager initialized")
        
        dex_manager = await create_dex_manager(web3_manager)
        logger.info("DEX manager initialized")
        
        # Create data collection coordinator
        data_coordinator = DataCollectionCoordinator(configs['pipeline'])
        success = await data_coordinator.initialize(web3_manager, dex_manager)
        if not success:
            raise RuntimeError("Failed to initialize data collection system")
        logger.info("Data collection system initialized")
        
        # Create feature pipeline
        feature_pipeline = FeaturePipeline(data_coordinator, configs['pipeline'])
        await feature_pipeline.start()
        logger.info("Feature pipeline started")
        
        # Create model manager
        model_manager = ModelManager(feature_pipeline, configs['model'])
        await model_manager.start()
        logger.info("Model manager started")
        
        # Create arbitrage detector
        detector = AggressiveArbitrageDetector(
            model_manager,
            dex_manager,
            configs['arbitrage']
        )
        await detector.start()
        logger.info("Arbitrage detector started")
        
        # Create opportunity tracker
        tracker = OpportunityTracker()
        
        # Example 1: Monitor Opportunities
        logger.info("\nExample 1: Monitoring Opportunities")
        try:
            start_time = datetime.utcnow()
            
            while (datetime.utcnow() - start_time).total_seconds() < 300:  # 5 minutes
                # Get detector status
                status = detector.get_status()
                
                # Log current state
                logger.info(
                    f"Active Opportunities: {status['opportunities']}, "
                    f"Active Trades: {status['active_trades']}"
                )
                
                # Track opportunities
                for opp in detector.opportunities:
                    tracker.add_opportunity(opp.__dict__)
                    
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error monitoring opportunities: {e}")
            
        # Example 2: Risk Management
        logger.info("\nExample 2: Risk Management")
        try:
            # Get risk metrics
            risk_metrics = detector.get_status()['risk_metrics']
            
            logger.info("\nRisk Metrics:")
            logger.info(f"Volatility: {risk_metrics['volatility']:.4f}")
            logger.info(f"Drawdown: {risk_metrics['drawdown']:.2%}")
            logger.info(f"Sharpe Ratio: {risk_metrics['sharpe_ratio']:.2f}")
            logger.info(f"Win Rate: {risk_metrics['win_rate']:.2%}")
            
        except Exception as e:
            logger.error(f"Error checking risk metrics: {e}")
            
        # Example 3: Performance Analysis
        logger.info("\nExample 3: Performance Analysis")
        try:
            # Plot performance
            tracker.plot_performance()
            logger.info("Performance plot saved as 'arbitrage_performance.png'")
            
            # Calculate statistics
            if tracker.profits:
                total_profit = sum(tracker.profits)
                win_rate = len([p for p in tracker.profits if p > 0]) / len(tracker.profits)
                
                logger.info(f"\nTotal Profit: ${total_profit:.2f}")
                logger.info(f"Win Rate: {win_rate:.2%}")
                logger.info(f"Number of Trades: {len(tracker.trades)}")
                
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            
        # Stop components
        await detector.stop()
        await model_manager.stop()
        await feature_pipeline.stop()
        logger.info("Components stopped")
        
    except Exception as e:
        logger.error(f"Error in arbitrage example: {e}")
        raise
    finally:
        # Cleanup
        if 'web3_manager' in locals():
            await web3_manager.disconnect()
        logger.info("Example completed")

def run_example():
    """Run the example."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Example interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise

if __name__ == '__main__':
    run_example()

"""
Example Usage:

1. Basic monitoring:
   ```python
   # Initialize components
   detector = AggressiveArbitrageDetector(model_manager, dex_manager, config)
   await detector.start()
   
   # Monitor opportunities
   while True:
       status = detector.get_status()
       print(f"Active Opportunities: {status['opportunities']}")
       await asyncio.sleep(1)
   ```

2. Risk management:
   ```python
   # Get risk metrics
   metrics = detector.get_status()['risk_metrics']
   
   # Check risk limits
   if metrics['drawdown'] > 0.1:  # 10% drawdown
       print("Risk limit exceeded!")
   ```

3. Performance tracking:
   ```python
   # Track opportunities and trades
   tracker = OpportunityTracker()
   
   # Add new opportunity
   tracker.add_opportunity(opportunity)
   
   # Add executed trade
   tracker.add_trade(trade)
   
   # Plot performance
   tracker.plot_performance()
   ```
"""