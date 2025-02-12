"""Factory for creating pre-configured storage managers."""

from typing import Optional, Union
from pathlib import Path
from ..memory import MemoryBank, MemoryBankManager
from . import StorageManager
from .schemas import (
    TRADE_SCHEMA,
    OPPORTUNITY_SCHEMA,
    MARKET_DATA_SCHEMA,
    CONFIG_SCHEMA,
    PERFORMANCE_SCHEMA,
    ERROR_SCHEMA,
    HEALTH_SCHEMA
)

class StorageFactory:
    """Creates pre-configured storage managers for different data types."""
    
    def __init__(self, base_path: Optional[str] = None, memory_bank: Optional[Union[MemoryBank, MemoryBankManager]] = None):
        """Initialize storage factory.
        
        Args:
            base_path: Base directory for all storage managers
            memory_bank: Optional MemoryBank or MemoryBankManager instance for caching
        """
        if base_path is None:
            base_path = Path(__file__).parent / "data"
        self.base_path = Path(base_path)
        if isinstance(memory_bank, MemoryBankManager):
            self.memory_bank = memory_bank.memory_bank
        else:
            self.memory_bank = memory_bank
    
    def create_trade_storage(self) -> StorageManager:
        """Create storage manager for trade data."""
        return StorageManager(
            base_path=str(self.base_path / "transactions"),
            schema_version="1.0.0",
            memory_bank=self.memory_bank
        )
    
    def create_opportunity_storage(self) -> StorageManager:
        """Create storage manager for opportunity data."""
        return StorageManager(
            base_path=str(self.base_path / "market_data"),
            schema_version="1.0.0",
            memory_bank=self.memory_bank
        )
    
    def create_market_data_storage(self) -> StorageManager:
        """Create storage manager for market data."""
        return StorageManager(
            base_path=str(self.base_path / "analytics"),
            schema_version="1.0.0",
            memory_bank=self.memory_bank
        )
    
    def create_config_storage(self) -> StorageManager:
        """Create storage manager for configuration data."""
        return StorageManager(
            base_path=str(self.base_path / "storage"),
            schema_version="1.0.0",
            memory_bank=self.memory_bank
        )
    
    def create_performance_storage(self) -> StorageManager:
        """Create storage manager for performance metrics."""
        return StorageManager(
            base_path=str(self.base_path / "analytics"),
            schema_version="1.0.0",
            memory_bank=self.memory_bank
        )
    
    def create_error_storage(self) -> StorageManager:
        """Create storage manager for error logs."""
        return StorageManager(
            base_path=str(self.base_path / "temp"),
            schema_version="1.0.0",
            memory_bank=self.memory_bank
        )
    
    def create_health_storage(self) -> StorageManager:
        """Create storage manager for system health data."""
        return StorageManager(
            base_path=str(self.base_path / "cache"),
            schema_version="1.0.0",
            memory_bank=self.memory_bank
        )

class StorageHub:
    """Central hub for accessing all storage managers."""
    
    def __init__(self, base_path: Optional[str] = None, memory_bank: Optional[Union[MemoryBank, MemoryBankManager]] = None):
        """Initialize storage hub.
        
        Args:
            base_path: Base directory for all storage
            memory_bank: Optional MemoryBank or MemoryBankManager instance for caching
        """
        factory = StorageFactory(base_path, memory_bank)
        
        # Create storage managers
        self.trades = factory.create_trade_storage()
        self.opportunities = factory.create_opportunity_storage()
        self.market_data = factory.create_market_data_storage()
        self.config = factory.create_config_storage()
        self.performance = factory.create_performance_storage()
        self.errors = factory.create_error_storage()
        self.health = factory.create_health_storage()
        
        # Register schemas
        self._register_schemas()
    
    def _register_schemas(self) -> None:
        """Register schemas with storage managers."""
        # Store schemas in each manager
        self.trades.store("schema", TRADE_SCHEMA, create_backup=False)
        self.opportunities.store("schema", OPPORTUNITY_SCHEMA, create_backup=False)
        self.market_data.store("schema", MARKET_DATA_SCHEMA, create_backup=False)
        self.config.store("schema", CONFIG_SCHEMA, create_backup=False)
        self.performance.store("schema", PERFORMANCE_SCHEMA, create_backup=False)
        self.errors.store("schema", ERROR_SCHEMA, create_backup=False)
        self.health.store("schema", HEALTH_SCHEMA, create_backup=False)

def create_storage_hub(base_path: Optional[str] = None,
                      memory_bank: Optional[Union[MemoryBank, MemoryBankManager]] = None) -> StorageHub:
    """Create a storage hub instance.
    
    This is the recommended way to create a storage hub, as it ensures proper
    initialization and schema registration.
    
    Args:
        base_path: Base directory for all storage
        memory_bank: Optional MemoryBankManager instance for caching
        
    Returns:
        Initialized StorageHub instance
    
    Example:
        ```python
        from arbitrage_bot.core.memory import get_memory_bank
        from arbitrage_bot.core.storage.factory import create_storage_hub
        
        # Create memory bank for caching
        memory = get_memory_bank()
        
        # Create storage hub
        storage = create_storage_hub(memory_bank=memory)
        
        # Store trade data
        trade = {
            "id": "trade_1",
            "timestamp": 1675432800,
            "pair": "ETH/USDC",
            "dex": "uniswap",
            "amount": 1.5,
            "price": 1850.75,
            "side": "buy",
            "status": "completed"
        }
        
        # Data will be validated against TRADE_SCHEMA
        storage.trades.store("trade_1", trade)
        
        # Retrieve trade data
        stored_trade = storage.trades.retrieve("trade_1")
        ```
    """
    return StorageHub(base_path, memory_bank)
