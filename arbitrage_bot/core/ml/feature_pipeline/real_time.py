"""Real-time feature processing for ML models."""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np

from ...data_collection.coordinator import DataCollectionCoordinator

class RealTimeFeatures:
    """Process real-time features for immediate use in ML models."""
    
    def __init__(self, coordinator: DataCollectionCoordinator, config: Dict[str, Any]):
        """
        Initialize real-time feature processor.
        
        Args:
            coordinator: Data collection coordinator
            config: Configuration dictionary containing:
                - update_interval: How often to update features (seconds)
                - feature_groups: Which feature groups to process
                - window_sizes: List of window sizes for features
        """
        self.coordinator = coordinator
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize feature cache
        self.features: Dict[str, Any] = {}
        self.last_update: Dict[str, datetime] = {}
        
        # Configure feature groups
        self.feature_groups = {
            'gas': self._process_gas_features,
            'liquidity': self._process_liquidity_features,
            'market': self._process_market_features
        }
        
        # Track feature statistics
        self.feature_stats = {
            'computation_time': [],
            'feature_counts': {},
            'update_frequency': {}
        }
        
        self._running = False
        self._update_task = None
        
    async def start(self):
        """Start real-time feature processing."""
        self._running = True
        self._update_task = asyncio.create_task(self._update_features())
        self.logger.info("Started real-time feature processing")
        
    async def stop(self):
        """Stop real-time feature processing."""
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped real-time feature processing")
        
    async def get_features(self) -> Dict[str, Any]:
        """
        Get current feature values.
        
        Returns:
            Dictionary of current features
        """
        return self.features.copy()
        
    async def _update_features(self):
        """Update features continuously."""
        while self._running:
            try:
                start_time = datetime.utcnow()
                
                # Process each feature group
                for group_name, process_func in self.feature_groups.items():
                    if self.config.get('feature_groups', {}).get(group_name, {}).get('enabled', True):
                        try:
                            features = await process_func()
                            self.features[group_name] = features
                            self.last_update[group_name] = datetime.utcnow()
                            
                            # Update statistics
                            self.feature_stats['feature_counts'][group_name] = len(features)
                            
                        except Exception as e:
                            self.logger.error(f"Error processing {group_name} features: {e}")
                            
                # Update performance metrics
                computation_time = (datetime.utcnow() - start_time).total_seconds()
                self.feature_stats['computation_time'].append(computation_time)
                
                # Keep only recent computation times
                if len(self.feature_stats['computation_time']) > 1000:
                    self.feature_stats['computation_time'] = self.feature_stats['computation_time'][-1000:]
                    
                # Wait for next update
                await asyncio.sleep(self.config.get('update_interval', 1))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in feature update loop: {e}")
                await asyncio.sleep(1)
                
    async def _process_gas_features(self) -> Dict[str, float]:
        """
        Process gas-related features.
        
        Returns:
            Dictionary of gas features
        """
        try:
            # Get recent network data
            data = await self.coordinator.get_recent_data(
                collector='network',
                minutes=5
            )
            
            if not data:
                return {}
                
            # Extract gas prices
            gas_prices = [d.get('base_fee', 0) for d in data]
            priority_fees = [d.get('priority_fee', 0) for d in data]
            
            # Calculate features
            features = {
                'gas_price_current': gas_prices[-1],
                'gas_price_mean': np.mean(gas_prices),
                'gas_price_std': np.std(gas_prices),
                'gas_price_trend': np.polyfit(range(len(gas_prices)), gas_prices, 1)[0],
                'priority_fee_current': priority_fees[-1],
                'priority_fee_mean': np.mean(priority_fees),
                'gas_volatility': np.std(np.diff(gas_prices)) / np.mean(gas_prices)
            }
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error processing gas features: {e}")
            return {}
            
    async def _process_liquidity_features(self) -> Dict[str, float]:
        """
        Process liquidity-related features.
        
        Returns:
            Dictionary of liquidity features
        """
        try:
            # Get recent pool data
            data = await self.coordinator.get_recent_data(
                collector='pool',
                minutes=5
            )
            
            if not data:
                return {}
                
            # Process each pool
            pool_features = {}
            for pool_data in data:
                pool_address = pool_data.get('pool_address')
                if pool_address:
                    metrics = pool_data.get('metrics', {})
                    pool_features[pool_address] = {
                        'liquidity': metrics.get('liquidity', 0),
                        'volume': metrics.get('volume_1h', 0),
                        'utilization': metrics.get('utilization', 0),
                        'price_impact': metrics.get('price_impact', 0)
                    }
                    
            # Aggregate features across pools
            features = {
                'total_liquidity': sum(p['liquidity'] for p in pool_features.values()),
                'total_volume': sum(p['volume'] for p in pool_features.values()),
                'avg_utilization': np.mean([p['utilization'] for p in pool_features.values()]),
                'max_price_impact': max(p['price_impact'] for p in pool_features.values())
            }
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error processing liquidity features: {e}")
            return {}
            
    async def _process_market_features(self) -> Dict[str, float]:
        """
        Process market-related features.
        
        Returns:
            Dictionary of market features
        """
        try:
            # Get recent market data
            network_data = await self.coordinator.get_recent_data(
                collector='network',
                minutes=5
            )
            
            pool_data = await self.coordinator.get_recent_data(
                collector='pool',
                minutes=5
            )
            
            if not network_data or not pool_data:
                return {}
                
            # Calculate network features
            network_load = [d.get('network_load', 0) for d in network_data]
            pending_txs = [d.get('pending_txs', 0) for d in network_data]
            
            # Calculate market features
            features = {
                'network_load_current': network_load[-1],
                'network_load_trend': np.polyfit(range(len(network_load)), network_load, 1)[0],
                'pending_txs_current': pending_txs[-1],
                'pending_txs_trend': np.polyfit(range(len(pending_txs)), pending_txs, 1)[0],
                'market_activity': np.mean(network_load) * np.mean(pending_txs)
            }
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error processing market features: {e}")
            return {}
            
    async def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary of performance metrics
        """
        return {
            'avg_computation_time': np.mean(self.feature_stats['computation_time']),
            'max_computation_time': max(self.feature_stats['computation_time']),
            'feature_counts': self.feature_stats['feature_counts'],
            'last_update': {
                group: update_time.isoformat()
                for group, update_time in self.last_update.items()
            }
        }