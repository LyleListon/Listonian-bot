"""Feature extraction processor for ML models."""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
from datetime import datetime, timedelta

from ..base import DataProcessor

class FeatureExtractor(DataProcessor):
    """Extract ML features from normalized data."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize feature extractor.
        
        Args:
            config: Configuration dictionary containing:
                - window_sizes: List of window sizes for features
                - feature_groups: Dictionary of feature group configurations
                - combine_method: How to combine features ('concat' or 'merge')
        """
        super().__init__(config)
        self.window_sizes = config.get('window_sizes', [10, 30, 60])  # in seconds
        self.feature_groups = config.get('feature_groups', {
            'gas': ['base_fee', 'priority_fee', 'block_utilization'],
            'network': ['pending_txs', 'network_load', 'block_time'],
            'liquidity': ['reserves', 'volume', 'price_impact'],
            'market': ['price', 'volatility', 'trend']
        })
        self.combine_method = config.get('combine_method', 'concat')
        
        # Initialize feature history
        self.history: Dict[str, List[Dict]] = {
            'network': [],
            'pool': []
        }
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process normalized data into ML features.
        
        Args:
            data: Normalized data to process
            
        Returns:
            Dictionary containing extracted features
        """
        try:
            # Update history
            collector = data.get('collector')
            if collector:
                self.history[collector].append({
                    'timestamp': datetime.fromisoformat(data['timestamp']),
                    'data': data['normalized_data']
                })
                
                # Trim history to largest window size
                max_window = max(self.window_sizes)
                cutoff = datetime.utcnow() - timedelta(seconds=max_window)
                self.history[collector] = [
                    entry for entry in self.history[collector]
                    if entry['timestamp'] > cutoff
                ]
            
            # Extract features
            features = {
                'timestamp': data['timestamp'],
                'features': {}
            }
            
            # Extract time-based features
            features['features'].update(
                await self._extract_time_features(data['timestamp'])
            )
            
            # Extract features for each group
            for group_name, metrics in self.feature_groups.items():
                features['features'].update(
                    await self._extract_group_features(group_name, metrics)
                )
                
            return features
            
        except Exception as e:
            self.logger.error(f"Error extracting features: {e}")
            return data
            
    async def _extract_time_features(self, timestamp: str) -> Dict[str, float]:
        """
        Extract time-based features.
        
        Args:
            timestamp: ISO format timestamp
            
        Returns:
            Dictionary of time-based features
        """
        try:
            dt = datetime.fromisoformat(timestamp)
            
            # Cyclical encoding of time features
            hour_sin = np.sin(2 * np.pi * dt.hour / 24)
            hour_cos = np.cos(2 * np.pi * dt.hour / 24)
            
            day_of_week_sin = np.sin(2 * np.pi * dt.weekday() / 7)
            day_of_week_cos = np.cos(2 * np.pi * dt.weekday() / 7)
            
            return {
                'hour_sin': float(hour_sin),
                'hour_cos': float(hour_cos),
                'day_of_week_sin': float(day_of_week_sin),
                'day_of_week_cos': float(day_of_week_cos)
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting time features: {e}")
            return {}
            
    async def _extract_group_features(
        self,
        group_name: str,
        metrics: List[str]
    ) -> Dict[str, Any]:
        """
        Extract features for a metric group.
        
        Args:
            group_name: Name of feature group
            metrics: List of metrics in group
            
        Returns:
            Dictionary of features for the group
        """
        features = {}
        
        try:
            # Get relevant history
            collector = 'network' if group_name in ['gas', 'network'] else 'pool'
            history = self.history[collector]
            
            if not history:
                return features
                
            # Extract features for each window size
            for window_size in self.window_sizes:
                window_features = await self._extract_window_features(
                    history,
                    metrics,
                    window_size
                )
                
                # Add window size to feature names
                features.update({
                    f"{group_name}_{k}_{window_size}s": v
                    for k, v in window_features.items()
                })
                
        except Exception as e:
            self.logger.error(f"Error extracting {group_name} features: {e}")
            
        return features
        
    async def _extract_window_features(
        self,
        history: List[Dict],
        metrics: List[str],
        window_size: int
    ) -> Dict[str, float]:
        """
        Extract features from a time window.
        
        Args:
            history: List of historical data points
            metrics: List of metrics to extract
            window_size: Window size in seconds
            
        Returns:
            Dictionary of features
        """
        features = {}
        
        try:
            # Get data points in window
            cutoff = datetime.utcnow() - timedelta(seconds=window_size)
            window_data = [
                entry['data'] for entry in history
                if entry['timestamp'] > cutoff
            ]
            
            if not window_data:
                return features
                
            # Extract features for each metric
            for metric in metrics:
                values = []
                for data_point in window_data:
                    if isinstance(data_point.get(metric), (int, float)):
                        values.append(float(data_point[metric]))
                        
                if values:
                    features.update({
                        f"{metric}_mean": float(np.mean(values)),
                        f"{metric}_std": float(np.std(values)) if len(values) > 1 else 0.0,
                        f"{metric}_min": float(np.min(values)),
                        f"{metric}_max": float(np.max(values)),
                        f"{metric}_last": float(values[-1])
                    })
                    
                    # Add trend features
                    if len(values) >= 2:
                        # Linear regression for trend
                        x = np.arange(len(values))
                        slope, _ = np.polyfit(x, values, 1)
                        features[f"{metric}_trend"] = float(slope)
                        
                        # Momentum indicators
                        features[f"{metric}_momentum"] = float(values[-1] - values[0])
                        features[f"{metric}_acceleration"] = float(
                            (values[-1] - values[-2]) if len(values) > 2
                            else 0.0
                        )
                        
        except Exception as e:
            self.logger.error(f"Error extracting window features: {e}")
            
        return features
        
    async def _combine_features(
        self,
        network_features: Dict[str, float],
        pool_features: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Combine features from different sources.
        
        Args:
            network_features: Features from network data
            pool_features: Features from pool data
            
        Returns:
            Combined feature dictionary
        """
        if self.combine_method == 'concat':
            # Simple concatenation
            return {
                **network_features,
                **pool_features
            }
        else:
            # Merge with interactions
            combined = {
                **network_features,
                **pool_features
            }
            
            # Add interaction features
            for nf_name, nf_value in network_features.items():
                for pf_name, pf_value in pool_features.items():
                    if isinstance(nf_value, (int, float)) and isinstance(pf_value, (int, float)):
                        combined[f"{nf_name}_x_{pf_name}"] = float(nf_value * pf_value)
                        
            return combined