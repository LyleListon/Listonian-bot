"""
Memory Bank Module

Manages persistent storage and retrieval of system state and context.
"""

import logging
import asyncio
import json
import time
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
                current_time = time.monotonic()  # Use monotonic time instead of event loop time
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

    async def store_trade_result(
        self,
        opportunity: Dict[str, Any],
        success: bool,
        net_profit: Optional[float] = None,
        gas_cost: Optional[float] = None,
        tx_hash: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Store trade result in memory bank.

        Args:
            opportunity: Trade opportunity details
            success: Whether trade was successful
            net_profit: Optional net profit amount
            gas_cost: Optional gas cost
            tx_hash: Optional transaction hash
            error: Optional error message
        """
        try:
            if not self.initialized:
                raise RuntimeError("Memory bank not initialized")

            # Create trade record
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'opportunity': opportunity,
                'success': success,
                'net_profit': net_profit,
                'gas_cost': gas_cost,
                'tx_hash': tx_hash,
                'error': error
            }

            # Update progress file
            progress_path = self.memory_dir / 'progress.md'
            try:
                if progress_path.exists():
                    current_content = await self.get_context('progress.md')
                else:
                    current_content = "# Trading Progress\n\n"

                # Add trade record
                trade_entry = (
                    f"\n## Trade at {trade_record['timestamp']}\n"
                    f"- Success: {success}\n"
                    f"- Net Profit: {net_profit if net_profit is not None else 'N/A'}\n"
                    f"- Gas Cost: {gas_cost if gas_cost is not None else 'N/A'}\n"
                    f"- TX Hash: {tx_hash if tx_hash else 'N/A'}\n"
                )
                if error:
                    trade_entry += f"- Error: {error}\n"

                # Update context
                await self.update_context('progress.md', current_content + trade_entry)

            except Exception as e:
                logger.error(f"Failed to update progress file: {e}")
                # Continue even if progress update fails

            # Store detailed trade data
            trades_dir = self.memory_dir / 'trades'
            trades_dir.mkdir(exist_ok=True)
            
            trade_file = trades_dir / f"trade_{int(time.time())}.json"
            with open(trade_file, 'w') as f:
                json.dump(trade_record, f, indent=2)

            logger.info(
                f"Trade result stored: success={success}, "
                f"profit={net_profit}, gas={gas_cost}"
            )

        except Exception as e:
            logger.error(f"Failed to store trade result: {e}")
            raise

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