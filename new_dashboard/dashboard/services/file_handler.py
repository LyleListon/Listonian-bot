"""Memory-mapped file handler for high-performance file operations."""

import mmap
import os
import json
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import aiofiles
import aiofiles.os

from ..core.logging import get_logger

logger = get_logger("file_handler")

class FileChangeHandler(FileSystemEventHandler):
    """Handle file system events for memory-mapped files."""
    
    def __init__(self, loop: asyncio.AbstractEventLoop, callback):
        self.loop = loop
        self.callback = callback
        
    def on_modified(self, event):
        if not event.is_directory:
            self.loop.call_soon_threadsafe(
                lambda: asyncio.run_coroutine_threadsafe(
                    self.callback(event.src_path), self.loop
                )
            )

class AsyncMemoryMappedFile:
    """Handle memory-mapped file operations with async support."""
    
    def __init__(self, file_path: Path, max_size: int = 1024 * 1024):
        """Initialize memory-mapped file.
        
        Args:
            file_path: Path to the file
            max_size: Maximum file size in bytes (default: 1MB)
        """
        self.file_path = file_path
        self.max_size = max_size
        self._mmap: Optional[mmap.mmap] = None
        self._file = None
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize the memory-mapped file."""
        try:
            # Ensure file exists with minimum size
            if not self.file_path.exists():
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(self.file_path, 'w') as f:
                    await f.write('{}')
            
            # Ensure file is at least max_size
            stat = await aiofiles.os.stat(self.file_path)
            if stat.st_size < self.max_size:
                async with aiofiles.open(self.file_path, 'ab') as f:
                    await f.write(b'\0' * (self.max_size - stat.st_size))
            
            # Open file and create memory mapping
            self._file = await aiofiles.open(self.file_path, 'r+b')
            raw_file = self._file.fileno()
            self._mmap = mmap.mmap(raw_file, 0, access=mmap.ACCESS_READ)
            logger.info(f"Initialized memory-mapped file: {self.file_path}")
            
        except Exception as e:
            logger.error(f"Error initializing memory-mapped file {self.file_path}: {e}")
            await self.cleanup()
            raise
            
    async def cleanup(self):
        """Clean up resources."""
        async with self._lock:
            if self._mmap:
                try:
                    self._mmap.close()
                except Exception as e:
                    logger.error(f"Error closing mmap: {e}")
                self._mmap = None
                
            if self._file:
                try:
                    await self._file.close()
                except Exception as e:
                    logger.error(f"Error closing file: {e}")
                self._file = None
    
    async def read(self) -> Dict[str, Any]:
        """Read content from memory-mapped file."""
        if not self._mmap:
            raise RuntimeError("Memory-mapped file not initialized")
            
        async with self._lock:
            try:
                # Create a copy of the memory-mapped content
                self._mmap.seek(0)
                content = self._mmap.read()
                
                # Find the end of the JSON content
                null_pos = content.find(b'\0')
                if null_pos != -1:
                    content = content[:null_pos]
                    
                # Decode and parse JSON
                try:
                    return json.loads(content.decode('utf-8'))
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in memory-mapped file")
                    return {}
            except Exception as e:
                logger.error(f"Error reading from memory-mapped file: {e}")
                return {}
    
    async def write(self, data: Dict[str, Any]):
        """Write content to memory-mapped file."""
        if not self._mmap:
            raise RuntimeError("Memory-mapped file not initialized")
            
        # Write to file first
        async with aiofiles.open(self.file_path, 'r+b') as f:
            try:
                # Convert data to bytes
                content = json.dumps(data).encode()
                if len(content) > self.max_size:
                    raise ValueError(f"Data size ({len(content)}) exceeds maximum size ({self.max_size})")
                
                # Write content and padding
                await f.write(content)
                padding_size = self.max_size - len(content)
                if padding_size > 0:
                    await f.write(b'\0' * padding_size)
                await f.flush()
                
            except Exception as e:
                logger.error(f"Error writing to file: {e}")
                raise
            
        # Re-read from memory map to ensure consistency
        self._mmap.seek(0)

class FileManager:
    """Manage memory-mapped files and file system watching."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.files: Dict[str, AsyncMemoryMappedFile] = {}
        self.observer: Optional[Observer] = None
        self._change_callbacks = []
        self._initialized = False
        self._loop = None
        
    async def initialize(self):
        """Initialize file manager."""
        if self._initialized:
            return
            
        try:
            # Get event loop
            self._loop = asyncio.get_running_loop()
            
            # Create required directories
            for subdir in ['trades', 'state', 'metrics']:
                (self.base_dir / subdir).mkdir(parents=True, exist_ok=True)
            
            # Initialize memory-mapped files
            self.files['trades'] = AsyncMemoryMappedFile(
                self.base_dir / 'trades' / 'recent_trades.json',
                max_size=2 * 1024 * 1024  # 2MB for trade history
            )
            self.files['metrics'] = AsyncMemoryMappedFile(
                self.base_dir / 'state' / 'metrics.json',
                max_size=1024 * 1024  # 1MB for metrics
            )
            
            # Initialize all files
            for file in self.files.values():
                await file.initialize()
            
            # Set up file watching
            self.observer = Observer()
            handler = FileChangeHandler(self._loop, self._handle_file_change)
            self.observer.schedule(handler, str(self.base_dir), recursive=True)
            self.observer.start()
            
            self._initialized = True
            logger.info("File manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing file manager: {e}")
            await self.cleanup()
            raise
            
    async def cleanup(self):
        """Clean up resources."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            
        for file in self.files.values():
            await file.cleanup()
            
        self.files.clear()
        self._initialized = False
        
    def subscribe_to_changes(self, callback):
        """Subscribe to file change notifications."""
        self._change_callbacks.append(callback)
        
    def unsubscribe_from_changes(self, callback):
        """Unsubscribe from file change notifications."""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
            
    async def _handle_file_change(self, file_path: str):
        """Handle file change events."""
        try:
            path = Path(file_path)
            file_key = None
            
            # Determine which file changed
            if 'trades' in str(path):
                file_key = 'trades'
            elif 'metrics' in str(path):
                file_key = 'metrics'
                
            if file_key and file_key in self.files:
                # Read updated content
                content = await self.files[file_key].read()
                
                # Notify subscribers
                for callback in self._change_callbacks:
                    try:
                        await callback(file_key, content)
                    except Exception as e:
                        logger.error(f"Error in file change callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error handling file change: {e}")
            
    async def read_file(self, file_key: str) -> Dict[str, Any]:
        """Read content from a memory-mapped file."""
        if not self._initialized:
            raise RuntimeError("File manager not initialized")
            
        if file_key not in self.files:
            raise KeyError(f"Unknown file key: {file_key}")
            
        return await self.files[file_key].read()
        
    async def write_file(self, file_key: str, data: Dict[str, Any]):
        """Write content to a memory-mapped file."""
        if not self._initialized:
            raise RuntimeError("File manager not initialized")
            
        if file_key not in self.files:
            raise KeyError(f"Unknown file key: {file_key}")
            
        await self.files[file_key].write(data)