"""Main feature pipeline coordinator."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np

from ...data_collection.coordinator import DataCollectionCoordinator
from .real_time import RealTimeFeatures
from .batch import BatchFeatures

class FeaturePipeline:
    """Coordinate real-time and batch feature processing."""
    
    def __init__(self, coordinator: DataCollectionCoordinator, config: Dict[str, Any]):
        """
        Initialize feature pipeline.
        
        Args:
            coordinator: Data collection coordinator
            config: Configuration dictionary containing:
                - real_time: Real-time feature config
                - batch: Batch feature config
                - feature_sets: Feature set definitions
        """
        self.coordinator = coordinator
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize processors
        self.real_time = RealTimeFeatures(coordinator, config.get('real_time', {}))
        self.batch = BatchFeatures(coordinator, config.get('batch', {}))
        
        # Configure feature sets
        self.feature_sets = config.get('feature_sets', {
            'minimal': ['gas', 'liquidity'],
            'standard': ['gas', 'liquidity', 'market', 'technical'],
            'full': ['gas', 'liquidity', 'market', 'technical', 'patterns', 'correlations']
        })
        
        # Track feature statistics
        self.stats = {
            'last_update': {},
            'feature_counts': {},
            'computation_times': [],
            'error_counts': {}
        }
        
    async def start(self):
        """Start feature pipeline."""
        try:
            # Start processors
            await self.real_time.start()
            await self.batch.start()
            self.logger.info("Feature pipeline started")
            
        except Exception as e:
            self.logger.error(f"Error starting feature pipeline: {e}")
            raise
            
    async def stop(self):
        """Stop feature pipeline."""
        try:
            # Stop processors
            await self.real_time.stop()
            await self.batch.stop()
            self.logger.info("Feature pipeline stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping feature pipeline: {e}")
            raise
            
    async def get_features(
        self,
        feature_set: str = 'standard'
    ) -> Dict[str, Any]:
        """
        Get current features.
        
        Args:
            feature_set: Which feature set to return ('minimal', 'standard', 'full')
            
        Returns:
            Dictionary of current features
        """
        try:
            start_time = datetime.utcnow()
            
            # Get required feature groups
            required_groups = self.feature_sets.get(feature_set, [])
            
            # Get real-time features
            rt_features = await self.real_time.get_features()
            
            # Get batch features
            batch_features = await self.batch.get_features()
            
            # Combine features
            features = {}
            for group in required_groups:
                if group in rt_features:
                    features[group] = rt_features[group]
                elif group in batch_features:
                    features[group] = batch_features[group]
                    
            # Update statistics
            computation_time = (datetime.utcnow() - start_time).total_seconds()
            self.stats['computation_times'].append(computation_time)
            self.stats['feature_counts'][feature_set] = len(features)
            self.stats['last_update'][feature_set] = datetime.utcnow()
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error getting features: {e}")
            self.stats['error_counts'][feature_set] = self.stats['error_counts'].get(feature_set, 0) + 1
            return {}
            
    async def get_feature_vector(
        self,
        feature_set: str = 'standard'
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Get features as a numpy array with feature names.
        
        Args:
            feature_set: Which feature set to return
            
        Returns:
            Tuple of (feature_vector, feature_names)
        """
        try:
            # Get features
            features = await self.get_features(feature_set)
            
            # Flatten nested dictionaries
            flat_features = {}
            feature_names = []
            
            def flatten_dict(d: Dict, prefix: str = ''):
                for k, v in d.items():
                    key = f"{prefix}{k}" if prefix else k
                    if isinstance(v, dict):
                        flatten_dict(v, f"{key}_")
                    elif isinstance(v, (int, float)):
                        flat_features[key] = float(v)
                        feature_names.append(key)
                        
            flatten_dict(features)
            
            # Create feature vector
            feature_vector = np.array([flat_features[name] for name in feature_names])
            
            return feature_vector, feature_names
            
        except Exception as e:
            self.logger.error(f"Error creating feature vector: {e}")
            return np.array([]), []
            
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get pipeline performance statistics.
        
        Returns:
            Dictionary of performance metrics
        """
        stats = {
            'real_time': self.real_time.get_performance_stats(),
            'feature_counts': self.stats['feature_counts'],
            'error_counts': self.stats['error_counts'],
            'computation_time': {
                'mean': np.mean(self.stats['computation_times']),
                'std': np.std(self.stats['computation_times']),
                'max': max(self.stats['computation_times'])
            },
            'last_update': {
                set_name: update_time.isoformat()
                for set_name, update_time in self.stats['last_update'].items()
            }
        }
        
        return stats
        
    async def validate_features(
        self,
        features: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate feature values.
        
        Args:
            features: Features to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check for required features
            for group in self.feature_sets['minimal']:
                if group not in features:
                    return False, f"Missing required feature group: {group}"
                    
            # Validate numeric values
            def validate_values(d: Dict) -> Tuple[bool, Optional[str]]:
                for k, v in d.items():
                    if isinstance(v, dict):
                        is_valid, error = validate_values(v)
                        if not is_valid:
                            return False, error
                    elif isinstance(v, (int, float)):
                        if not np.isfinite(v):
                            return False, f"Invalid value for {k}: {v}"
                return True, None
                
            return validate_values(features)
            
        except Exception as e:
            self.logger.error(f"Error validating features: {e}")
            return False, str(e)