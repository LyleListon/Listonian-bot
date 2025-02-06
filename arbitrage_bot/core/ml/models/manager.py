"""Model manager for coordinating predictors and feature pipeline."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
import torch

from ..feature_pipeline.pipeline import FeaturePipeline
from .predictors import GasPricePredictor, LiquidityPredictor

class ModelManager:
    """Manage ML models and coordinate with feature pipeline."""
    
    def __init__(self, feature_pipeline: FeaturePipeline, config: Dict[str, Any]):
        """
        Initialize model manager.
        
        Args:
            feature_pipeline: Feature pipeline instance
            config: Configuration dictionary containing:
                - update_interval: How often to update models
                - model_configs: Configurations for each model
                - performance_thresholds: Performance monitoring thresholds
        """
        self.feature_pipeline = feature_pipeline
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize models
        self.models = {
            'gas': GasPricePredictor(config['model_configs']['gas']),
            'liquidity': LiquidityPredictor(config['model_configs']['liquidity'])
        }
        
        # Track predictions and performance
        self.predictions = {
            'gas': {
                'history': [],
                'accuracy': [],
                'last_prediction': None
            },
            'liquidity': {
                'history': [],
                'accuracy': [],
                'last_prediction': None
            }
        }
        
        self._running = False
        self._update_task = None
        
    async def start(self):
        """Start model manager."""
        try:
            self._running = True
            self._update_task = asyncio.create_task(self._update_loop())
            self.logger.info("Model manager started")
            
        except Exception as e:
            self.logger.error(f"Error starting model manager: {e}")
            raise
            
    async def stop(self):
        """Stop model manager."""
        try:
            self._running = False
            if self._update_task:
                self._update_task.cancel()
                try:
                    await self._update_task
                except asyncio.CancelledError:
                    pass
            self.logger.info("Model manager stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping model manager: {e}")
            
    async def predict_gas_price(self) -> Dict[str, Any]:
        """
        Get gas price prediction with metadata.
        
        Returns:
            Dictionary containing:
                - predicted_price: Predicted gas price
                - uncertainty: Prediction uncertainty
                - confidence: Prediction confidence
                - metadata: Additional prediction metadata
        """
        try:
            # Get latest features
            features = await self.feature_pipeline.get_feature_vector('minimal')
            
            # Make prediction
            price, uncertainty, metadata = self.models['gas'].predict(features)
            
            prediction = {
                'predicted_price': float(price),
                'uncertainty': float(uncertainty),
                'confidence': metadata['confidence'],
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': metadata
            }
            
            # Update tracking
            self.predictions['gas']['history'].append(prediction)
            self.predictions['gas']['last_prediction'] = prediction
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Error predicting gas price: {e}")
            return {
                'predicted_price': 0.0,
                'uncertainty': float('inf'),
                'confidence': 0.0,
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
            
    async def predict_liquidity(self) -> Dict[str, Any]:
        """
        Get liquidity prediction with metadata.
        
        Returns:
            Dictionary containing:
                - liquidity: Predicted liquidity metrics
                - uncertainty: Prediction uncertainty
                - confidence: Prediction confidence
                - metadata: Additional prediction metadata
        """
        try:
            # Get latest features
            features = await self.feature_pipeline.get_feature_vector('standard')
            
            # Make prediction
            metrics, uncertainty, metadata = self.models['liquidity'].predict(features)
            
            prediction = {
                'liquidity': {
                    'total': float(metrics[0]),
                    'volume': float(metrics[1]),
                    'impact': float(metrics[2])
                },
                'uncertainty': float(uncertainty),
                'confidence': metadata['confidence'],
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': metadata
            }
            
            # Update tracking
            self.predictions['liquidity']['history'].append(prediction)
            self.predictions['liquidity']['last_prediction'] = prediction
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Error predicting liquidity: {e}")
            return {
                'liquidity': {'total': 0.0, 'volume': 0.0, 'impact': 0.0},
                'uncertainty': float('inf'),
                'confidence': 0.0,
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
            
    async def _update_loop(self):
        """Update models with new data continuously."""
        while self._running:
            try:
                # Get latest features and targets
                features = await self.feature_pipeline.get_feature_vector('full')
                
                # Update gas price model
                gas_target = await self._get_gas_target()
                if gas_target is not None:
                    self.models['gas'].update(features, gas_target)
                    
                # Update liquidity model
                liquidity_target = await self._get_liquidity_target()
                if liquidity_target is not None:
                    self.models['liquidity'].update(features, liquidity_target)
                    
                # Monitor performance
                await self._monitor_performance()
                
                # Wait for next update
                await asyncio.sleep(self.config['update_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in update loop: {e}")
                await asyncio.sleep(1)
                
    async def _get_gas_target(self) -> Optional[np.ndarray]:
        """Get latest gas price target from feature pipeline."""
        try:
            features = await self.feature_pipeline.get_features('minimal')
            if 'gas' in features:
                return np.array([
                    features['gas']['base_fee'],
                    features['gas'].get('volatility', 0.0)
                ])
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting gas target: {e}")
            return None
            
    async def _get_liquidity_target(self) -> Optional[np.ndarray]:
        """Get latest liquidity target from feature pipeline."""
        try:
            features = await self.feature_pipeline.get_features('standard')
            if 'liquidity' in features:
                return np.array([
                    features['liquidity']['total_liquidity'],
                    features['liquidity']['volume'],
                    features['liquidity']['price_impact'],
                    features['liquidity'].get('volatility', 0.0)
                ])
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting liquidity target: {e}")
            return None
            
    async def _monitor_performance(self):
        """Monitor model performance and log issues."""
        try:
            thresholds = self.config['performance_thresholds']
            
            # Check gas price model
            gas_stats = self.models['gas'].get_training_stats()
            if gas_stats['loss_mean'] > thresholds['max_gas_loss']:
                self.logger.warning(
                    f"Gas price model loss ({gas_stats['loss_mean']:.4f}) "
                    f"exceeds threshold ({thresholds['max_gas_loss']})"
                )
                
            # Check liquidity model
            liquidity_stats = self.models['liquidity'].get_training_stats()
            if liquidity_stats['loss_mean'] > thresholds['max_liquidity_loss']:
                self.logger.warning(
                    f"Liquidity model loss ({liquidity_stats['loss_mean']:.4f}) "
                    f"exceeds threshold ({thresholds['max_liquidity_loss']})"
                )
                
        except Exception as e:
            self.logger.error(f"Error monitoring performance: {e}")
            
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for all models.
        
        Returns:
            Dictionary of performance statistics
        """
        return {
            'gas': {
                'model_stats': self.models['gas'].get_training_stats(),
                'predictions': {
                    'count': len(self.predictions['gas']['history']),
                    'last': self.predictions['gas']['last_prediction']
                }
            },
            'liquidity': {
                'model_stats': self.models['liquidity'].get_training_stats(),
                'predictions': {
                    'count': len(self.predictions['liquidity']['history']),
                    'last': self.predictions['liquidity']['last_prediction']
                }
            }
        }