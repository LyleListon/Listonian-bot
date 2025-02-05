# Modular Data Collection System Design

## Core Architecture

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import asyncio
import logging

class DataCollector(ABC):
    """Abstract base class for all data collectors"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.subscribers: List[DataProcessor] = []
        self._running = False
        
    @abstractmethod
    async def collect(self) -> Dict[str, Any]:
        """Collect data from source"""
        pass
        
    @abstractmethod
    async def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate collected data"""
        pass
        
    async def start(self):
        """Start data collection"""
        self._running = True
        while self._running:
            try:
                data = await self.collect()
                if await self.validate_data(data):
                    await self.notify_subscribers(data)
            except Exception as e:
                self.logger.error(f"Collection error: {e}")
                
    async def notify_subscribers(self, data: Dict[str, Any]):
        """Notify all subscribers of new data"""
        for subscriber in self.subscribers:
            await subscriber.process(data)
```

## 1. Network Data Collection

```python
class NetworkDataCollector(DataCollector):
    """Collect network-level data"""
    
    def __init__(self, web3_manager, config: Dict):
        super().__init__()
        self.web3 = web3_manager.web3
        self.collection_interval = config.get('interval', 1)  # seconds
        self.metrics = {
            'base_fee': self._collect_base_fee,
            'priority_fee': self._collect_priority_fee,
            'block_utilization': self._collect_block_utilization,
            'pending_txs': self._collect_pending_transactions,
            'network_load': self._collect_network_load
        }
        
    async def collect(self) -> Dict[str, Any]:
        """Collect all network metrics"""
        data = {}
        for metric_name, collector_func in self.metrics.items():
            try:
                data[metric_name] = await collector_func()
            except Exception as e:
                self.logger.error(f"Error collecting {metric_name}: {e}")
                data[metric_name] = None
        return data
        
    async def add_metric(self, name: str, collector_func):
        """Add new metric to collection"""
        self.metrics[name] = collector_func
        
    async def remove_metric(self, name: str):
        """Remove metric from collection"""
        self.metrics.pop(name, None)
```

## 2. Pool Data Collection

```python
class PoolDataCollector(DataCollector):
    """Collect pool-specific data"""
    
    def __init__(self, web3_manager, dex_manager, config: Dict):
        super().__init__()
        self.web3 = web3_manager.web3
        self.dex_manager = dex_manager
        self.tracked_pools = config.get('pools', [])
        self.metrics = {
            'reserves': self._collect_reserves,
            'volume': self._collect_volume,
            'price_impact': self._collect_price_impact,
            'concentration': self._collect_concentration,
            'utilization': self._collect_utilization
        }
        
    async def add_pool(self, pool_address: str, dex_name: str):
        """Add new pool to tracking"""
        if pool_address not in self.tracked_pools:
            self.tracked_pools.append({
                'address': pool_address,
                'dex': dex_name
            })
            
    async def remove_pool(self, pool_address: str):
        """Remove pool from tracking"""
        self.tracked_pools = [
            p for p in self.tracked_pools 
            if p['address'] != pool_address
        ]
```

## 3. Data Processing Pipeline

```python
class DataProcessor(ABC):
    """Abstract base class for data processors"""
    
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming data"""
        pass

class DataNormalizer(DataProcessor):
    """Normalize raw data for ML models"""
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data to standard ranges"""
        normalized = {}
        for key, value in data.items():
            if isinstance(value, (int, float)):
                normalized[key] = self._normalize_value(
                    value, 
                    self.ranges.get(key, {'min': 0, 'max': 1})
                )
        return normalized

class FeatureExtractor(DataProcessor):
    """Extract ML features from raw data"""
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant features"""
        return {
            'features': self._extract_features(data),
            'metadata': self._extract_metadata(data)
        }
```

## 4. Data Storage System

```python
class DataStorage(ABC):
    """Abstract base class for data storage"""
    
    @abstractmethod
    async def store(self, data: Dict[str, Any]):
        """Store data"""
        pass
        
    @abstractmethod
    async def retrieve(
        self, 
        query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Retrieve data"""
        pass

class TimeSeriesStorage(DataStorage):
    """Store time series data"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.table_configs = {
            'network_metrics': {
                'timestamp_column': 'timestamp',
                'indexes': ['metric_name', 'timestamp']
            },
            'pool_metrics': {
                'timestamp_column': 'timestamp',
                'indexes': ['pool_address', 'metric_name', 'timestamp']
            }
        }
```

## 5. Data Quality System

```python
class DataValidator:
    """Validate data quality"""
    
    def __init__(self):
        self.validators = {
            'network_data': self._validate_network_data,
            'pool_data': self._validate_pool_data
        }
        
    async def validate(
        self, 
        data_type: str, 
        data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate data by type"""
        if data_type not in self.validators:
            return False, f"Unknown data type: {data_type}"
            
        return await self.validators[data_type](data)
        
    def add_validator(
        self, 
        data_type: str, 
        validator_func
    ):
        """Add new validator"""
        self.validators[data_type] = validator_func
```

## 6. System Coordinator

```python
class DataCollectionSystem:
    """Coordinate all data collection components"""
    
    def __init__(self, config: Dict):
        self.collectors = {}
        self.processors = {}
        self.storage = None
        self.validator = DataValidator()
        
    async def initialize(self):
        """Initialize all components"""
        # Initialize collectors
        self.collectors['network'] = NetworkDataCollector(
            self.web3_manager,
            self.config.get('network', {})
        )
        self.collectors['pool'] = PoolDataCollector(
            self.web3_manager,
            self.dex_manager,
            self.config.get('pool', {})
        )
        
        # Initialize processors
        self.processors['normalizer'] = DataNormalizer()
        self.processors['feature_extractor'] = FeatureExtractor()
        
        # Initialize storage
        self.storage = TimeSeriesStorage(self.db_connection)
        
    async def start_collection(self):
        """Start all collectors"""
        for collector in self.collectors.values():
            asyncio.create_task(collector.start())
            
    async def add_collector(
        self, 
        name: str, 
        collector: DataCollector
    ):
        """Add new collector"""
        self.collectors[name] = collector
        await collector.start()
```

## Implementation Strategy

### Phase 1: Core Infrastructure
1. Implement base classes
2. Set up data validation
3. Create storage system
4. Add basic metrics

### Phase 2: Network Data
1. Implement NetworkDataCollector
2. Add gas metrics
3. Add block metrics
4. Add transaction metrics

### Phase 3: Pool Data
1. Implement PoolDataCollector
2. Add reserve tracking
3. Add volume metrics
4. Add concentration metrics

### Phase 4: Processing Pipeline
1. Implement normalizer
2. Add feature extraction
3. Create processing pipeline
4. Add data validation

Would you like to start implementing any particular component of this system?