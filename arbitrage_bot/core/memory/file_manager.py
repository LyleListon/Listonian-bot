"""
File Manager Implementation

This module provides the FileManager class for handling file I/O operations
in an async-safe manner.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Union

logger = logging.getLogger(__name__)

class FileManager:
    """
    Manager for async file I/O operations.
    
    This class provides thread-safe file operations for reading and writing
    data files.
    """
    
    def __init__(self):
        """Initialize the file manager."""
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the file manager."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing file manager")
            self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            self._initialized = False
    
    async def read_json(
        self,
        file_path: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Read JSON data from a file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Parsed JSON data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        if not self._initialized:
            raise RuntimeError("File manager not initialized")
        
        file_path = Path(file_path)
        
        async with self._lock:
            try:
                # Read file in chunks to handle large files
                content = []
                chunk_size = 8192  # 8KB chunks
                
                with open(file_path, 'r') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        content.append(chunk)
                
                data = json.loads(''.join(content))
                return data
                
            except FileNotFoundError:
                logger.error(f"File not found: {file_path}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in file {file_path}: {e}")
                raise
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                raise
    
    async def write_json(
        self,
        file_path: Union[str, Path],
        data: Dict[str, Any]
    ) -> None:
        """
        Write JSON data to a file.
        
        Args:
            file_path: Path to JSON file
            data: Data to write
            
        Raises:
            OSError: If file cannot be written
            TypeError: If data cannot be serialized to JSON
        """
        if not self._initialized:
            raise RuntimeError("File manager not initialized")
        
        file_path = Path(file_path)
        
        async with self._lock:
            try:
                # Create parent directories if needed
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write to temporary file first
                temp_path = file_path.with_suffix('.tmp')
                
                with open(temp_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Rename temporary file to target file
                # This ensures atomic writes
                temp_path.replace(file_path)
                
            except TypeError as e:
                logger.error(f"Cannot serialize data to JSON: {e}")
                raise
            except OSError as e:
                logger.error(f"Error writing file {file_path}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error writing file {file_path}: {e}")
                raise
    
    async def ensure_directory(
        self,
        directory: Union[str, Path]
    ) -> None:
        """
        Ensure a directory exists.
        
        Args:
            directory: Directory path to create
            
        Raises:
            OSError: If directory cannot be created
        """
        if not self._initialized:
            raise RuntimeError("File manager not initialized")
        
        directory = Path(directory)
        
        async with self._lock:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.error(f"Error creating directory {directory}: {e}")
                raise
    
    async def delete_file(
        self,
        file_path: Union[str, Path]
    ) -> None:
        """
        Delete a file.
        
        Args:
            file_path: Path to file to delete
            
        Raises:
            FileNotFoundError: If file doesn't exist
            OSError: If file cannot be deleted
        """
        if not self._initialized:
            raise RuntimeError("File manager not initialized")
        
        file_path = Path(file_path)
        
        async with self._lock:
            try:
                file_path.unlink()
            except FileNotFoundError:
                logger.warning(f"File not found for deletion: {file_path}")
                raise
            except OSError as e:
                logger.error(f"Error deleting file {file_path}: {e}")
                raise
    
    async def list_files(
        self,
        directory: Union[str, Path],
        pattern: str = "*"
    ) -> list[Path]:
        """
        List files in a directory.
        
        Args:
            directory: Directory to list
            pattern: Glob pattern to match
            
        Returns:
            List of matching file paths
            
        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        if not self._initialized:
            raise RuntimeError("File manager not initialized")
        
        directory = Path(directory)
        
        async with self._lock:
            try:
                return list(directory.glob(pattern))
            except Exception as e:
                logger.error(f"Error listing files in {directory}: {e}")
                raise