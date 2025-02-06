"""Specialized LSTM models for gas and liquidity prediction."""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .online_lstm import OnlineLSTM

class GasPricePredictor(OnlineLSTM):
    """LSTM model for gas price prediction."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize gas price predictor.
        
        Args:
            config: Configuration dictionary containing model parameters
                   and gas-specific settings
        """
        # Ensure output size is 2 (price and uncertainty)
        config['output_size'] = 2
        
        super().__init__(config)
        
        # Gas-specific loss weights
        self.price_weight = config.get('price_weight', 1.0)
        self.volatility_weight = config.get('volatility_weight', 0.5)
        
        # Track prediction performance
        self.performance = {
            'mae': [],
            'rmse': [],
            'volatility_error': [],
            'last_evaluation': None
        }
        
    def update(self, features: np.ndarray, target: np.ndarray):
        """
        Update model with new gas price data.
        
        Args:
            features: Input features including gas metrics
            target: Actual gas price and volatility
        """
        try:
            # Add custom gas price features
            features = self._augment_gas_features(features)
            
            # Update base model
            super().update(features, target)
            
            # Evaluate performance
            if len(self.train_stats['predictions']) >= 100:
                self._evaluate_performance()
                
        except Exception as e:
            self.logger.error(f"Error updating gas price model: {e}")
            
    def predict(
        self,
        features: np.ndarray
    ) -> Tuple[float, float, Dict[str, float]]:
        """
        Predict gas price with uncertainty.
        
        Args:
            features: Input features including gas metrics
            
        Returns:
            Tuple of (predicted_price, uncertainty, metadata)
        """
        try:
            # Add custom gas price features
            features = self._augment_gas_features(features)
            
            # Get base prediction
            prediction, uncertainty = super().predict(features)
            
            # Add prediction metadata
            metadata = {
                'confidence': 1.0 / uncertainty[0],
                'volatility': uncertainty[1],
                'mae': np.mean(self.performance['mae'][-100:]),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return prediction[0], uncertainty[0], metadata
            
        except Exception as e:
            self.logger.error(f"Error predicting gas price: {e}")
            return 0.0, float('inf'), {}
            
    def _augment_gas_features(self, features: np.ndarray) -> np.ndarray:
        """
        Add gas-specific features.
        
        Args:
            features: Base features
            
        Returns:
            Augmented feature array
        """
        try:
            # Calculate gas price momentum
            if features.shape[0] > 1:
                momentum = features[-1, 0] - features[0, 0]
                features = np.concatenate([
                    features,
                    np.full((features.shape[0], 1), momentum)
                ], axis=1)
                
            return features
            
        except Exception as e:
            self.logger.error(f"Error augmenting gas features: {e}")
            return features
            
    def _evaluate_performance(self):
        """Evaluate prediction performance."""
        try:
            predictions = np.array(self.train_stats['predictions'][-100:])
            targets = np.array([m[1] for m in list(self.memory)[-100:]])
            
            # Calculate metrics
            mae = np.mean(np.abs(predictions[:, 0] - targets[:, 0]))
            rmse = np.sqrt(np.mean((predictions[:, 0] - targets[:, 0])**2))
            vol_error = np.mean(np.abs(predictions[:, 1] - targets[:, 1]))
            
            # Update performance tracking
            self.performance['mae'].append(mae)
            self.performance['rmse'].append(rmse)
            self.performance['volatility_error'].append(vol_error)
            self.performance['last_evaluation'] = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error evaluating performance: {e}")

class LiquidityPredictor(OnlineLSTM):
    """LSTM model for liquidity prediction."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize liquidity predictor.
        
        Args:
            config: Configuration dictionary containing model parameters
                   and liquidity-specific settings
        """
        # Ensure output size is 4 (liquidity, volume, impact, uncertainty)
        config['output_size'] = 4
        
        super().__init__(config)
        
        # Liquidity-specific loss weights
        self.liquidity_weight = config.get('liquidity_weight', 1.0)
        self.volume_weight = config.get('volume_weight', 0.8)
        self.impact_weight = config.get('impact_weight', 0.6)
        
        # Track prediction performance
        self.performance = {
            'liquidity_mae': [],
            'volume_mae': [],
            'impact_mae': [],
            'last_evaluation': None
        }
        
    def update(self, features: np.ndarray, target: np.ndarray):
        """
        Update model with new liquidity data.
        
        Args:
            features: Input features including liquidity metrics
            target: Actual liquidity metrics
        """
        try:
            # Add custom liquidity features
            features = self._augment_liquidity_features(features)
            
            # Update base model
            super().update(features, target)
            
            # Evaluate performance
            if len(self.train_stats['predictions']) >= 100:
                self._evaluate_performance()
                
        except Exception as e:
            self.logger.error(f"Error updating liquidity model: {e}")
            
    def predict(
        self,
        features: np.ndarray
    ) -> Tuple[np.ndarray, float, Dict[str, float]]:
        """
        Predict liquidity metrics with uncertainty.
        
        Args:
            features: Input features including liquidity metrics
            
        Returns:
            Tuple of (predictions, uncertainty, metadata)
        """
        try:
            # Add custom liquidity features
            features = self._augment_liquidity_features(features)
            
            # Get base prediction
            predictions, uncertainties = super().predict(features)
            
            # Add prediction metadata
            metadata = {
                'confidence': 1.0 / np.mean(uncertainties),
                'liquidity_mae': np.mean(self.performance['liquidity_mae'][-100:]),
                'volume_mae': np.mean(self.performance['volume_mae'][-100:]),
                'impact_mae': np.mean(self.performance['impact_mae'][-100:]),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return predictions[:3], uncertainties[3], metadata
            
        except Exception as e:
            self.logger.error(f"Error predicting liquidity: {e}")
            return np.zeros(3), float('inf'), {}
            
    def _augment_liquidity_features(self, features: np.ndarray) -> np.ndarray:
        """
        Add liquidity-specific features.
        
        Args:
            features: Base features
            
        Returns:
            Augmented feature array
        """
        try:
            if features.shape[0] > 1:
                # Calculate volume momentum
                volume_momentum = features[-1, 1] - features[0, 1]
                
                # Calculate liquidity concentration
                liquidity_std = np.std(features[:, 0])
                
                # Add new features
                new_features = np.column_stack([
                    np.full(features.shape[0], volume_momentum),
                    np.full(features.shape[0], liquidity_std)
                ])
                
                features = np.concatenate([features, new_features], axis=1)
                
            return features
            
        except Exception as e:
            self.logger.error(f"Error augmenting liquidity features: {e}")
            return features
            
    def _evaluate_performance(self):
        """Evaluate prediction performance."""
        try:
            predictions = np.array(self.train_stats['predictions'][-100:])
            targets = np.array([m[1] for m in list(self.memory)[-100:]])
            
            # Calculate metrics for each component
            liquidity_mae = np.mean(np.abs(predictions[:, 0] - targets[:, 0]))
            volume_mae = np.mean(np.abs(predictions[:, 1] - targets[:, 1]))
            impact_mae = np.mean(np.abs(predictions[:, 2] - targets[:, 2]))
            
            # Update performance tracking
            self.performance['liquidity_mae'].append(liquidity_mae)
            self.performance['volume_mae'].append(volume_mae)
            self.performance['impact_mae'].append(impact_mae)
            self.performance['last_evaluation'] = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error evaluating performance: {e}")