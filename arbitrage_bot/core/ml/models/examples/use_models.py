"""Example script demonstrating ML model usage with feature pipeline."""

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
    pipeline_config_path = Path(__file__).parent.parent.parent / 'feature_pipeline' / 'config' / 'default_config.yaml'
    with open(pipeline_config_path) as f:
        configs['pipeline'] = yaml.safe_load(f)
        
    # Load model config
    model_config_path = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
    with open(model_config_path) as f:
        configs['model'] = yaml.safe_load(f)
        
    return configs

async def main():
    """Run ML model example."""
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
        
        # Example 1: Real-time Gas Price Prediction
        logger.info("\nExample 1: Gas Price Prediction")
        try:
            # Track predictions over time
            gas_predictions = []
            start_time = datetime.utcnow()
            
            while (datetime.utcnow() - start_time).total_seconds() < 60:
                # Get prediction
                prediction = await model_manager.predict_gas_price()
                gas_predictions.append(prediction)
                
                # Log prediction
                logger.info(
                    f"Gas Price: {prediction['predicted_price']:.2f} "
                    f"(±{prediction['uncertainty']:.2f}) "
                    f"Confidence: {prediction['confidence']:.2%}"
                )
                
                await asyncio.sleep(1)
                
            # Analyze predictions
            df = pd.DataFrame(gas_predictions)
            logger.info("\nPrediction Statistics:")
            logger.info(df['predicted_price'].describe())
            
            # Plot predictions
            plt.figure(figsize=(10, 6))
            plt.plot(df['predicted_price'], label='Predicted Price')
            plt.fill_between(
                range(len(df)),
                df['predicted_price'] - df['uncertainty'],
                df['predicted_price'] + df['uncertainty'],
                alpha=0.3
            )
            plt.title('Gas Price Predictions with Uncertainty')
            plt.xlabel('Time')
            plt.ylabel('Gas Price (Gwei)')
            plt.legend()
            plt.savefig('gas_predictions.png')
            plt.close()
            
        except Exception as e:
            logger.error(f"Error in gas price example: {e}")
            
        # Example 2: Liquidity Prediction
        logger.info("\nExample 2: Liquidity Prediction")
        try:
            # Get prediction
            prediction = await model_manager.predict_liquidity()
            
            logger.info("\nLiquidity Metrics:")
            logger.info(f"Total Liquidity: {prediction['liquidity']['total']:.2f}")
            logger.info(f"Volume: {prediction['liquidity']['volume']:.2f}")
            logger.info(f"Price Impact: {prediction['liquidity']['impact']:.2%}")
            logger.info(f"Confidence: {prediction['confidence']:.2%}")
            
        except Exception as e:
            logger.error(f"Error in liquidity example: {e}")
            
        # Example 3: Model Performance Monitoring
        logger.info("\nExample 3: Performance Monitoring")
        try:
            # Get performance stats
            stats = model_manager.get_performance_stats()
            
            logger.info("\nGas Price Model:")
            logger.info(f"Loss: {stats['gas']['model_stats']['loss_mean']:.4f}")
            logger.info(f"Updates: {stats['gas']['model_stats']['updates']}")
            
            logger.info("\nLiquidity Model:")
            logger.info(f"Loss: {stats['liquidity']['model_stats']['loss_mean']:.4f}")
            logger.info(f"Updates: {stats['liquidity']['model_stats']['updates']}")
            
        except Exception as e:
            logger.error(f"Error in monitoring example: {e}")
            
        # Stop components
        await model_manager.stop()
        await feature_pipeline.stop()
        logger.info("Components stopped")
        
    except Exception as e:
        logger.error(f"Error in ML model example: {e}")
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

1. Basic prediction:
   ```python
   # Initialize components
   model_manager = ModelManager(feature_pipeline, config)
   await model_manager.start()
   
   # Get predictions
   gas_price = await model_manager.predict_gas_price()
   liquidity = await model_manager.predict_liquidity()
   
   print(f"Gas Price: {gas_price['predicted_price']}")
   print(f"Liquidity: {liquidity['liquidity']['total']}")
   ```

2. Continuous monitoring:
   ```python
   while True:
       # Get predictions
       prediction = await model_manager.predict_gas_price()
       
       # Check confidence
       if prediction['confidence'] > 0.8:
           print(f"High confidence prediction: {prediction['predicted_price']}")
           
       await asyncio.sleep(1)
   ```

3. Performance tracking:
   ```python
   # Monitor model performance
   while True:
       stats = model_manager.get_performance_stats()
       print(f"Gas Model Loss: {stats['gas']['model_stats']['loss_mean']}")
       print(f"Liquidity Model Loss: {stats['liquidity']['model_stats']['loss_mean']}")
       await asyncio.sleep(60)
   ```

4. Custom prediction intervals:
   ```python
   # Get prediction with custom confidence interval
   prediction = await model_manager.predict_gas_price()
   lower = prediction['predicted_price'] - 2 * prediction['uncertainty']
   upper = prediction['predicted_price'] + 2 * prediction['uncertainty']
   print(f"95% Confidence Interval: [{lower:.2f}, {upper:.2f}]")
   ```
"""