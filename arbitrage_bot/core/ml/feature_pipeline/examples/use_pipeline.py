"""Example script demonstrating feature pipeline usage."""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from datetime import datetime, timedelta

from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.core.dex.dex_manager import create_dex_manager
from arbitrage_bot.core.data_collection.coordinator import DataCollectionCoordinator
from arbitrage_bot.core.ml.feature_pipeline.pipeline import FeaturePipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def load_config() -> Dict[str, Any]:
    """Load feature pipeline configuration."""
    config_path = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
    with open(config_path) as f:
        return yaml.safe_load(f)

async def main():
    """Run feature pipeline example."""
    try:
        # Load configuration
        config = await load_config()
        logger.info("Configuration loaded")
        
        # Initialize managers
        web3_manager = await create_web3_manager()
        await web3_manager.connect()
        logger.info("Web3 manager initialized")
        
        dex_manager = await create_dex_manager(web3_manager)
        logger.info("DEX manager initialized")
        
        # Create data collection coordinator
        data_coordinator = DataCollectionCoordinator(config)
        success = await data_coordinator.initialize(web3_manager, dex_manager)
        if not success:
            raise RuntimeError("Failed to initialize data collection system")
        logger.info("Data collection system initialized")
        
        # Create feature pipeline
        pipeline = FeaturePipeline(data_coordinator, config)
        await pipeline.start()
        logger.info("Feature pipeline started")
        
        # Example 1: Real-time Feature Collection
        logger.info("\nExample 1: Real-time Features")
        try:
            # Collect features for 30 seconds
            start_time = datetime.utcnow()
            feature_history = []
            
            while (datetime.utcnow() - start_time).total_seconds() < 30:
                # Get minimal feature set (real-time only)
                features = await pipeline.get_features('minimal')
                feature_history.append(features)
                
                # Log some key metrics
                if 'gas' in features:
                    logger.info(f"Gas Price: {features['gas'].get('base_fee', 0):.2f}")
                if 'liquidity' in features:
                    logger.info(f"Total Liquidity: {features['liquidity'].get('total_liquidity', 0):.2f}")
                    
                await asyncio.sleep(1)
                
            # Analyze collected features
            df = pd.DataFrame(feature_history)
            logger.info("\nFeature Statistics:")
            logger.info(df.describe())
            
        except Exception as e:
            logger.error(f"Error in real-time example: {e}")
            
        # Example 2: Batch Feature Collection
        logger.info("\nExample 2: Batch Features")
        try:
            # Get full feature set (includes batch features)
            features = await pipeline.get_features('full')
            
            logger.info("\nAvailable Feature Groups:")
            for group, values in features.items():
                logger.info(f"{group}: {len(values)} features")
                
            # Get as numpy array for ML models
            feature_vector, feature_names = await pipeline.get_feature_vector('full')
            logger.info(f"\nFeature Vector Shape: {feature_vector.shape}")
            logger.info(f"Number of Features: {len(feature_names)}")
            
        except Exception as e:
            logger.error(f"Error in batch example: {e}")
            
        # Example 3: Feature Validation
        logger.info("\nExample 3: Feature Validation")
        try:
            # Get features and validate
            features = await pipeline.get_features('standard')
            is_valid, error = await pipeline.validate_features(features)
            
            if is_valid:
                logger.info("Features validated successfully")
            else:
                logger.warning(f"Feature validation failed: {error}")
                
        except Exception as e:
            logger.error(f"Error in validation example: {e}")
            
        # Example 4: Performance Monitoring
        logger.info("\nExample 4: Performance Monitoring")
        try:
            # Get performance stats
            stats = pipeline.get_performance_stats()
            
            logger.info("\nPerformance Metrics:")
            logger.info(f"Average Computation Time: {stats['computation_time']['mean']:.3f}s")
            logger.info(f"Feature Counts: {stats['feature_counts']}")
            logger.info(f"Error Counts: {stats['error_counts']}")
            
        except Exception as e:
            logger.error(f"Error in monitoring example: {e}")
            
        # Stop pipeline
        await pipeline.stop()
        logger.info("Feature pipeline stopped")
        
    except Exception as e:
        logger.error(f"Error in feature pipeline example: {e}")
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

1. Basic feature collection:
   ```python
   # Initialize pipeline
   pipeline = FeaturePipeline(data_coordinator, config)
   await pipeline.start()
   
   # Get real-time features
   features = await pipeline.get_features('minimal')
   print(f"Gas Price: {features['gas']['base_fee']}")
   ```

2. ML model integration:
   ```python
   # Get feature vector for ML model
   X, feature_names = await pipeline.get_feature_vector('full')
   
   # Make prediction
   prediction = model.predict(X.reshape(1, -1))
   print(f"Prediction: {prediction}")
   ```

3. Custom feature sets:
   ```python
   # Define custom feature set in config
   config['feature_sets']['custom'] = {
       'groups': ['gas', 'technical'],
       'update_interval': 1
   }
   
   # Get custom feature set
   features = await pipeline.get_features('custom')
   ```

4. Performance monitoring:
   ```python
   # Monitor pipeline performance
   while True:
       stats = pipeline.get_performance_stats()
       print(f"Computation Time: {stats['computation_time']['mean']:.3f}s")
       await asyncio.sleep(60)
   ```
"""