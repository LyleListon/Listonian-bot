"""
Type definitions for memory bank entries and operations.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

class MemoryType(Enum):
    """Types of memory entries that can be stored."""
    TRANSACTION = "transaction"
    MARKET_STATE = "market_state"
    EXECUTION_RESULT = "execution_result"
    ERROR = "error"
    SYSTEM_STATE = "system_state"
    CUSTOM = "custom"

@dataclass
class MemoryEntry:
    """Represents a single memory entry in the memory bank."""
    id: str
    type: MemoryType
    data: Dict[str, Any]
    timestamp: datetime
    tags: list[str]
    expiry: Optional[datetime] = None
    priority: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}