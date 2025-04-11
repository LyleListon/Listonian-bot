"""
WebSocket Optimization for Better Performance

This module provides optimizations for WebSocket communication:
- Binary message format using MessagePack
- Intelligent message batching
- Connection optimization
"""

import asyncio
import logging
import time
import json
import zlib
import msgpack
import websockets
from typing import Dict, Any, Optional, List, Tuple, Union, Callable, Awaitable # Removed Set
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


class MessagePriority(int, Enum):
    """Priority levels for messages."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class Message:
    """WebSocket message with metadata."""

    data: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: f"{time.time():.6f}")
    compress: bool = False
    binary: bool = True
    schema_version: int = 1


class MessageFormat(str, Enum):
    """Message serialization formats."""

    JSON = "json"
    MSGPACK = "msgpack"
    MSGPACK_COMPRESSED = "msgpack_compressed"


class OptimizedWebSocketClient:
    """
    Optimized WebSocket client with improved performance.

    This class provides:
    - Binary message format using MessagePack
    - Message compression for large payloads
    - Intelligent message batching
    - Connection pooling and quality monitoring
    """

    def __init__(
        self,
        url: str,
        format: MessageFormat = MessageFormat.MSGPACK,
        batch_size: int = 10,
        batch_interval: float = 0.1,
        compression_threshold: int = 1024,
        max_queue_size: int = 1000,
        reconnect_interval: float = 1.0,
        max_reconnect_interval: float = 30.0,
        connection_timeout: float = 10.0,
    ):
        """
        Initialize the optimized WebSocket client.

        Args:
            url: WebSocket server URL
            format: Message serialization format
            batch_size: Maximum number of messages in a batch
            batch_interval: Maximum time to wait before sending a batch (seconds)
            compression_threshold: Minimum message size for compression (bytes)
            max_queue_size: Maximum number of messages in the queue
            reconnect_interval: Initial reconnect interval (seconds)
            max_reconnect_interval: Maximum reconnect interval (seconds)
            connection_timeout: Connection timeout (seconds)
        """
        self.url = url
        self.format = format
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.compression_threshold = compression_threshold
        self.max_queue_size = max_queue_size
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_interval = max_reconnect_interval
        self.connection_timeout = connection_timeout

        # Connection state
        self._connection: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._connecting = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._current_reconnect_interval = reconnect_interval

        # Message queue
        self._queue: deque[Message] = deque()
        self._queue_lock = asyncio.Lock()
        self._batch_task: Optional[asyncio.Task] = None
        self._last_batch_time = 0.0

        # Connection quality metrics
        self._sent_messages = 0
        self._received_messages = 0
        self._connection_errors = 0
        self._last_latency = 0.0
        self._avg_latency = 0.0
        self._latency_samples: deque[float] = deque(maxlen=100)

        # Message handlers
        self._message_handlers: Dict[
            str, Callable[[Dict[str, Any]], Awaitable[None]]
        ] = {}

        logger.debug(f"OptimizedWebSocketClient initialized with URL: {url}")

    async def connect(self) -> bool:
        """
        Connect to the WebSocket server.

        Returns:
            True if connected successfully, False otherwise
        """
        if self._connected:
            return True

        if self._connecting:
            # Wait for the connection to complete
            while self._connecting:
                await asyncio.sleep(0.1)
            return self._connected

        self._connecting = True

        try:
            logger.debug(f"Connecting to WebSocket server: {self.url}")
            self._connection = await asyncio.wait_for(
                websockets.connect(self.url), timeout=self.connection_timeout
            )

            self._connected = True
            self._connecting = False
            self._current_reconnect_interval = self.reconnect_interval

            # Start message processing
            self._batch_task = asyncio.create_task(self._process_queue())

            # Start message receiving
            asyncio.create_task(self._receive_messages())

            logger.info(f"Connected to WebSocket server: {self.url}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket server: {e}")
            self._connected = False
            self._connecting = False
            self._connection_errors += 1

            # Schedule reconnection
            if not self._reconnect_task or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnect())

            return False

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        if not self._connected:
            return

        logger.debug("Disconnecting from WebSocket server")

        # Cancel batch task
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass

        # Cancel reconnect task
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        # Close connection
        if self._connection:
            try:
                await self._connection.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket connection: {e}")

        self._connected = False
        logger.info("Disconnected from WebSocket server")

    async def send(
        self, data: Dict[str, Any], priority: MessagePriority = MessagePriority.NORMAL
    ) -> bool:
        """
        Send a message to the WebSocket server.

        Args:
            data: Message data
            priority: Message priority

        Returns:
            True if the message was queued successfully, False otherwise
        """
        # Create message
        message = Message(
            data=data,
            priority=priority,
            compress=self._should_compress(data),
            binary=self.format != MessageFormat.JSON,
        )

        # Add to queue
        async with self._queue_lock:
            if len(self._queue) >= self.max_queue_size:
                # Remove lowest priority message if queue is full
                if priority == MessagePriority.BACKGROUND:
                    logger.warning("Queue full, dropping background message")
                    return False

                # Find lowest priority message to remove
                lowest_priority = min(self._queue, key=lambda m: m.priority)
                if lowest_priority.priority > priority:
                    logger.warning(
                        f"Queue full, dropping message with priority {lowest_priority.priority}"
                    )
                    self._queue.remove(lowest_priority)
                else:
                    logger.warning(
                        f"Queue full, dropping new message with priority {priority}"
                    )
                    return False

            self._queue.append(message)

        # Connect if not connected
        if not self._connected and not self._connecting:
            asyncio.create_task(self.connect())

        return True

    async def register_handler(
        self, message_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Register a message handler.

        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        self._message_handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")

    async def _reconnect(self) -> None:
        """Reconnect to the WebSocket server with exponential backoff."""
        while not self._connected:
            logger.info(
                f"Reconnecting in {self._current_reconnect_interval:.1f} seconds"
            )
            await asyncio.sleep(self._current_reconnect_interval)

            # Exponential backoff
            self._current_reconnect_interval = min(
                self._current_reconnect_interval * 1.5, self.max_reconnect_interval
            )

            # Try to connect
            await self.connect()

    async def _process_queue(self) -> None:
        """Process the message queue."""
        while self._connected:
            try:
                # Check if we have messages to send
                if not self._queue:
                    await asyncio.sleep(0.01)
                    continue

                # Check if we should send a batch
                now = time.time()
                time_since_last_batch = now - self._last_batch_time
                should_send_batch = len(self._queue) >= self.batch_size or (
                    self._queue and time_since_last_batch >= self.batch_interval
                )

                if should_send_batch:
                    await self._send_batch()
                else:
                    await asyncio.sleep(0.01)

            except asyncio.CancelledError:
                logger.debug("Message processing cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
                await asyncio.sleep(0.1)

    async def _send_batch(self) -> None:
        """Send a batch of messages."""
        if not self._connected or not self._connection:
            return

        # Get batch of messages
        batch = []
        async with self._queue_lock:
            # Sort by priority
            sorted_queue = sorted(self._queue, key=lambda m: m.priority)

            # Take up to batch_size messages
            batch = sorted_queue[: self.batch_size]

            # Remove from queue
            for message in batch:
                self._queue.remove(message)

        if not batch:
            return

        # Prepare batch data
        batch_data = {
            "batch": True,
            "messages": [msg.data for msg in batch],
            "count": len(batch),
            "timestamp": time.time(),
        }

        # Serialize and send
        try:
            serialized_data = self._serialize(
                batch_data, any(msg.compress for msg in batch)
            )
            await self._connection.send(serialized_data)
            self._sent_messages += len(batch)
            self._last_batch_time = time.time()
            logger.debug(f"Sent batch of {len(batch)} messages")
        except Exception as e:
            logger.error(f"Error sending batch: {e}")

            # Put messages back in queue
            async with self._queue_lock:
                for message in reversed(batch):
                    self._queue.appendleft(message)

            # Handle connection error
            self._connection_errors += 1
            self._connected = False

            # Schedule reconnection
            if not self._reconnect_task or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnect())

    async def _receive_messages(self) -> None:
        """Receive messages from the WebSocket server."""
        if not self._connected or not self._connection:
            return

        try:
            async for message in self._connection:
                try:
                    # Deserialize message
                    data = self._deserialize(message)
                    self._received_messages += 1

                    # Handle batch
                    if isinstance(data, dict) and data.get("batch"):
                        messages = data.get("messages", [])
                        logger.debug(f"Received batch of {len(messages)} messages")

                        # Process each message
                        for msg in messages:
                            await self._handle_message(msg)
                    else:
                        # Handle single message
                        await self._handle_message(data)

                except Exception as e:
                    logger.error(f"Error processing received message: {e}")

        except asyncio.CancelledError:
            logger.debug("Message receiving cancelled")
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
            self._connection_errors += 1
            self._connected = False

            # Schedule reconnection
            if not self._reconnect_task or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnect())

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """
        Handle a received message.

        Args:
            data: Message data
        """
        if not isinstance(data, dict):
            logger.warning(f"Received non-dict message: {data}")
            return

        # Extract message type
        message_type = data.get("type")
        if not message_type:
            logger.warning(f"Received message without type: {data}")
            return

        # Call handler
        handler = self._message_handlers.get(message_type)
        if handler:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Error in message handler for {message_type}: {e}")
        else:
            logger.debug(f"No handler for message type: {message_type}")

    def _serialize(
        self, data: Dict[str, Any], compress: bool = False
    ) -> Union[str, bytes]:
        """
        Serialize data for sending.

        Args:
            data: Data to serialize
            compress: Whether to compress the data

        Returns:
            Serialized data
        """
        if self.format == MessageFormat.JSON:
            serialized = json.dumps(data)
            return serialized
        elif (
            self.format == MessageFormat.MSGPACK
            or self.format == MessageFormat.MSGPACK_COMPRESSED
        ):
            serialized = msgpack.packb(data, use_bin_type=True)

            # Compress if needed
            if compress or self.format == MessageFormat.MSGPACK_COMPRESSED:
                if len(serialized) >= self.compression_threshold:
                    compressed = zlib.compress(serialized)

                    # Only use compression if it actually reduces size
                    if len(compressed) < len(serialized):
                        # Add compression header (0x01 = compressed)
                        return b"\x01" + compressed

            # No compression (0x00 = uncompressed)
            return b"\x00" + serialized

        raise ValueError(f"Unsupported format: {self.format}")

    def _deserialize(self, data: Union[str, bytes]) -> Dict[str, Any]:
        """
        Deserialize received data.

        Args:
            data: Data to deserialize

        Returns:
            Deserialized data
        """
        if isinstance(data, str):
            # JSON format
            return json.loads(data)
        elif isinstance(data, bytes):
            # Check compression header
            if data[0] == 0x01:
                # Compressed
                decompressed = zlib.decompress(data[1:])
                return msgpack.unpackb(decompressed, raw=False)
            elif data[0] == 0x00:
                # Uncompressed
                return msgpack.unpackb(data[1:], raw=False)
            else:
                # No header, assume uncompressed
                return msgpack.unpackb(data, raw=False)

        raise ValueError(f"Unsupported data type: {type(data)}")

    def _should_compress(self, data: Dict[str, Any]) -> bool:
        """
        Determine if a message should be compressed.

        Args:
            data: Message data

        Returns:
            True if the message should be compressed, False otherwise
        """
        # Quick size estimate
        size_estimate = len(json.dumps(data))
        return size_estimate >= self.compression_threshold

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics.

        Returns:
            Dictionary with connection statistics
        """
        return {
            "connected": self._connected,
            "connecting": self._connecting,
            "sent_messages": self._sent_messages,
            "received_messages": self._received_messages,
            "connection_errors": self._connection_errors,
            "queue_size": len(self._queue),
            "last_latency": self._last_latency,
            "avg_latency": self._avg_latency,
            "reconnect_interval": self._current_reconnect_interval,
        }


