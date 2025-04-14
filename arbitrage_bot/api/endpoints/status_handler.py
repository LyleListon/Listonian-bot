"""Status endpoint handler."""

import logging
import platform
import time
from typing import Dict, Any

from arbitrage_bot.api.endpoints.base_handler import BaseHandler
from arbitrage_bot.api.models.response import StatusResponse

logger = logging.getLogger(__name__)


class StatusHandler(BaseHandler):
    """Handler for status endpoint."""
    
    def get_status(self) -> StatusResponse:
        """Get system status.
        
        Returns:
            Status response.
        """
        # Get bot metrics
        metrics = self.bot.get_metrics()
        
        # Get component statuses
        components = {
            "market_monitor": "running" if self.bot.running else "stopped",
            "arbitrage_engine": "running" if self.bot.running else "stopped",
            "transaction_manager": "running" if self.bot.running else "stopped",
        }
        
        # Add blockchain connector statuses
        for name, connector in self.bot.blockchain_connectors.items():
            components[f"blockchain_{name}"] = "connected" if connector.is_connected() else "disconnected"
        
        # Create status response
        status_response = StatusResponse(
            status=metrics.get("status", "unknown"),
            version="0.1.0",  # TODO: Get from version file
            uptime=metrics.get("uptime", 0),
            components=components,
        )
        
        return status_response
