"""Base classes for data collection system."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

class DataCollector(ABC):
    """Abstract base class for all data collectors."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data collector.
        
        Args:
            config: Configuration dictionary containing:
                - interval_seconds: Collection interval
                - metrics: Dictionary of metrics to collect
                - validation: Validation rules
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.subscribers: List['DataProcessor'] = []
        self._running = False
        self.metrics: Dict[str, callable] = {}
        self.last_collection: Dict[str, datetime] = {}
        self.storage: Optional['DataStorage'] = None
        
    @abstractmethod
    async def collect(self) -> Dict[str, Any]:
        """
        Collect data from source.
        
        Returns:
            Dictionary containing collected metrics
        """
        pass
        
    @abstractmethod
    async def validate_data(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate collected data.
        
        Args:
            data: Data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
        
    async def start(self):
        """Start data collection loop."""
        self._running = True
        self.logger.info(f"Starting {self.__class__.__name__}")
        
        while self._running:
            try:
                # Collect data
                data = await self.collect()
                
                # Add metadata
                data['timestamp'] = datetime.utcnow().isoformat()
                data['collector'] = self.__class__.__name__
                
                # Validate data
                is_valid, error = await self.validate_data(data)
                if not is_valid:
                    self.logger.error(f"Data validation failed: {error}")
                    continue
                    
                # Store data if storage is configured
                if self.storage:
                    try:
                        await self.storage.store(data)
                    except Exception as e:
                        self.logger.error(f"Failed to store data: {e}")
                        
                # Notify subscribers
                await self.notify_subscribers(data)
                
                # Update last collection time
                self.last_collection = {
                    metric: datetime.utcnow()
                    for metric in data.keys()
                }
                
            except Exception as e:
                self.logger.error(f"Collection error: {e}")
                
            # Wait for next collection interval
            await asyncio.sleep(self.config.get('interval_seconds', 1))
            
    async def stop(self):
        """Stop data collection."""
        self._running = False
        self.logger.info(f"Stopping {self.__class__.__name__}")
        
    async def add_subscriber(self, subscriber: 'DataProcessor'):
        """
        Add a subscriber to receive collected data.
        
        Args:
            subscriber: DataProcessor instance to receive data
        """
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)
            self.logger.info(f"Added subscriber: {subscriber.__class__.__name__}")
            
    async def remove_subscriber(self, subscriber: 'DataProcessor'):
        """
        Remove a subscriber.
        
        Args:
            subscriber: DataProcessor instance to remove
        """
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
            self.logger.info(f"Removed subscriber: {subscriber.__class__.__name__}")
            
    async def notify_subscribers(self, data: Dict[str, Any]):
        """
        Notify all subscribers of new data.
        
        Args:
            data: Data to send to subscribers
        """
        for subscriber in self.subscribers:
            try:
                await subscriber.process(data)
            except Exception as e:
                self.logger.error(f"Error notifying subscriber {subscriber.__class__.__name__}: {e}")
                
    def set_storage(self, storage: 'DataStorage'):
        """
        Set storage backend.
        
        Args:
            storage: DataStorage instance to use
        """
        self.storage = storage
        self.logger.info(f"Set storage: {storage.__class__.__name__}")

class DataProcessor(ABC):
    """Abstract base class for data processors."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data processor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming data.
        
        Args:
            data: Data to process
            
        Returns:
            Processed data
        """
        pass

class DataStorage(ABC):
    """Abstract base class for data storage."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data storage.
        
        Args:
            config: Configuration dictionary containing:
                - retention_days: How long to keep data
                - backup_enabled: Whether to backup data
                - compression_enabled: Whether to compress data
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    async def store(self, data: Dict[str, Any]):
        """
        Store data.
        
        Args:
            data: Data to store
        """
        pass
        
    @abstractmethod
    async def retrieve(
        self,
        query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve data.
        
        Args:
            query: Query parameters
            
        Returns:
            List of matching data records
        """
        pass
        
    @abstractmethod
    async def cleanup(self):
        """Clean up old data based on retention policy."""
        pass