class WebSocketConnectionPool:
    """
    WebSocket connection pool for efficient connection management.

    This class provides:
    - Connection pooling
    - Connection quality monitoring
    - Automatic reconnection
    """

    def __init__(
        self,
        max_connections: int = 5,
        format: MessageFormat = MessageFormat.MSGPACK,
        batch_size: int = 10,
        batch_interval: float = 0.1,
        compression_threshold: int = 1024,
        max_queue_size: int = 1000,
        reconnect_interval: float = 1.0,
        max_reconnect_interval: float = 30.0,
        connection_timeout: float = 10.0,
    ):
        """
        Initialize the WebSocket connection pool.

        Args:
            max_connections: Maximum number of connections
            format: Message serialization format
            batch_size: Maximum number of messages in a batch
            batch_interval: Maximum time to wait before sending a batch (seconds)
            compression_threshold: Minimum message size for compression (bytes)
            max_queue_size: Maximum number of messages in the queue
            reconnect_interval: Initial reconnect interval (seconds)
            max_reconnect_interval: Maximum reconnect interval (seconds)
            connection_timeout: Connection timeout (seconds)
        """
        self.max_connections = max_connections
        self.format = format
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.compression_threshold = compression_threshold
        self.max_queue_size = max_queue_size
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_interval = max_reconnect_interval
        self.connection_timeout = connection_timeout

        # Connection pool
        self._connections: Dict[str, OptimizedWebSocketClient] = {}
        self._lock = asyncio.Lock()

        logger.debug(
            f"WebSocketConnectionPool initialized with max_connections={max_connections}"
        )

    async def get_connection(self, url: str) -> OptimizedWebSocketClient:
        """
        Get a connection from the pool.

        Args:
            url: WebSocket server URL

        Returns:
            WebSocket client
        """
        async with self._lock:
            # Check if connection exists
            if url in self._connections:
                return self._connections[url]

            # Check if pool is full
            if len(self._connections) >= self.max_connections:
                # Find least used connection to remove
                least_used = min(
                    self._connections.items(),
                    key=lambda x: x[1].get_connection_stats()["sent_messages"],
                )

                # Remove from pool
                await least_used[1].disconnect()
                del self._connections[least_used[0]]

            # Create new connection
            client = OptimizedWebSocketClient(
                url=url,
                format=self.format,
                batch_size=self.batch_size,
                batch_interval=self.batch_interval,
                compression_threshold=self.compression_threshold,
                max_queue_size=self.max_queue_size,
                reconnect_interval=self.reconnect_interval,
                max_reconnect_interval=self.max_reconnect_interval,
                connection_timeout=self.connection_timeout,
            )

            # Add to pool
            self._connections[url] = client

            return client

    async def connect_all(self) -> None:
        """Connect all connections in the pool."""
        for client in self._connections.values():
            await client.connect()

    async def disconnect_all(self) -> None:
        """Disconnect all connections in the pool."""
        for client in self._connections.values():
            await client.disconnect()

    async def send(
        self,
        url: str,
        data: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> bool:
        """
        Send a message to a WebSocket server.

        Args:
            url: WebSocket server URL
            data: Message data
            priority: Message priority

        Returns:
            True if the message was queued successfully, False otherwise
        """
        client = await self.get_connection(url)
        return await client.send(data, priority)

    async def register_handler(
        self,
        url: str,
        message_type: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> None:
        """
        Register a message handler.

        Args:
            url: WebSocket server URL
            message_type: Type of message to handle
            handler: Handler function
        """
        client = await self.get_connection(url)
        await client.register_handler(message_type, handler)

    def get_pool_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        stats = {
            "pool_size": len(self._connections),
            "max_connections": self.max_connections,
            "connections": {},
        }

        for url, client in self._connections.items():
            stats["connections"][url] = client.get_connection_stats()

        return stats
