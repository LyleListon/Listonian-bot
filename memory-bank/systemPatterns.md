# System Design Patterns

## Async Component Pattern
This pattern is used for components that require asynchronous initialization and operations.

### Structure
```python
class AsyncComponent:
    def __init__(self, config):
        # Synchronous initialization
        self.config = config
        self._setup_basic_attributes()

    async def initialize(self):
        # Async initialization
        await self._setup_async_resources()
        return True

    @classmethod
    async def create(cls, config):
        # Factory method
        instance = cls(config)
        await instance.initialize()
        return instance
```

### Usage
- Web3Manager
- WalletManager
- FlashbotsProvider
- DexManager

## Provider Pattern
Used for managing external service connections with proper async handling.

### Structure
```python
class AsyncProvider:
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self._connection = None
        self._lock = AsyncLock()

    async def connect(self):
        async with self._lock:
            if not self._connection:
                self._connection = await self._establish_connection()

    async def request(self, method, params):
        await self.connect()
        return await self._make_request(method, params)
```

### Usage
- CustomAsyncProvider
- AlchemyProvider
- FlashbotsProvider

## Resource Management Pattern
Ensures proper cleanup of resources in async context.

### Structure
```python
class ManagedResource:
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()

    async def initialize(self):
        # Setup resources
        pass

    async def cleanup(self):
        # Cleanup resources
        pass
```

### Usage
- Connection pools
- Cache managers
- Event subscriptions

## Event Loop Management Pattern
Handles event loop creation and cleanup for async operations.

### Structure
```python
def manage_event_loop(func):
    async def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        try:
            return await func(*args, **kwargs)
        finally:
            if not loop.is_running():
                loop.close()
    return wrapper
```

### Usage
- CustomAsyncProvider
- Web3Manager
- Event handlers

## Retry Pattern
Implements retry logic for async operations with exponential backoff.

### Structure
```python
def with_retry(retries=3, delay=1.0):
    async def decorator(func):
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < retries - 1:
                        await asyncio.sleep(delay * (2 ** attempt))
            raise last_error
        return wrapper
    return decorator
```

### Usage
- Web3 requests
- API calls
- Network operations

## Cache Pattern
Implements TTL-based caching for async operations.

### Structure
```python
class AsyncCache:
    def __init__(self, ttl):
        self._cache = {}
        self._ttl = ttl
        self._lock = AsyncLock()

    async def get_or_set(self, key, getter):
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    return value
            value = await getter()
            self._cache[key] = (value, time.time())
            return value
```

### Usage
- Price data
- Gas estimates
- Contract state

## Factory Pattern
Creates and initializes async components.

### Structure
```python
class AsyncFactory:
    @classmethod
    async def create_component(cls, config):
        # Create instance
        instance = cls._create_instance(config)
        # Initialize async resources
        await instance.initialize()
        return instance

    @classmethod
    def _create_instance(cls, config):
        # Create basic instance
        return cls(config)
```

### Usage
- Web3Manager creation
- DexManager creation
- Provider initialization

## Observer Pattern
Implements async event handling and notifications.

### Structure
```python
class AsyncObserver:
    def __init__(self):
        self._handlers = set()

    async def subscribe(self, handler):
        self._handlers.add(handler)

    async def unsubscribe(self, handler):
        self._handlers.remove(handler)

    async def notify(self, event):
        for handler in self._handlers:
            await handler(event)
```

### Usage
- Price updates
- Block notifications
- Transaction events

## Lock Pattern
Manages concurrent access to shared resources.

### Structure
```python
class AsyncResourceManager:
    def __init__(self):
        self._lock = AsyncLock()
        self._resource = None

    async def get_resource(self):
        async with self._lock:
            if not self._resource:
                self._resource = await self._create_resource()
            return self._resource
```

### Usage
- Connection pools
- Shared state
- Resource initialization
