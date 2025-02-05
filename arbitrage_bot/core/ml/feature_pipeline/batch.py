"""Batch feature processing for ML models."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass
import pandas as pd
from scipy import stats

from ...data_collection.coordinator import DataCollectionCoordinator

@dataclass
class BatchConfig:
    """Configuration for batch feature processing."""
    update_interval: int = 300  # 5 minutes
    history_hours: int = 24
    min_samples: int = 100
    max_samples: int = 10000
    feature_expiry: int = 3600  # 1 hour

class BatchFeatures:
    """Process batch features for ML models."""
    
    def __init__(self, coordinator: DataCollectionCoordinator, config: Dict[str, Any]):
        """
        Initialize batch feature processor.
        
        Args:
            coordinator: Data collection coordinator
            config: Configuration dictionary containing:
                - batch_config: BatchConfig settings
                - feature_groups: Which feature groups to process
                - technical_indicators: Which indicators to calculate
        """
        self.coordinator = coordinator
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize batch config
        self.batch_config = BatchConfig(**config.get('batch_config', {}))
        
        # Initialize feature storage
        self.features: Dict[str, Any] = {}
        self.feature_timestamps: Dict[str, datetime] = {}
        
        # Configure feature processors
        self.feature_processors = {
            'technical': self._process_technical_indicators,
            'patterns': self._process_market_patterns,
            'correlations': self._process_correlations,
            'volatility': self._process_volatility_metrics
        }
        
        self._running = False
        self._update_task = None
        
    async def start(self):
        """Start batch feature processing."""
        self._running = True
        self._update_task = asyncio.create_task(self._update_features())
        self.logger.info("Started batch feature processing")
        
    async def stop(self):
        """Stop batch feature processing."""
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped batch feature processing")
        
    async def get_features(self) -> Dict[str, Any]:
        """
        Get current batch features.
        
        Returns:
            Dictionary of current features
        """
        # Check for expired features
        current_time = datetime.utcnow()
        valid_features = {}
        
        for group, features in self.features.items():
            timestamp = self.feature_timestamps.get(group)
            if timestamp:
                age = (current_time - timestamp).total_seconds()
                if age < self.batch_config.feature_expiry:
                    valid_features[group] = features
                    
        return valid_features
        
    async def _update_features(self):
        """Update batch features periodically."""
        while self._running:
            try:
                start_time = datetime.utcnow()
                
                # Process each feature group
                for group_name, process_func in self.feature_processors.items():
                    if self.config.get('feature_groups', {}).get(group_name, {}).get('enabled', True):
                        try:
                            features = await process_func()
                            self.features[group_name] = features
                            self.feature_timestamps[group_name] = datetime.utcnow()
                            
                        except Exception as e:
                            self.logger.error(f"Error processing {group_name} features: {e}")
                            
                # Log performance metrics
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                self.logger.info(f"Batch processing completed in {processing_time:.2f}s")
                
                # Wait for next update
                await asyncio.sleep(self.batch_config.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in batch update loop: {e}")
                await asyncio.sleep(self.batch_config.update_interval)
                
    async def _process_technical_indicators(self) -> Dict[str, Any]:
        """
        Calculate technical indicators.
        
        Returns:
            Dictionary of technical indicators
        """
        try:
            # Get historical data
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=self.batch_config.history_hours)
            
            pool_data = await self.coordinator.get_recent_data(
                collector='pool',
                minutes=self.batch_config.history_hours * 60
            )
            
            if not pool_data:
                return {}
                
            # Convert to DataFrame
            df = pd.DataFrame(pool_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Calculate indicators
            indicators = {}
            
            # Moving averages
            for window in [5, 15, 30, 60]:
                indicators[f'ma_{window}'] = df['price'].rolling(window).mean().iloc[-1]
                
            # RSI
            delta = df['price'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            indicators['rsi'] = 100 - (100 / (1 + rs.iloc[-1]))
            
            # Bollinger Bands
            ma20 = df['price'].rolling(window=20).mean()
            std20 = df['price'].rolling(window=20).std()
            indicators['bb_upper'] = ma20 + (std20 * 2)
            indicators['bb_lower'] = ma20 - (std20 * 2)
            indicators['bb_width'] = (indicators['bb_upper'] - indicators['bb_lower']) / ma20
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating technical indicators: {e}")
            return {}
            
    async def _process_market_patterns(self) -> Dict[str, Any]:
        """
        Detect market patterns.
        
        Returns:
            Dictionary of detected patterns
        """
        try:
            # Get historical data
            pool_data = await self.coordinator.get_recent_data(
                collector='pool',
                minutes=self.batch_config.history_hours * 60
            )
            
            if not pool_data:
                return {}
                
            # Convert to DataFrame
            df = pd.DataFrame(pool_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            patterns = {}
            
            # Detect trend
            price_changes = df['price'].pct_change()
            trend_strength = abs(price_changes.mean()) / price_changes.std()
            patterns['trend_strength'] = trend_strength
            
            # Detect mean reversion
            z_score = (df['price'] - df['price'].rolling(50).mean()) / df['price'].rolling(50).std()
            patterns['mean_reversion_signal'] = z_score.iloc[-1]
            
            # Detect momentum
            momentum = df['price'].diff(20) / df['price'].shift(20)
            patterns['momentum'] = momentum.iloc[-1]
            
            # Detect volatility regime
            vol = df['price'].pct_change().rolling(30).std()
            patterns['volatility_regime'] = 'high' if vol.iloc[-1] > vol.mean() else 'low'
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error detecting market patterns: {e}")
            return {}
            
    async def _process_correlations(self) -> Dict[str, Any]:
        """
        Calculate cross-metric correlations.
        
        Returns:
            Dictionary of correlation metrics
        """
        try:
            # Get historical data
            network_data = await self.coordinator.get_recent_data(
                collector='network',
                minutes=self.batch_config.history_hours * 60
            )
            
            pool_data = await self.coordinator.get_recent_data(
                collector='pool',
                minutes=self.batch_config.history_hours * 60
            )
            
            if not network_data or not pool_data:
                return {}
                
            # Create correlation matrix
            metrics = {
                'gas_price': [d.get('base_fee', 0) for d in network_data],
                'network_load': [d.get('network_load', 0) for d in network_data],
                'liquidity': [d.get('liquidity', 0) for d in pool_data],
                'volume': [d.get('volume', 0) for d in pool_data]
            }
            
            df = pd.DataFrame(metrics)
            corr_matrix = df.corr()
            
            # Extract relevant correlations
            correlations = {
                'gas_liquidity_corr': corr_matrix.loc['gas_price', 'liquidity'],
                'gas_volume_corr': corr_matrix.loc['gas_price', 'volume'],
                'load_volume_corr': corr_matrix.loc['network_load', 'volume']
            }
            
            return correlations
            
        except Exception as e:
            self.logger.error(f"Error calculating correlations: {e}")
            return {}
            
    async def _process_volatility_metrics(self) -> Dict[str, Any]:
        """
        Calculate advanced volatility metrics.
        
        Returns:
            Dictionary of volatility metrics
        """
        try:
            # Get historical data
            pool_data = await self.coordinator.get_recent_data(
                collector='pool',
                minutes=self.batch_config.history_hours * 60
            )
            
            if not pool_data:
                return {}
                
            # Convert to DataFrame
            df = pd.DataFrame(pool_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Calculate volatility metrics
            returns = df['price'].pct_change().dropna()
            
            metrics = {
                'volatility': returns.std(),
                'skewness': stats.skew(returns),
                'kurtosis': stats.kurtosis(returns),
                'var_95': np.percentile(returns, 5),  # Value at Risk
                'cvar_95': returns[returns <= np.percentile(returns, 5)].mean()  # Conditional VaR
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility metrics: {e}")
            return {}