"""Data collection system coordinator."""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import DataCollector, DataProcessor, DataStorage
from .collectors.network import NetworkDataCollector
from .collectors.pool import PoolDataCollector
from .processors.normalizer import DataNormalizer
from .processors.feature_extractor import FeatureExtractor
from .storage.timeseries import TimeSeriesStorage

class DataCollectionCoordinator:
    """Coordinate data collection, processing, and storage."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize coordinator.
        
        Args:
            config: Configuration dictionary containing:
                - collectors: Collector configurations
                - processors: Processor configurations
                - storage: Storage configuration
                - monitoring: Monitoring settings
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self.collectors: Dict[str, DataCollector] = {}
        self.processors: Dict[str, DataProcessor] = {}
        self.storage: Optional[DataStorage] = None
        
        # Track component status
        self.status = {
            'collectors': {},
            'processors': {},
            'storage': 'initialized',
            'last_collection': {},
            'last_processing': {},
            'errors': []
        }
        
        # Initialize monitoring
        self.monitoring_interval = config.get('monitoring', {}).get('interval_seconds', 60)
        self._monitoring_task = None
        
    async def initialize(
        self,
        web3_manager: Any,
        dex_manager: Any
    ) -> bool:
        """
        Initialize all components.
        
        Args:
            web3_manager: Web3Manager instance
            dex_manager: DEXManager instance
            
        Returns:
            bool: True if initialization successful
        """
        try:
            # Initialize collectors
            self.collectors['network'] = NetworkDataCollector(
                web3_manager,
                self.config.get('collectors', {}).get('network', {})
            )
            
            self.collectors['pool'] = PoolDataCollector(
                web3_manager,
                dex_manager,
                self.config.get('collectors', {}).get('pool', {})
            )
            
            # Initialize processors
            self.processors['normalizer'] = DataNormalizer(
                self.config.get('processors', {}).get('normalizer', {})
            )
            
            self.processors['feature_extractor'] = FeatureExtractor(
                self.config.get('processors', {}).get('feature_extractor', {})
            )
            
            # Initialize storage
            self.storage = TimeSeriesStorage(
                self.config.get('storage', {})
            )
            
            # Set up processing pipeline
            await self._setup_pipeline()
            
            self.logger.info("Data collection system initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing data collection system: {e}")
            return False
            
    async def start(self):
        """Start data collection and monitoring."""
        try:
            # Start collectors
            for name, collector in self.collectors.items():
                asyncio.create_task(collector.start())
                self.status['collectors'][name] = 'running'
                self.logger.info(f"Started collector: {name}")
                
            # Start monitoring
            self._monitoring_task = asyncio.create_task(self._monitor_system())
            self.logger.info("Data collection system started")
            
        except Exception as e:
            self.logger.error(f"Error starting data collection system: {e}")
            raise
            
    async def stop(self):
        """Stop data collection and monitoring."""
        try:
            # Stop collectors
            for name, collector in self.collectors.items():
                await collector.stop()
                self.status['collectors'][name] = 'stopped'
                self.logger.info(f"Stopped collector: {name}")
                
            # Stop monitoring
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
                
            self.logger.info("Data collection system stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping data collection system: {e}")
            raise
            
    async def _setup_pipeline(self):
        """Set up data processing pipeline."""
        try:
            # Connect normalizer to collectors
            for collector in self.collectors.values():
                await collector.add_subscriber(self.processors['normalizer'])
                
            # Connect feature extractor to normalizer
            await self.processors['normalizer'].add_subscriber(
                self.processors['feature_extractor']
            )
            
            # Set storage for all components
            if self.storage:
                for collector in self.collectors.values():
                    collector.set_storage(self.storage)
                    
            self.logger.info("Processing pipeline configured")
            
        except Exception as e:
            self.logger.error(f"Error setting up pipeline: {e}")
            raise
            
    async def _monitor_system(self):
        """Monitor system health and performance."""
        while True:
            try:
                # Check collector status
                for name, collector in self.collectors.items():
                    last_collection = collector.last_collection
                    if last_collection:
                        self.status['last_collection'][name] = max(
                            last_collection.values()
                        )
                        
                        # Check for stale collectors
                        staleness = (
                            datetime.utcnow() - 
                            self.status['last_collection'][name]
                        ).total_seconds()
                        
                        if staleness > self.monitoring_interval * 2:
                            self.logger.warning(
                                f"Collector {name} may be stale. "
                                f"Last collection: {staleness:.1f}s ago"
                            )
                            
                # Check storage
                if self.storage:
                    await self.storage.cleanup()
                    
                # Update status
                self.status['timestamp'] = datetime.utcnow().isoformat()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in system monitoring: {e}")
                self.status['errors'].append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': str(e)
                })
                await asyncio.sleep(self.monitoring_interval)
                
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current system status.
        
        Returns:
            Dictionary containing system status
        """
        return {
            'status': self.status,
            'collectors': {
                name: {
                    'status': self.status['collectors'].get(name, 'unknown'),
                    'last_collection': self.status['last_collection'].get(name)
                }
                for name in self.collectors
            },
            'processors': {
                name: {
                    'status': self.status['processors'].get(name, 'unknown'),
                    'last_processing': self.status['last_processing'].get(name)
                }
                for name in self.processors
            },
            'storage': {
                'status': self.status['storage'],
                'errors': len(self.status['errors'])
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
    async def get_recent_data(
        self,
        collector: Optional[str] = None,
        minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get recent data from storage.
        
        Args:
            collector: Optional collector filter
            minutes: Number of minutes of data to retrieve
            
        Returns:
            List of recent data points
        """
        if not self.storage:
            return []
            
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)
        
        query = {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
        
        if collector:
            query['collector'] = collector
            
        return await self.storage.retrieve(query)