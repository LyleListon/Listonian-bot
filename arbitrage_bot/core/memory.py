"""
Memory Bank Module

Manages persistent storage and retrieval of system state and context.
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class MemoryBank:
    """Manages system memory and context."""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        """Initialize memory bank."""
        self.initialized = False
        self.memory_dir = Path('memory-bank')
        self.context = {}
        self._last_sync = 0
        self._sync_interval = 300  # 5 minutes
        
    async def initialize(self) -> bool:
        """
        Initialize the memory bank.
        
        Returns:
            True if initialization successful
        """
        try:
            # Create memory directory if it doesn't exist
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            
            # Load all memory files
            await self._load_all_files()
            
            # Start background sync
            asyncio.create_task(self._sync_loop())
            
            self.initialized = True
            logger.info("Memory bank initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize memory bank: {e}")
            return False
            
    async def _load_all_files(self):
        """Load all memory files."""
        try:
            # Load key files
            key_files = [
                'projectbrief.md',
                'activeContext.md',
                'techContext.md',
                'systemPatterns.md',
                'productContext.md',
                'progress.md'
            ]
            
            for filename in key_files:
                file_path = self.memory_dir / filename
                if file_path.exists():
                    async with asyncio.Lock():
                        with open(file_path, 'r') as f:
                            self.context[filename] = f.read()
                            
        except Exception as e:
            logger.error(f"Failed to load memory files: {e}")
            
    async def _sync_loop(self):
        """Background sync loop."""
        while True:
            try:
                await asyncio.sleep(self._sync_interval)
                await self._sync_to_disk()
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(60)  # Longer delay on error
                
    async def _sync_to_disk(self):
        """Sync memory to disk."""
        try:
            async with self._lock:
                current_time = asyncio.get_event_loop().time()
                if current_time - self._last_sync < self._sync_interval:
                    return
                    
                # Update sync time
                self._last_sync = current_time
                
                # Write each context file
                for filename, content in self.context.items():
                    file_path = self.memory_dir / filename
                    with open(file_path, 'w') as f:
                        f.write(content)
                        
                logger.debug("Memory bank synced to disk")
                
        except Exception as e:
            logger.error(f"Failed to sync memory bank: {e}")
            
    async def get_context(self, key: str) -> Optional[str]:
        """
        Get context by key.
        
        Args:
            key: Context key (filename)
            
        Returns:
            Context content if found
        """
        if not self.initialized:
            raise RuntimeError("Memory bank not initialized")
            
        return self.context.get(key)
        
    async def update_context(self, key: str, content: str):
        """
        Update context content.
        
        Args:
            key: Context key (filename)
            content: New content
        """
        if not self.initialized:
            raise RuntimeError("Memory bank not initialized")
            
        async with self._lock:
            self.context[key] = content
            await self._sync_to_disk()
            
    async def get_all_context(self) -> Dict[str, str]:
        """
        Get all context.
        
        Returns:
            Dictionary of all context
        """
        if not self.initialized:
            raise RuntimeError("Memory bank not initialized")
            
        return self.context.copy()

async def get_memory_bank() -> MemoryBank:
    """
    Get or create memory bank instance.
    
    Returns:
        Initialized MemoryBank instance
    """
    async with MemoryBank._lock:
        if MemoryBank._instance is None:
            MemoryBank._instance = MemoryBank()
            if not await MemoryBank._instance.initialize():
                raise RuntimeError("Failed to initialize memory bank")
        return MemoryBank._instance