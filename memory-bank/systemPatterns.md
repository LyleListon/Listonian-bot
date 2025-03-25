# System Patterns - Dashboard Implementation

## Core Patterns

### 1. Service Pattern
```python
class BaseService:
    """Base class for all services implementing initialization pattern."""
    
    def __init__(self):
        self._initialized = False
        self._lock = asyncio.Lock()
        self._subscribers = set()

    async def initialize(self):
        """Initialize service with proper locking."""
        async with self._lock:
            if not self._initialized:
                await self._do_initialize()
                self._initialized = True

    async def shutdown(self):
        """Clean shutdown with resource cleanup."""
        async with self._lock:
            if self._initialized:
                await self._do_shutdown()
                self._initialized = False
```

### 2. Resource Management Pattern
```python
class ResourceManager:
    """Manage resources with proper cleanup."""
    
    def __init__(self):
        self._resources = WeakKeyDictionary()
        self._lock = asyncio.Lock()

    async def acquire(self, key):
        """Acquire resource with tracking."""
        async with self._lock:
            resource = await self._create_resource()
            self._resources[key] = resource
            return resource

    async def release(self, key):
        """Release resource with cleanup."""
        async with self._lock:
            if key in self._resources:
                await self._cleanup_resource(self._resources[key])
                del self._resources[key]
```

### 3. Connection Management Pattern
```python
@asynccontextmanager
async def managed_connection():
    """Context manager for connection lifecycle."""
    try:
        connection = await establish_connection()
        yield connection
    finally:
        await cleanup_connection(connection)
```

## Design Patterns

### 1. Observer Pattern
```python
class MetricsPublisher:
    """Publish metrics to subscribers."""
    
    def __init__(self):
        self._subscribers = set()
        self._lock = asyncio.Lock()

    async def subscribe(self, subscriber):
        """Add subscriber with thread safety."""
        async with self._lock:
            self._subscribers.add(subscriber)

    async def unsubscribe(self, subscriber):
        """Remove subscriber with thread safety."""
        async with self._lock:
            self._subscribers.discard(subscriber)

    async def publish(self, metrics):
        """Publish updates to all subscribers."""
        async with self._lock:
            tasks = [sub.update(metrics) for sub in self._subscribers]
            await asyncio.gather(*tasks, return_exceptions=True)
```

### 2. State Machine Pattern
```python
class ConnectionState:
    """Connection state management."""
    
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"

    def __init__(self):
        self._state = self.DISCONNECTED
        self._lock = asyncio.Lock()

    async def transition_to(self, new_state):
        """Thread-safe state transition."""
        async with self._lock:
            if self._is_valid_transition(new_state):
                self._state = new_state
```

### 3. Factory Pattern
```python
class ServiceFactory:
    """Create services with proper initialization."""
    
    @classmethod
    async def create_service(cls, service_type):
        """Create and initialize service."""
        service = service_type()
        await service.initialize()
        return service
```

## Error Handling Patterns

### 1. Retry Pattern
```python
async def with_retry(func, max_retries=3, delay=1.0):
    """Execute with retry logic."""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(delay * (attempt + 1))
```

### 2. Circuit Breaker Pattern
```python
class CircuitBreaker:
    """Prevent repeated failures."""
    
    def __init__(self, failure_threshold=5, reset_timeout=60):
        self._failures = 0
        self._threshold = failure_threshold
        self._timeout = reset_timeout
        self._state = "closed"
        self._last_failure = 0

    async def call(self, func):
        """Execute with circuit breaker logic."""
        if self._state == "open":
            if time.time() - self._last_failure > self._timeout:
                self._state = "half-open"
            else:
                raise CircuitBreakerOpen()

        try:
            result = await func()
            if self._state == "half-open":
                self._state = "closed"
            return result
        except Exception as e:
            self._handle_failure()
            raise
```

## Resource Management Patterns

### 1. Connection Pool Pattern
```python
class ConnectionPool:
    """Manage connection pooling."""
    
    def __init__(self, max_size=10):
        self._pool = asyncio.Queue(max_size)
        self._size = 0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Get connection from pool."""
        async with self._lock:
            if self._pool.empty() and self._size < self._pool.maxsize:
                connection = await self._create_connection()
                self._size += 1
                return connection
            return await self._pool.get()

    async def release(self, connection):
        """Return connection to pool."""
        await self._pool.put(connection)
```

### 2. Resource Cleanup Pattern
```python
class ManagedResource:
    """Resource with automatic cleanup."""
    
    def __init__(self):
        self._resources = set()
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        """Acquire resources."""
        self._resource = await self._acquire_resource()
        async with self._lock:
            self._resources.add(self._resource)
        return self._resource

    async def __aexit__(self, exc_type, exc, tb):
        """Clean up resources."""
        async with self._lock:
            if self._resource in self._resources:
                await self._cleanup_resource(self._resource)
                self._resources.remove(self._resource)
```

## Performance Patterns

### 1. Caching Pattern
```python
class MetricsCache:
    """Cache metrics with TTL."""
    
    def __init__(self, ttl=60):
        self._cache = {}
        self._ttl = ttl
        self._lock = asyncio.Lock()

    async def get(self, key):
        """Get cached value with TTL check."""
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp <= self._ttl:
                    return value
            return None

    async def set(self, key, value):
        """Cache value with timestamp."""
        async with self._lock:
            self._cache[key] = (value, time.time())
```

### 2. Batch Processing Pattern
```python
class BatchProcessor:
    """Process updates in batches."""
    
    def __init__(self, batch_size=100, timeout=1.0):
        self._batch = []
        self._size = batch_size
        self._timeout = timeout
        self._lock = asyncio.Lock()

    async def add(self, item):
        """Add item to batch."""
        async with self._lock:
            self._batch.append(item)
            if len(self._batch) >= self._size:
                await self._process_batch()

    async def _process_batch(self):
        """Process current batch."""
        if self._batch:
            batch = self._batch
            self._batch = []
            await self._do_process(batch)
```

## Testing Patterns

### 1. Fixture Pattern
```python
@pytest.fixture
async def metrics_service():
    """Provide initialized metrics service."""
    service = MetricsService()
    await service.initialize()
    yield service
    await service.shutdown()
```

### 2. Mock Pattern
```python
class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.closed = False

    async def send_json(self, data):
        """Record sent messages."""
        self.sent_messages.append(data)

    async def close(self):
        """Mark as closed."""
        self.closed = True
```

## Usage Guidelines

1. Always use async/await consistently
2. Implement proper resource cleanup
3. Handle all error cases
4. Use appropriate locking
5. Follow established patterns
6. Document all implementations
7. Add comprehensive logging
8. Test thoroughly