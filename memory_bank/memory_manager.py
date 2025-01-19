"""
Main interface for memory bank operations.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .memory_store import MemoryStore
from .memory_types import MemoryEntry, MemoryType

class MemoryManager:
    """Manages memory operations and provides the main interface for the memory bank."""
    
    def __init__(self, storage_dir: str = "data/memory"):
        """Initialize the memory manager with a storage directory."""
        self.store = MemoryStore(storage_dir)

    def create_entry(self,
                    type: MemoryType,
                    data: Dict[str, Any],
                    tags: List[str] = None,
                    expiry: Optional[datetime] = None,
                    priority: int = 0,
                    metadata: Dict[str, Any] = None) -> MemoryEntry:
        """Create and store a new memory entry."""
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            type=type,
            data=data,
            timestamp=datetime.now(),
            tags=tags or [],
            expiry=expiry,
            priority=priority,
            metadata=metadata
        )
        self.store.save(entry)
        return entry

    def get_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        return self.store.get(entry_id)

    def delete_entry(self, entry_id: str) -> None:
        """Delete a memory entry by ID."""
        self.store.delete(entry_id)

    def list_entries(self,
                    memory_type: Optional[MemoryType] = None,
                    tags: Optional[List[str]] = None) -> List[MemoryEntry]:
        """List memory entries with optional filtering."""
        return self.store.list_entries(memory_type, tags)

    def cleanup_expired(self) -> None:
        """Remove all expired memory entries."""
        self.store.cleanup_expired()

    def create_temporary_entry(self,
                             type: MemoryType,
                             data: Dict[str, Any],
                             duration: timedelta,
                             tags: List[str] = None,
                             priority: int = 0,
                             metadata: Dict[str, Any] = None) -> MemoryEntry:
        """Create a memory entry that expires after a specified duration."""
        expiry = datetime.now() + duration
        return self.create_entry(
            type=type,
            data=data,
            tags=tags,
            expiry=expiry,
            priority=priority,
            metadata=metadata
        )

    def update_entry(self,
                    entry_id: str,
                    data: Optional[Dict[str, Any]] = None,
                    tags: Optional[List[str]] = None,
                    expiry: Optional[datetime] = None,
                    priority: Optional[int] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> Optional[MemoryEntry]:
        """Update an existing memory entry."""
        entry = self.store.get(entry_id)
        if not entry:
            return None

        if data is not None:
            entry.data = data
        if tags is not None:
            entry.tags = tags
        if expiry is not None:
            entry.expiry = expiry
        if priority is not None:
            entry.priority = priority
        if metadata is not None:
            entry.metadata = metadata

        self.store.save(entry)
        return entry

    def search_by_tag(self, tag: str) -> List[MemoryEntry]:
        """Search for memory entries with a specific tag."""
        return self.list_entries(tags=[tag])

    def get_entries_by_type(self, memory_type: MemoryType) -> List[MemoryEntry]:
        """Get all memory entries of a specific type."""
        return self.list_entries(memory_type=memory_type)

    def get_recent_entries(self, 
                          limit: int = 10, 
                          memory_type: Optional[MemoryType] = None) -> List[MemoryEntry]:
        """Get the most recent memory entries."""
        entries = self.list_entries(memory_type=memory_type)
        return entries[:limit]