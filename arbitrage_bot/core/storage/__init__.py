"""Storage system for arbitrage bot data."""

from typing import Dict, Any, Optional, List, Union, TypeVar, Generic
from dataclasses import dataclass, asdict
import json
import os
import time
import shutil
from pathlib import Path
from datetime import datetime
from ..memory import MemoryBank, MemoryBankManager

T = TypeVar('T')

@dataclass
class StorageMetadata:
    """Metadata for stored items."""
    schema_version: str
    created_at: float
    updated_at: float
    checksum: str
    category: str
    backup_path: Optional[str] = None

class StorageError(Exception):
    """Base class for storage errors."""
    pass

class ValidationError(StorageError):
    """Raised when data validation fails."""
    pass

class SchemaError(StorageError):
    """Raised when schema validation fails."""
    pass

class BackupError(StorageError):
    """Raised when backup operations fail."""
    pass

class StorageManager(Generic[T]):
    """Manages persistent storage with validation, backup, and recovery."""
    
    def __init__(self, base_path: Optional[str] = None, schema_version: str = "1.0.0",
                 memory_bank: Optional[Union[MemoryBank, MemoryBankManager]] = None):
        """Initialize storage manager.
        
        Args:
            base_path: Base directory for storage. Defaults to storage/ in current dir.
            schema_version: Version of the data schema being used
            memory_bank: Optional MemoryBank or MemoryBankManager instance for caching
        """
        if base_path is None:
            base_path = os.path.join(os.path.dirname(__file__), "data")
        
        self.base_path = Path(base_path)
        self.schema_version = schema_version
        if isinstance(memory_bank, MemoryBankManager):
            self.memory_bank = memory_bank.memory_bank
        else:
            self.memory_bank = memory_bank
        
        # Determine category from base path
        self.category = self.base_path.name
        if self.category not in ["market_data", "transactions", "analytics", "docs", "temp", "storage", "cache"]:
            self.category = "storage"  # Default category
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Load existing metadata
        self._metadata: Dict[str, StorageMetadata] = {}
        self._load_metadata()
    
    def _ensure_directories(self) -> None:
        """Create required directory structure."""
        directories = [
            self.base_path,
            self.base_path / "data",
            self.base_path / "backups",
            self.base_path / "metadata",
            self.base_path / "schemas"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_metadata(self) -> None:
        """Load metadata for all stored items."""
        metadata_path = self.base_path / "metadata" / "items.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    data = json.load(f)
                    self._metadata = {
                        k: StorageMetadata(**v) for k, v in data.items()
                    }
            except json.JSONDecodeError:
                # Start fresh if metadata is corrupted
                self._metadata = {}
    
    def _save_metadata(self) -> None:
        """Save current metadata to disk."""
        metadata_path = self.base_path / "metadata" / "items.json"
        with open(metadata_path, 'w') as f:
            json.dump({k: asdict(v) for k, v in self._metadata.items()}, f, indent=2)
    
    def _calculate_checksum(self, data: Any) -> str:
        """Calculate checksum for data validation."""
        import hashlib
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
    
    def _validate_schema(self, data: Any, schema: Dict) -> None:
        """Validate data against JSON schema."""
        from jsonschema import validate, ValidationError as JsonValidationError
        try:
            validate(instance=data, schema=schema)
        except JsonValidationError as e:
            raise ValidationError("Schema validation failed: %s" % str(e))
    
    def store(self, key: str, data: T, schema: Optional[Dict] = None,
              create_backup: bool = True) -> StorageMetadata:
        """Store data with optional schema validation and backup.
        
        Args:
            key: Unique identifier for the data
            data: Data to store
            schema: Optional JSON schema for validation
            create_backup: Whether to create a backup of existing data
            
        Returns:
            Metadata about the stored item
            
        Raises:
            ValidationError: If schema validation fails
            StorageError: If storage operations fail
        """
        # Validate schema if provided
        if schema:
            self._validate_schema(data, schema)
            
            # Store schema for future validation
            schema_path = self.base_path / "schemas" / (key + ".json")
            with open(schema_path, 'w') as f:
                json.dump(schema, f, indent=2)
        
        # Create backup of existing data if requested
        if create_backup and key in self._metadata:
            try:
                self._create_backup(key)
            except Exception as e:
                raise BackupError("Failed to create backup: %s" % str(e))
        
        # Store data
        now = time.time()
        file_path = self.base_path / "data" / (key + ".json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise StorageError("Failed to store data: %s" % str(e))
        
        # Update metadata
        metadata = StorageMetadata(
            schema_version=self.schema_version,
            created_at=self._metadata[key].created_at if key in self._metadata else now,
            updated_at=now,
            checksum=self._calculate_checksum(data),
            category=self.category,
            backup_path=str(self.base_path / "backups" / (key + "_" + str(now) + ".json"))
                         if create_backup and key in self._metadata else None
        )
        self._metadata[key] = metadata
        self._save_metadata()
        
        # Update cache if memory bank is available
        if self.memory_bank:
            self.memory_bank.store(key, data, self.category, ttl=None)
        
        return metadata
    
    def retrieve(self, key: str, validate: bool = True) -> Optional[T]:
        """Retrieve stored data with optional validation.
        
        Args:
            key: Key to retrieve
            validate: Whether to validate checksum
            
        Returns:
            Retrieved data or None if not found
            
        Raises:
            ValidationError: If checksum validation fails
            StorageError: If retrieval fails
        """
        # Check cache first if memory bank is available
        if self.memory_bank:
            cached = self.memory_bank.retrieve(key, category=self.category)
            if cached is not None:
                return cached
        
        # Check if key exists
        if key not in self._metadata:
            return None
        
        file_path = self.base_path / "data" / (key + ".json")
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Validate checksum if requested
            if validate:
                checksum = self._calculate_checksum(data)
                if checksum != self._metadata[key].checksum:
                    raise ValidationError(
                        "Checksum validation failed for %s. Expected %s, got %s" % (
                            key, self._metadata[key].checksum, checksum
                        )
                    )
            
            # Update cache if memory bank is available
            if self.memory_bank:
                self.memory_bank.store(key, data, self.category, ttl=None)
            
            return data
        except Exception as e:
            raise StorageError("Failed to retrieve data: %s" % str(e))
    
    def _create_backup(self, key: str) -> None:
        """Create backup of existing data."""
        source = self.base_path / "data" / (key + ".json")
        if not source.exists():
            return
        
        timestamp = time.time()
        backup = self.base_path / "backups" / (key + "_" + str(timestamp) + ".json")
        
        try:
            shutil.copy2(source, backup)
        except Exception as e:
            raise BackupError("Failed to create backup: %s" % str(e))
    
    def restore_backup(self, key: str, timestamp: Optional[float] = None) -> StorageMetadata:
        """Restore data from backup.
        
        Args:
            key: Key to restore
            timestamp: Specific backup timestamp to restore, or latest if None
            
        Returns:
            Metadata for restored data
            
        Raises:
            StorageError: If restore fails
        """
        # Find backup file
        if timestamp:
            backup = self.base_path / "backups" / (key + "_" + str(timestamp) + ".json")
            if not backup.exists():
                raise StorageError("Backup not found for timestamp %s" % str(timestamp))
        else:
            # Find latest backup
            backups = list(self.base_path.glob("backups/" + key + "_*.json"))
            if not backups:
                raise StorageError("No backups found")
            backup = max(backups, key=lambda p: float(p.stem.split('_')[1]))
        
        # Restore data
        try:
            with open(backup, 'r') as f:
                data = json.load(f)
            return self.store(key, data, create_backup=False)
        except Exception as e:
            raise StorageError("Failed to restore backup: %s" % str(e))
    
    def list_backups(self, key: str) -> List[float]:
        """List available backup timestamps for a key.
        
        Args:
            key: Key to list backups for
            
        Returns:
            List of backup timestamps
        """
        backups = list(self.base_path.glob("backups/" + key + "_*.json"))
        return [float(p.stem.split('_')[1]) for p in backups]
    
    def get_metadata(self, key: str) -> Optional[StorageMetadata]:
        """Get metadata for stored item.
        
        Args:
            key: Key to get metadata for
            
        Returns:
            Metadata or None if key not found
        """
        return self._metadata.get(key)
    
    def list_keys(self) -> List[str]:
        """List all stored keys.
        
        Returns:
            List of stored keys
        """
        return list(self._metadata.keys())

    def retrieve_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve most recent items.
        
        Args:
            limit: Maximum number of items to retrieve
            
        Returns:
            List of recent items sorted by updated_at timestamp
        """
        # Get all keys sorted by updated_at timestamp
        sorted_keys = sorted(
            self._metadata.keys(),
            key=lambda k: self._metadata[k].updated_at,
            reverse=True
        )[:limit]
        
        # Retrieve data for each key
        items = []
        for key in sorted_keys:
            data = self.retrieve(key)
            if data:
                items.append({
                    'key': key,
                    'data': data,
                    'metadata': asdict(self._metadata[key])
                })
        
        return items
    
    def delete(self, key: str, keep_backups: bool = True) -> None:
        """Delete stored data.
        
        Args:
            key: Key to delete
            keep_backups: Whether to keep backup files
        """
        # Remove data file
        file_path = self.base_path / "data" / (key + ".json")
        if file_path.exists():
            file_path.unlink()
        
        # Remove schema if exists
        schema_path = self.base_path / "schemas" / (key + ".json")
        if schema_path.exists():
            schema_path.unlink()
        
        # Remove backups if requested
        if not keep_backups:
            for backup in self.base_path.glob("backups/" + key + "_*.json"):
                backup.unlink()
        
        # Remove from metadata
        if key in self._metadata:
            del self._metadata[key]
            self._save_metadata()
        
        # Remove from cache if memory bank is available
        if self.memory_bank:
            self.memory_bank.clear(key, category=self.category)
