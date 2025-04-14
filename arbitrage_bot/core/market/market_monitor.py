"""Market monitor for collecting and processing market data."""

import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable

from arbitrage_bot.common.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class MarketMonitor:
    """Monitors market data from various sources."""
    
    def __init__(
        self,
        event_bus: EventBus,
        config: Dict[str, Any],
    ):
        """Initialize the market monitor.
        
        Args:
            event_bus: Event bus for publishing events.
            config: Configuration dictionary.
        """
        self.event_bus = event_bus
        self.config = config
        
        # Initialize state
        self.running = False
        self.market_data = {"pairs": []}
        self.token_prices = {}
        self.token_info = {}
        self.dex_connectors = []
        self.update_interval = 10  # seconds
        self.update_thread = None
        self.last_update_time = 0
        
        logger.info("Market monitor initialized")
    
    def add_dex_connector(self, connector: Any) -> None:
        """Add a DEX connector.
        
        Args:
            connector: DEX connector instance.
        """
        self.dex_connectors.append(connector)
        logger.info(f"Added DEX connector: {connector.__class__.__name__}")
    
    def start(self) -> None:
        """Start the market monitor."""
        if self.running:
            logger.warning("Market monitor already running")
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        logger.info("Market monitor started")
    
    def stop(self) -> None:
        """Stop the market monitor."""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5.0)
            self.update_thread = None
        
        logger.info("Market monitor stopped")
    
    def _update_loop(self) -> None:
        """Update loop for periodically fetching market data."""
        while self.running:
            try:
                self.update_market_data()
                self.last_update_time = time.time()
            except Exception as e:
                logger.error(f"Error updating market data: {e}")
            
            # Sleep until next update
            time.sleep(self.update_interval)
    
    def update_market_data(self) -> None:
        """Update market data from all sources."""
        logger.debug("Updating market data")
        
        # Initialize new market data
        new_market_data = {"pairs": []}
        new_token_prices = {}
        new_token_info = {}
        
        # Collect data from all DEX connectors
        for connector in self.dex_connectors:
            try:
                # Get pairs from connector
                pairs = connector.get_pairs()
                new_market_data["pairs"].extend(pairs)
                
                # Get token prices from connector
                prices = connector.get_token_prices()
                new_token_prices.update(prices)
                
                # Get token info from connector
                info = connector.get_token_info()
                new_token_info.update(info)
            except Exception as e:
                logger.error(f"Error collecting data from {connector.__class__.__name__}: {e}")
        
        # Update state
        self.market_data = new_market_data
        self.token_prices = new_token_prices
        self.token_info = new_token_info
        
        # Publish market data updated event
        self.event_bus.publish_event(
            "market_data_updated",
            {
                "market_data": self.market_data,
                "token_prices": self.token_prices,
                "token_info": self.token_info,
                "timestamp": time.time(),
            },
        )
        
        logger.debug(
            f"Market data updated: {len(self.market_data['pairs'])} pairs, "
            f"{len(self.token_prices)} token prices, {len(self.token_info)} token info"
        )
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get the current market data.
        
        Returns:
            Current market data.
        """
        return self.market_data
    
    def get_token_prices(self) -> Dict[str, float]:
        """Get the current token prices.
        
        Returns:
            Current token prices.
        """
        return self.token_prices
    
    def get_token_info(self) -> Dict[str, Dict[str, Any]]:
        """Get the current token information.
        
        Returns:
            Current token information.
        """
        return self.token_info
    
    def get_pair(self, base_token: str, quote_token: str, dex: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a specific trading pair.
        
        Args:
            base_token: Base token symbol or address.
            quote_token: Quote token symbol or address.
            dex: Optional DEX name to filter by.
            
        Returns:
            Trading pair information, or None if not found.
        """
        for pair in self.market_data.get("pairs", []):
            if pair.get("base_token") == base_token and pair.get("quote_token") == quote_token:
                if dex is None or pair.get("dex") == dex:
                    return pair
        
        return None
    
    def get_token_price(self, token: str) -> Optional[float]:
        """Get the price of a specific token.
        
        Args:
            token: Token symbol or address.
            
        Returns:
            Token price in USD, or None if not found.
        """
        return self.token_prices.get(token)
    
    def get_token_pairs(self, token: str) -> List[Dict[str, Any]]:
        """Get all trading pairs involving a specific token.
        
        Args:
            token: Token symbol or address.
            
        Returns:
            List of trading pairs.
        """
        pairs = []
        
        for pair in self.market_data.get("pairs", []):
            if pair.get("base_token") == token or pair.get("quote_token") == token:
                pairs.append(pair)
        
        return pairs
