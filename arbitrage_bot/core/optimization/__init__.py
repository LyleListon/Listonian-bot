"""
Performance Optimization Components

This package provides performance optimization components for the Listonian Arbitrage Bot:
- Memory-Mapped Files
- WebSocket Optimization
- Resource Management
"""

# Import main components for easier access
from .shared_memory import (
    SharedMemoryManager,
    SharedMetricsStore,
    SharedStateManager,
    MemoryRegionType,
    MemoryRegionInfo,
    LockType,
    MemoryRegionNotFoundError,
    SchemaValidationError,
    CorruptDataError,
    LockAcquisitionError,
    SharedMemoryError
)

from .websocket_optimization import (
    OptimizedWebSocketClient,
    WebSocketConnectionPool,
    MessageFormat,
    MessagePriority,
    Message
)

from .resource_manager import (
    ResourceManager,
    ResourceType,
    TaskPriority,
    ResourceUsage
)

# Version
__version__ = '1.0.0'
