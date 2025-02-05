# Data Collection Implementation Plan

## Directory Structure

```
arbitrage_bot/
└── core/
    └── data_collection/
        ├── __init__.py
        ├── base.py           # Base classes
        ├── collectors/       # Specific collectors
        │   ├── __init__.py
        │   ├── network.py    # Network data collector
        │   └── pool.py       # Pool data collector
        ├── processors/       # Data processors
        │   ├── __init__.py
        │   ├── normalizer.py
        │   └── feature_extractor.py
        ├── storage/          # Storage implementations
        │   ├── __init__.py
        │   ├── timeseries.py
        │   └── database.py
        └── validation/       # Data validation
            ├── __init__.py
            └── validators.py
```

## Core Implementation

### 1. Base Classes (base.py)

```python
"""Base classes for data collection system."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

class DataCollector(ABC):
    """Abstract base class for all data collectors."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.subscribers: List[DataProcessor] = []
        self._running = False
        self.metrics: Dict[str, callable] = {}
        self.last_collection: Dict[str, datetime] = {}
        
    @abstractmethod
    async def collect(self) -> Dict[str, Any]:
        """Collect data from source."""
        pass
        
    @abstractmethod
    async def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate collected data."""
        pass
        
    async def start(self):
        """Start data collection loop."""
        self._running = True
        while self._running:
            try:
                data = await self.collect()
                if await self.validate_data(data):
                    await self.notify_subscribers(data)
                    await self.store_data(data)
            except Exception as e:
                self.logger.error(f"Collection error: {e}")
            await asyncio.sleep(self.config.get('interval_seconds', 1))
            
    async def stop(self):
        """Stop data collection."""
        self._running = False
        
    async def add_subscriber(self, subscriber: 'DataProcessor'):
        """Add a subscriber to receive collected data."""
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)
            
    async def notify_subscribers(self, data: Dict[str, Any]):
        """Notify all subscribers of new data."""
        for subscriber in self.subscribers:
            try:
                await subscriber.process(data)
            except Exception as e:
                self.logger.error(f"Error notifying subscriber: {e}")

class DataProcessor(ABC):
    """Abstract base class for data processors."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming data."""
        pass

class DataStorage(ABC):
    """Abstract base class for data storage."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    async def store(self, data: Dict[str, Any]):
        """Store data."""
        pass
        
    @abstractmethod
    async def retrieve(
        self,
        query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Retrieve data."""
        pass
```

### 2. Network Data Collector (collectors/network.py)

```python
"""Network data collector implementation."""

from typing import Dict, Any
from web3 import Web3
from ...base import DataCollector

class NetworkDataCollector(DataCollector):
    """Collect network-level data."""
    
    def __init__(self, web3_manager, config: Dict[str, Any]):
        super().__init__(config)
        self.web3 = web3_manager.web3
        self.metrics = {
            'base_fee': self._collect_base_fee,
            'priority_fee': self._collect_priority_fee,
            'block_utilization': self._collect_block_utilization,
            'pending_txs': self._collect_pending_transactions,
            'network_load': self._collect_network_load
        }
        
    async def _collect_base_fee(self) -> int:
        """Collect current base fee."""
        block = await self.web3.eth.get_block('latest')
        return block.baseFeePerGas
        
    async def _collect_priority_fee(self) -> int:
        """Collect current priority fee."""
        return await self.web3.eth.max_priority_fee
        
    async def _collect_block_utilization(self) -> float:
        """Calculate block utilization."""
        block = await self.web3.eth.get_block('latest')
        return block.gasUsed / block.gasLimit
        
    async def _collect_pending_transactions(self) -> int:
        """Get pending transaction count."""
        return len(await self.web3.eth.get_pending_transactions())
        
    async def _collect_network_load(self) -> float:
        """Calculate network load."""
        # Implementation depends on specific metrics you want to use
        pass
```

### 3. Pool Data Collector (collectors/pool.py)

```python
"""Pool data collector implementation."""

from typing import Dict, Any
from web3 import Web3
from ...base import DataCollector

class PoolDataCollector(DataCollector):
    """Collect pool-specific data."""
    
    def __init__(self, web3_manager, dex_manager, config: Dict[str, Any]):
        super().__init__(config)
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
        
    async def _collect_reserves(self, pool: Dict) -> Dict[str, Any]:
        """Collect pool reserves."""
        contract = self.dex_manager.get_pool_contract(
            pool['address'],
            pool['dex']
        )
        reserves = await contract.functions.getReserves().call()
        return {
            'token0_reserve': reserves[0],
            'token1_reserve': reserves[1],
            'last_update': reserves[2]
        }
        
    async def _collect_volume(self, pool: Dict) -> Dict[str, Any]:
        """Collect trading volume."""
        # Implementation depends on DEX interface
        pass
```

### 4. Data Processor Implementation (processors/normalizer.py)

```python
"""Data normalization processor."""

from typing import Dict, Any
from ...base import DataProcessor

class DataNormalizer(DataProcessor):
    """Normalize raw data for ML models."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.ranges = config.get('ranges', {})
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data to standard ranges."""
        normalized = {}
        for key, value in data.items():
            if isinstance(value, (int, float)):
                normalized[key] = self._normalize_value(
                    value,
                    self.ranges.get(key, {'min': 0, 'max': 1})
                )
        return normalized
        
    def _normalize_value(
        self,
        value: float,
        range_config: Dict[str, float]
    ) -> float:
        """Normalize a single value."""
        min_val = range_config['min']
        max_val = range_config['max']
        return (value - min_val) / (max_val - min_val)
```

## Implementation Steps

### Phase 1: Core Setup (1-2 days)
1. Create directory structure
2. Implement base classes
3. Add basic configuration
4. Set up logging

### Phase 2: Network Collection (2-3 days)
1. Implement NetworkDataCollector
2. Add gas metrics collection
3. Add block metrics collection
4. Add basic validation

### Phase 3: Pool Collection (2-3 days)
1. Implement PoolDataCollector
2. Add reserves collection
3. Add volume collection
4. Add validation

### Phase 4: Processing (2-3 days)
1. Implement DataNormalizer
2. Add feature extraction
3. Set up processing pipeline
4. Add data validation

Would you like to proceed with implementing any of these components? We can switch to Code mode to start the actual implementation.