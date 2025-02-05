"""Time series data storage implementation."""

import logging
import sqlite3
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path

from ..base import DataStorage

class TimeSeriesStorage(DataStorage):
    """Store time series data efficiently."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize time series storage.
        
        Args:
            config: Configuration dictionary containing:
                - database_path: Path to SQLite database
                - retention_days: How long to keep data
                - compression_enabled: Whether to compress old data
                - backup_enabled: Whether to backup data
        """
        super().__init__(config)
        self.db_path = Path(config.get('database_path', 'data/timeseries.db'))
        self.retention_days = config.get('retention_days', 30)
        self.compression_enabled = config.get('compression_enabled', True)
        self.backup_enabled = config.get('backup_enabled', True)
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._initialize_db()
        
    def _initialize_db(self):
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Create tables if they don't exist
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS raw_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        collector TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        data TEXT NOT NULL,
                        compressed BOOLEAN DEFAULT 0
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS processed_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        processor TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        features TEXT NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create indexes
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_raw_timestamp 
                    ON raw_data(timestamp)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_raw_collector 
                    ON raw_data(collector)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_processed_timestamp 
                    ON processed_data(timestamp)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_processed_processor 
                    ON processed_data(processor)
                ''')
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
            
    async def store(self, data: Dict[str, Any]):
        """
        Store data.
        
        Args:
            data: Data to store
        """
        try:
            timestamp = data.get('timestamp', datetime.utcnow().isoformat())
            collector = data.get('collector', 'unknown')
            
            # Store raw data
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'INSERT INTO raw_data (collector, timestamp, data) VALUES (?, ?, ?)',
                    (
                        collector,
                        timestamp,
                        json.dumps(data)
                    )
                )
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error storing data: {e}")
            raise
            
    async def store_processed(
        self,
        processor: str,
        timestamp: str,
        features: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Store processed features.
        
        Args:
            processor: Name of processor that generated features
            timestamp: Timestamp of data
            features: Feature dictionary
            metadata: Optional metadata
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    '''
                    INSERT INTO processed_data 
                    (processor, timestamp, features, metadata) 
                    VALUES (?, ?, ?, ?)
                    ''',
                    (
                        processor,
                        timestamp,
                        json.dumps(features),
                        json.dumps(metadata) if metadata else None
                    )
                )
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error storing processed data: {e}")
            raise
            
    async def retrieve(
        self,
        query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve data matching query.
        
        Args:
            query: Query parameters:
                - start_time: Start of time range
                - end_time: End of time range
                - collector: Optional collector filter
                - processor: Optional processor filter
                - compressed: Whether to include compressed data
                
        Returns:
            List of matching data records
        """
        try:
            conditions = ['1=1']  # Always true condition to start
            params = []
            
            # Add time range conditions
            if 'start_time' in query:
                conditions.append('timestamp >= ?')
                params.append(query['start_time'])
            if 'end_time' in query:
                conditions.append('timestamp <= ?')
                params.append(query['end_time'])
                
            # Add collector/processor filter
            if 'collector' in query:
                conditions.append('collector = ?')
                params.append(query['collector'])
                
            # Build query
            sql = f'''
                SELECT * FROM raw_data 
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp DESC
            '''
            
            # Execute query
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                
            # Parse results
            results = []
            for row in rows:
                try:
                    data = json.loads(row[3])  # data column
                    results.append(data)
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse data for row {row[0]}")
                    
            return results
            
        except Exception as e:
            self.logger.error(f"Error retrieving data: {e}")
            return []
            
    async def retrieve_features(
        self,
        start_time: str,
        end_time: str,
        processor: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve processed features.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            processor: Optional processor filter
            
        Returns:
            List of feature records
        """
        try:
            conditions = ['timestamp >= ? AND timestamp <= ?']
            params = [start_time, end_time]
            
            if processor:
                conditions.append('processor = ?')
                params.append(processor)
                
            sql = f'''
                SELECT * FROM processed_data 
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp ASC
            '''
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                
            results = []
            for row in rows:
                try:
                    features = json.loads(row[3])  # features column
                    metadata = json.loads(row[4]) if row[4] else None  # metadata column
                    results.append({
                        'timestamp': row[2],
                        'features': features,
                        'metadata': metadata
                    })
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse features for row {row[0]}")
                    
            return results
            
        except Exception as e:
            self.logger.error(f"Error retrieving features: {e}")
            return []
            
    async def cleanup(self):
        """Clean up old data based on retention policy."""
        try:
            cutoff = (
                datetime.utcnow() - timedelta(days=self.retention_days)
            ).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Delete old raw data
                conn.execute(
                    'DELETE FROM raw_data WHERE timestamp < ?',
                    (cutoff,)
                )
                
                # Delete old processed data
                conn.execute(
                    'DELETE FROM processed_data WHERE timestamp < ?',
                    (cutoff,)
                )
                
                # Vacuum database to reclaim space
                conn.execute('VACUUM')
                conn.commit()
                
            self.logger.info(f"Cleaned up data older than {cutoff}")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            raise