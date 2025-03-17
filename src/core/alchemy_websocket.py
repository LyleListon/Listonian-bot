"""
WebSocket client implementation for Alchemy SDK with async support.
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from asyncio import Lock, Task
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed

from .alchemy_config import WebSocketConfig, AlchemySettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Subscription:
    """WebSocket subscription details."""
    id: str
    method: str
    params: List[Any]
    callback: Callable

class AlchemyWebSocket:
    """
    Async WebSocket client for Alchemy with automatic reconnection and subscription management.
    
    Features:
    - Async WebSocket connection management
    - Automatic reconnection with backoff
    - Subscription tracking and recovery
    - Thread-safe operations
    - Proper resource cleanup
    """
    
    def __init__(self, settings: AlchemySettings):
        """Initialize the WebSocket client."""
        self.settings = settings
        self.ws_config = settings.websocket
        self._ws: Optional[WebSocketClientProtocol] = None
        self._lock = Lock()
        self._subscriptions: Dict[str, Subscription] = {}
        self._connected = asyncio.Event()
        self._stop_event = asyncio.Event()
        self._tasks: List[Task] = []
        self._subscription_id = 0
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        
    async def connect(self):
        """Establish WebSocket connection with retry logic."""
        async with self._lock:
            if self._ws is not None:
                return
                
            for attempt in range(self.ws_config.reconnect_attempts):
                try:
                    self._ws = await websockets.connect(
                        self.settings.ws_url,
                        ping_interval=self.ws_config.heartbeat_interval,
                        ping_timeout=self.ws_config.ping_timeout,
                        close_timeout=self.ws_config.timeout
                    )
                    
                    # Start message handler and heartbeat
                    self._tasks.append(asyncio.create_task(self._handle_messages()))
                    self._tasks.append(asyncio.create_task(self._monitor_connection()))
                    
                    self._connected.set()
                    logger.info("WebSocket connection established")
                    
                    # Restore subscriptions if any
                    await self._restore_subscriptions()
                    return
                    
                except Exception as e:
                    logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                    if attempt < self.ws_config.reconnect_attempts - 1:
                        await asyncio.sleep(self.ws_config.reconnect_interval * (attempt + 1))
                    else:
                        raise
                        
    async def _restore_subscriptions(self):
        """Restore existing subscriptions after reconnection."""
        for sub in self._subscriptions.values():
            try:
                await self._send_subscription(sub.method, sub.params)
            except Exception as e:
                logger.error(f"Failed to restore subscription {sub.id}: {e}")
                
    async def _handle_messages(self):
        """Handle incoming WebSocket messages."""
        while not self._stop_event.is_set():
            try:
                if self._ws is None:
                    await asyncio.sleep(1)
                    continue
                    
                message = await self._ws.recv()
                data = json.loads(message)
                
                # Handle subscription messages
                if "method" in data and data["method"] == "eth_subscription":
                    subscription_id = data["params"]["subscription"]
                    if subscription_id in self._subscriptions:
                        subscription = self._subscriptions[subscription_id]
                        await self._handle_subscription_message(subscription, data["params"]["result"])
                        
            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self._connected.clear()
                await self._attempt_reconnect()
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await asyncio.sleep(1)
                
    async def _handle_subscription_message(self, subscription: Subscription, data: Any):
        """Handle subscription message with proper error handling."""
        try:
            await subscription.callback(data)
        except Exception as e:
            logger.error(f"Error in subscription callback: {e}")
            
    async def _monitor_connection(self):
        """Monitor WebSocket connection and handle reconnection."""
        while not self._stop_event.is_set():
            try:
                if self._ws is None or not self._connected.is_set():
                    await self._attempt_reconnect()
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")
                await asyncio.sleep(1)
                
    async def _attempt_reconnect(self):
        """Attempt to reconnect with backoff."""
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
            
        try:
            await self.connect()
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            
    async def _send_subscription(self, method: str, params: List[Any]) -> str:
        """Send subscription request."""
        if self._ws is None:
            raise RuntimeError("WebSocket not connected")
            
        self._subscription_id += 1
        subscription_id = str(self._subscription_id)
        
        message = {
            "jsonrpc": "2.0",
            "id": subscription_id,
            "method": method,
            "params": params
        }
        
        await self._ws.send(json.dumps(message))
        return subscription_id
        
    async def subscribe(self, method: str, params: List[Any], callback: Callable) -> str:
        """Subscribe to events."""
        async with self._lock:
            subscription_id = await self._send_subscription(method, params)
            
            self._subscriptions[subscription_id] = Subscription(
                id=subscription_id,
                method=method,
                params=params,
                callback=callback
            )
            
            logger.info(f"Subscribed to {method} with ID {subscription_id}")
            return subscription_id
            
    async def unsubscribe(self, subscription_id: str):
        """Unsubscribe from events."""
        async with self._lock:
            if subscription_id in self._subscriptions:
                if self._ws is not None:
                    message = {
                        "jsonrpc": "2.0",
                        "id": subscription_id,
                        "method": "eth_unsubscribe",
                        "params": [subscription_id]
                    }
                    await self._ws.send(json.dumps(message))
                    
                del self._subscriptions[subscription_id]
                logger.info(f"Unsubscribed from {subscription_id}")
                
    async def disconnect(self):
        """Disconnect and cleanup resources."""
        self._stop_event.set()
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
            
        try:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error during task cleanup: {e}")
            
        # Close WebSocket connection
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
            
        self._connected.clear()
        self._subscriptions.clear()
        logger.info("WebSocket disconnected and cleaned up")

# Example usage:
async def main():
    settings = AlchemySettings(
        api_key="kRXhWVt8YU_8LnGS20145F5uBDFbL_k0"
    )
    
    async def handle_new_heads(data):
        print(f"New block: {data}")
    
    async with AlchemyWebSocket(settings) as ws:
        # Subscribe to new block headers
        await ws.subscribe(
            "eth_subscribe",
            ["newHeads"],
            handle_new_heads
        )
        
        # Wait for some time
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())