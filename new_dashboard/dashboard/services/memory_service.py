"""Memory service for managing application state."""

import asyncio
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path
import json
from datetime import datetime

from ..core.logging import get_logger
from .file_handler import FileManager

logger = get_logger("memory_service")

class MemoryService:
    """Service for managing application memory and state."""
    
    def __init__(self, base_dir: str):
        """Initialize memory service.
        
        Args:
            base_dir: Base directory for memory files (as string)
        """
        self.base_dir = Path(base_dir)
        self.file_manager = FileManager(self.base_dir)
        self._subscribers: List[asyncio.Queue] = []
        self._current_state: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        
    async def initialize(self):
        """Initialize the memory service."""
        if self._initialized:
            return
            
        try:
            logger.info(f"Setting storage directory to absolute path: {self.base_dir.absolute()}")
            
            # Initialize file manager
            await self.file_manager.initialize()
            
            # Subscribe to file changes
            self.file_manager.subscribe_to_changes(self._handle_file_change)
            
            # Load initial state
            await self._load_state()
            
            self._initialized = True
            logger.info("Memory service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing memory service: {e}")
            await self.cleanup()
            raise
            
    async def cleanup(self):
        """Clean up resources."""
        try:
            # Unsubscribe from file changes
            if hasattr(self, 'file_manager'):
                self.file_manager.unsubscribe_from_changes(self._handle_file_change)
            
            # Clean up file manager
            await self.file_manager.cleanup()
            
            # Clear subscribers
            self._subscribers.clear()
            
            self._initialized = False
            logger.info("Memory service shut down")
            
        except Exception as e:
            logger.error(f"Error during memory service cleanup: {e}")
            raise
            
    async def _load_state(self):
        """Load state from files."""
        try:
            async with self._lock:
                # Load trades
                trades_data = await self.file_manager.read_file('trades')
                self._current_state['trade_history'] = trades_data.get('trades', [])
                
                # Load metrics
                metrics_data = await self.file_manager.read_file('metrics')
                self._current_state['metrics'] = metrics_data
                
                logger.debug(f"Loaded state: {json.dumps(self._current_state, indent=2)}")
                
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            raise
            
    async def _handle_file_change(self, file_key: str, content: Dict[str, Any]):
        """Handle file change notifications."""
        try:
            async with self._lock:
                if file_key == 'trades':
                    self._current_state['trade_history'] = content.get('trades', [])
                elif file_key == 'metrics':
                    self._current_state['metrics'] = content
                    
                # Notify subscribers
                await self._notify_subscribers()
                
        except Exception as e:
            logger.error(f"Error handling file change: {e}")
            
    async def _notify_subscribers(self):
        """Notify subscribers of state changes."""
        if not self._subscribers:
            return
            
        try:
            # Create a copy of the state to avoid modification during sending
            state_copy = {
                'trade_history': self._current_state.get('trade_history', [])[:],
                'metrics': dict(self._current_state.get('metrics', {})),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Send to all subscribers
            for queue in self._subscribers:
                try:
                    await queue.put(state_copy)
                except Exception as e:
                    logger.error(f"Error notifying subscriber: {e}")
                    
        except Exception as e:
            logger.error(f"Error in notify subscribers: {e}")
            
    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to state updates.
        
        Returns:
            Queue that will receive state updates
        """
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        
        # Send initial state
        try:
            state_copy = {
                'trade_history': self._current_state.get('trade_history', [])[:],
                'metrics': dict(self._current_state.get('metrics', {})),
                'timestamp': datetime.utcnow().isoformat()
            }
            await queue.put(state_copy)
        except Exception as e:
            logger.error(f"Error sending initial state to subscriber: {e}")
            
        return queue
        
    async def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from state updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
            
    async def get_current_state(self) -> Dict[str, Any]:
        """Get current application state.
        
        Returns:
            Current state dictionary
        """
        async with self._lock:
            return {
                'trade_history': self._current_state.get('trade_history', [])[:],
                'metrics': dict(self._current_state.get('metrics', {})),
                'timestamp': datetime.utcnow().isoformat()
            }
            
    async def update_state(self, updates: Dict[str, Any]):
        """Update application state.
        
        Args:
            updates: Dictionary of state updates
        """
        async with self._lock:
            # Update state
            if 'trade_history' in updates:
                self._current_state['trade_history'] = updates['trade_history'][:]
            if 'metrics' in updates:
                self._current_state['metrics'] = dict(updates['metrics'])
                
            # Write to files
            if 'trade_history' in updates:
                await self.file_manager.write_file('trades', {
                    'trades': self._current_state['trade_history']
                })
            if 'metrics' in updates:
                await self.file_manager.write_file('metrics', 
                    self._current_state['metrics']
                )
                
            # Notify subscribers
            await self._notify_subscribers()