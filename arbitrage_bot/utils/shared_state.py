"""
Shared State Management Module

Provides a simple mechanism for sharing state across different components
of the arbitrage trading system.
"""

from typing import List, Dict, Any


class SharedState:
    def __init__(self):
        """
        Initialize the shared state with empty opportunities list
        """
        self._opportunities = []

    def update_opportunities(self, opportunities: List[Dict[str, Any]]):
        """
        Update the list of current arbitrage opportunities

        Args:
            opportunities (List[Dict[str, Any]]): List of detected arbitrage opportunities
        """
        self._opportunities = opportunities

    def get_opportunities(self) -> List[Dict[str, Any]]:
        """
        Retrieve the current list of arbitrage opportunities

        Returns:
            List[Dict[str, Any]]: Current list of opportunities
        """
        return self._opportunities.copy()

    def clear_opportunities(self):
        """
        Clear all current opportunities
        """
        self._opportunities = []
