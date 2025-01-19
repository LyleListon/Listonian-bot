"""
Handles persistence of memory entries to disk and memory.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .memory_types import MemoryEntry, MemoryType

class MemoryStore:
    """Manages persistence of memory entries."""
    
    def __init__(self, storage_dir: str = "data/memory"):
        """Initialize the memory store with a storage directory."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache: Dict[str, MemoryEntry] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load existing memory entries from disk."""
        if not self.storage_dir.exists():
            return

        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    entry = self._deserialize_entry(data)
                    self.memory_cache[entry.id] = entry
            except Exception as e:
                print(f"Error loading memory file {file_path}: {e}")

    def _serialize_entry(self, entry: MemoryEntry) -> dict:
        """Convert a MemoryEntry to a JSON-serializable dict."""
        return {
            'id': entry.id,
            'type': entry.type.value,
            'data': entry.data,
            'timestamp': entry.timestamp.isoformat(),
            'tags': entry.tags,
            'expiry': entry.expiry.isoformat() if entry.expiry else None,
            'priority': entry.priority,
            'metadata': entry.metadata or {}
        }

    def _deserialize_entry(self, data: dict) -> MemoryEntry:
        """Convert a dict to a MemoryEntry."""
        return MemoryEntry(
            id=data['id'],
            type=MemoryType(data['type']),
            data=data['data'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            tags=data['tags'],
            expiry=datetime.fromisoformat(data['expiry']) if data['expiry'] else None,
            priority=data['priority'],
            metadata=data['metadata']
        )

    def save(self, entry: MemoryEntry) -> None:
        """Save a memory entry to both cache and disk."""
        self.memory_cache[entry.id] = entry
        
        file_path = self.storage_dir / f"{entry.id}.json"
        with open(file_path, 'w') as f:
            json.dump(self._serialize_entry(entry), f, indent=2)

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        return self.memory_cache.get(entry_id)

    def delete(self, entry_id: str) -> None:
        """Delete a memory entry from both cache and disk."""
        if entry_id in self.memory_cache:
            del self.memory_cache[entry_id]
            
        file_path = self.storage_dir / f"{entry_id}.json"
        if file_path.exists():
            file_path.unlink()

    def list_entries(self, 
                     memory_type: Optional[MemoryType] = None,
                     tags: Optional[List[str]] = None) -> List[MemoryEntry]:
        """List memory entries, optionally filtered by type and tags."""
        entries = list(self.memory_cache.values())
        
        if memory_type:
            entries = [e for e in entries if e.type == memory_type]
            
        if tags:
            entries = [e for e in entries if all(tag in e.tags for tag in tags)]
            
        return sorted(entries, key=lambda x: x.timestamp, reverse=True)

    def cleanup_expired(self) -> None:
        """Remove expired memory entries."""
        now = datetime.now()
        expired_ids = [
            entry_id for entry_id, entry in self.memory_cache.items()
            if entry.expiry and entry.expiry < now
        ]
        
        for entry_id in expired_ids:
            self.delete(entry_id)