"""File manager for memory bank with improved file access handling."""

import os
import json
import logging
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class FileManager:
    """Manages file operations with proper locking and retries."""

    def __init__(self, base_path: str):
        """Initialize file manager."""
        self.base_path = Path(base_path).resolve()
        self._file_locks = defaultdict(asyncio.Lock)
        self._dir_locks = defaultdict(asyncio.Lock)
        
        # Constants
        self.MAX_RETRIES = 3
        self.BASE_DELAY = 0.1  # 100ms
        self.MAX_DELAY = 1.0  # 1 second
        
    def _get_file_lock(self, file_path: str) -> asyncio.Lock:
        """Get lock for specific file."""
        return self._file_locks[str(Path(file_path).resolve())]
        
    def _get_dir_lock(self, dir_path: str) -> asyncio.Lock:
        """Get lock for specific directory."""
        return self._dir_locks[str(Path(dir_path).resolve())]
        
    async def read_json(self, relative_path: str) -> Optional[Dict[str, Any]]:
        """Read JSON file with retries and proper locking."""
        file_path = (self.base_path / relative_path).resolve()
        file_lock = self._get_file_lock(str(file_path))
        dir_lock = self._get_dir_lock(str(file_path.parent))
        
        for attempt in range(self.MAX_RETRIES):
            try:
                # First acquire directory lock
                async with dir_lock:
                    # Then acquire file lock
                    async with file_lock:
                        if file_path.exists():
                            with open(file_path, 'rb') as f:
                                json_data = f.read()
                                return json.loads(json_data.decode('utf-8'))
                        return None
                        
            except (IOError, OSError) as e:
                delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                logger.warning("Attempt %d failed to read %s: %s", attempt + 1, str(file_path), str(e))
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                    continue
                logger.error("Failed to read %s after %d attempts", str(file_path), self.MAX_RETRIES)
                return None
                
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in %s: %s", str(file_path), str(e))
                return None
                
            except Exception as e:
                logger.error("Unexpected error reading %s: %s", str(file_path), str(e))
                return None
                
    async def write_json(self, relative_path: str, data: Any) -> bool:
        """Write JSON file with retries and proper locking."""
        file_path = (self.base_path / relative_path).resolve()
        file_lock = self._get_file_lock(str(file_path))
        dir_lock = self._get_dir_lock(str(file_path.parent))
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        temp_path = None
        for attempt in range(self.MAX_RETRIES):
            try:
                # Prepare data
                json_data = json.dumps(data, indent=2).encode('utf-8')
                
                # Create temporary file path
                temp_path = file_path.with_suffix("." + uuid.uuid4().hex + ".tmp")
                
                # First acquire directory lock
                async with dir_lock:
                    # Write to temporary file
                    with open(temp_path, 'wb') as f:
                        f.write(json_data)
                        f.flush()
                        os.fsync(f.fileno())
                    
                    # Then acquire file lock for the rename
                    async with file_lock:
                        # Small delay to let other processes release the file
                        await asyncio.sleep(0.1)
                        
                        # Try to copy first (for cross-device moves)
                        try:
                            # If target exists, try to remove it first
                            if file_path.exists():
                                file_path.unlink()
                            os.rename(temp_path, file_path)
                        except OSError:
                            # If rename fails, try copy and delete
                            with open(temp_path, 'rb') as src:
                                with open(file_path, 'wb') as dst:
                                    dst.write(src.read())
                                    dst.flush()
                                    os.fsync(dst.fileno())
                            os.unlink(temp_path)
                            temp_path = None
                        
                        return True
                        
            except (IOError, OSError) as e:
                delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                logger.warning("Attempt %d failed to write %s: %s", attempt + 1, str(file_path), str(e))
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                    continue
                logger.error("Failed to write %s after %d attempts", str(file_path), self.MAX_RETRIES)
                return False
                
            except Exception as e:
                logger.error("Unexpected error writing %s: %s", str(file_path), str(e))
                return False
                
            finally:
                # Clean up temporary file if it still exists
                try:
                    if temp_path and temp_path.exists():
                        temp_path.unlink()
                except:
                    pass
                
    async def delete_file(self, relative_path: str) -> bool:
        """Delete file with retries and proper locking."""
        file_path = (self.base_path / relative_path).resolve()
        file_lock = self._get_file_lock(str(file_path))
        dir_lock = self._get_dir_lock(str(file_path.parent))
        
        for attempt in range(self.MAX_RETRIES):
            try:
                async with dir_lock:
                    async with file_lock:
                        if file_path.exists():
                            file_path.unlink()
                        return True
                        
            except (IOError, OSError) as e:
                delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                logger.warning("Attempt %d failed to delete %s: %s", attempt + 1, str(file_path), str(e))
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                    continue
                logger.error("Failed to delete %s after %d attempts", str(file_path), self.MAX_RETRIES)
                return False
                
            except Exception as e:
                logger.error("Unexpected error deleting %s: %s", str(file_path), str(e))
                return False
                
    async def ensure_directory(self, relative_path: str) -> bool:
        """Ensure directory exists with retries."""
        dir_path = (self.base_path / relative_path).resolve()
        dir_lock = self._get_dir_lock(str(dir_path))
        
        for attempt in range(self.MAX_RETRIES):
            try:
                async with dir_lock:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    return True
                    
            except (IOError, OSError) as e:
                delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                logger.warning("Attempt %d failed to create directory %s: %s", attempt + 1, str(dir_path), str(e))
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                    continue
                logger.error("Failed to create directory %s after %d attempts", str(dir_path), self.MAX_RETRIES)
                return False
                
            except Exception as e:
                logger.error("Unexpected error creating directory %s: %s", str(dir_path), str(e))
                return False