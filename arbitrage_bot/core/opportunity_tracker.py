"""
Opportunity Tracker

Tracks and manages arbitrage opportunities and their execution status.
"""

import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import deque

logger = logging.getLogger(__name__)

class OpportunityTracker:
    """
    Tracks arbitrage opportunities and their execution status.
    Thread-safe storage and retrieval of opportunity data.
    """
    
    def __init__(self, max_entries: int = 5000):
        """
        Initialize the opportunity tracker.
        
        Args:
            max_entries: Maximum number of opportunities to store
        """
        self.opportunities = deque(maxlen=max_entries)
        self.lock = threading.Lock()
        self.stats: Dict[str, Any] = {
            'total_opportunities': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_profit': 0.0,
            'last_update': None
        }
        
    def add_opportunity(self, data: Dict[str, Any]) -> None:
        """
        Add a new opportunity to the tracker.
        
        Args:
            data: Dictionary containing opportunity details:
                - timestamp: Time of detection (ISO format string)
                - source_dex: Source DEX name
                - target_dex: Target DEX name
                - token: Token symbol or address
                - amount: Trade amount
                - profit_usd: Expected profit in USD
                - gas_cost_usd: Estimated gas cost in USD (optional)
                - net_profit_usd: Net profit after gas (optional)
                - executed: Whether the opportunity was executed (optional)
                - tx_hash: Transaction hash if executed (optional)
        """
        with self.lock:
            # Ensure required fields
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
                
            # Calculate net profit if not provided
            if 'net_profit_usd' not in data and 'profit_usd' in data:
                gas_cost = data.get('gas_cost_usd', 0)
                data['net_profit_usd'] = data['profit_usd'] - gas_cost
                
            # Update statistics
            self.stats['total_opportunities'] += 1
            if data.get('executed', False):
                if data.get('status', '').lower() == 'success':
                    self.stats['successful_executions'] += 1
                    self.stats['total_profit'] += data.get('net_profit_usd', 0)
                else:
                    self.stats['failed_executions'] += 1
                    
            self.stats['last_update'] = datetime.now().isoformat()
            
            # Add to deque
            self.opportunities.appendleft(data)
            
            # Log the addition
            logger.debug(
                f"Added opportunity: {data.get('source_dex')} -> {data.get('target_dex')}, "
                f"Profit: ${data.get('net_profit_usd', 0):.2f}"
            )
            
    def get_opportunities(
        self,
        limit: int = 100,
        min_profit: Optional[float] = None,
        pair: Optional[str] = None,
        dex: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent opportunities with optional filtering.
        
        Args:
            limit: Maximum number of opportunities to return
            min_profit: Minimum net profit in USD
            pair: Filter by trading pair
            dex: Filter by DEX name (source or target)
            
        Returns:
            List of opportunity dictionaries
        """
        with self.lock:
            # Convert deque to list for filtering
            opps = list(self.opportunities)
            
        # Apply filters
        if min_profit is not None:
            opps = [o for o in opps if o.get('net_profit_usd', 0) >= min_profit]
            
        if pair is not None:
            opps = [o for o in opps if o.get('pair') == pair]
            
        if dex is not None:
            opps = [
                o for o in opps 
                if dex in (o.get('source_dex', ''), o.get('target_dex', ''))
            ]
            
        # Return limited number of opportunities
        return opps[:limit]
        
    def get_profitable_opportunities(
        self,
        min_profit: float = 0.0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get profitable opportunities.
        
        Args:
            min_profit: Minimum net profit in USD
            limit: Maximum number of opportunities to return
            
        Returns:
            List of profitable opportunity dictionaries
        """
        return self.get_opportunities(limit=limit, min_profit=min_profit)
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about tracked opportunities.
        
        Returns:
            Dictionary with statistics:
                - total_opportunities: Total number of opportunities tracked
                - successful_executions: Number of successful executions
                - failed_executions: Number of failed executions
                - total_profit: Total profit from successful executions
                - success_rate: Percentage of successful executions
                - avg_profit: Average profit per successful execution
                - last_update: Timestamp of last update
        """
        with self.lock:
            stats = self.stats.copy()
            
            # Calculate additional metrics
            total_executions = (
                stats['successful_executions'] + stats['failed_executions']
            )
            if total_executions > 0:
                stats['success_rate'] = (
                    stats['successful_executions'] / total_executions
                )
            else:
                stats['success_rate'] = 0.0
                
            if stats['successful_executions'] > 0:
                stats['avg_profit'] = (
                    stats['total_profit'] / stats['successful_executions']
                )
            else:
                stats['avg_profit'] = 0.0
                
            return stats
            
    def clear(self) -> None:
        """Clear all stored opportunities and reset statistics."""
        with self.lock:
            self.opportunities.clear()
            self.stats = {
                'total_opportunities': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'total_profit': 0.0,
                'last_update': datetime.now().isoformat()
            }
            logger.info("Cleared all opportunities and reset statistics")