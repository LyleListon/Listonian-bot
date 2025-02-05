"""Data normalization processor."""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
from datetime import datetime

from ..base import DataProcessor

class DataNormalizer(DataProcessor):
    """Normalize raw data for ML models."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data normalizer.
        
        Args:
            config: Configuration dictionary containing:
                - ranges: Dictionary of expected value ranges per metric
                - window_size: Size of window for rolling statistics
                - scaling_method: 'standard' or 'minmax'
        """
        super().__init__(config)
        self.ranges = config.get('ranges', {})
        self.window_size = config.get('window_size', 100)
        self.scaling_method = config.get('scaling_method', 'standard')
        
        # Track historical values for rolling statistics
        self.history: Dict[str, List[float]] = {}
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and normalize incoming data.
        
        Args:
            data: Raw data to normalize
            
        Returns:
            Dictionary containing normalized data
        """
        try:
            normalized = {
                'timestamp': data.get('timestamp', datetime.utcnow().isoformat()),
                'collector': data.get('collector'),
                'normalized_data': {}
            }
            
            if 'metrics' in data:
                # Handle pool data structure
                normalized['normalized_data'] = await self._normalize_metrics(
                    data['metrics']
                )
            else:
                # Handle flat data structure
                normalized['normalized_data'] = await self._normalize_metrics(data)
                
            return normalized
            
        except Exception as e:
            self.logger.error(f"Error normalizing data: {e}")
            return data
            
    async def _normalize_metrics(
        self,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Normalize a set of metrics.
        
        Args:
            metrics: Dictionary of metrics to normalize
            
        Returns:
            Dictionary of normalized metrics
        """
        normalized = {}
        
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                try:
                    # Update historical values
                    if metric_name not in self.history:
                        self.history[metric_name] = []
                    self.history[metric_name].append(float(value))
                    
                    # Keep history within window size
                    if len(self.history[metric_name]) > self.window_size:
                        self.history[metric_name].pop(0)
                        
                    # Normalize value
                    normalized[metric_name] = await self._normalize_value(
                        metric_name,
                        value
                    )
                    
                    # Add statistical features
                    normalized[f"{metric_name}_stats"] = await self._calculate_statistics(
                        metric_name
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error normalizing {metric_name}: {e}")
                    normalized[metric_name] = value
                    
            elif isinstance(value, dict):
                # Recursively normalize nested dictionaries
                normalized[metric_name] = await self._normalize_metrics(value)
            else:
                # Keep non-numeric values as is
                normalized[metric_name] = value
                
        return normalized
        
    async def _normalize_value(
        self,
        metric_name: str,
        value: float
    ) -> float:
        """
        Normalize a single value.
        
        Args:
            metric_name: Name of metric being normalized
            value: Value to normalize
            
        Returns:
            Normalized value
        """
        try:
            if self.scaling_method == 'standard' and len(self.history[metric_name]) > 1:
                # Use standard scaling (z-score)
                mean = np.mean(self.history[metric_name])
                std = np.std(self.history[metric_name])
                if std > 0:
                    return (value - mean) / std
                return 0.0
            else:
                # Use min-max scaling
                range_config = self.ranges.get(metric_name, {})
                min_val = range_config.get('min', min(self.history[metric_name]))
                max_val = range_config.get('max', max(self.history[metric_name]))
                
                if max_val > min_val:
                    return (value - min_val) / (max_val - min_val)
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error in _normalize_value for {metric_name}: {e}")
            return value
            
    async def _calculate_statistics(
        self,
        metric_name: str
    ) -> Dict[str, float]:
        """
        Calculate statistical features for a metric.
        
        Args:
            metric_name: Name of metric
            
        Returns:
            Dictionary containing statistical features
        """
        try:
            values = self.history[metric_name]
            if len(values) < 2:
                return {}
                
            stats = {
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'median': float(np.median(values))
            }
            
            # Calculate trend
            if len(values) >= 2:
                recent_values = values[-10:]  # Use last 10 values for trend
                slope, _ = np.polyfit(range(len(recent_values)), recent_values, 1)
                stats['trend'] = float(slope)
            else:
                stats['trend'] = 0.0
                
            # Calculate volatility
            if len(values) >= 2:
                pct_changes = np.diff(values) / values[:-1]
                stats['volatility'] = float(np.std(pct_changes))
            else:
                stats['volatility'] = 0.0
                
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculating statistics for {metric_name}: {e}")
            return {}