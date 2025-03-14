# System Architecture Patterns

## Dashboard Architecture Patterns

### Component Patterns
1. WebSocket Communication
```python
class WebSocketServer:
    def __init__(self, app, components...):
        self.app = app
        self.clients = set()
        self.initialize_components()

    async def initialize(self):
        # Set up routes and handlers
        self.app.router.add_get('/ws', self.websocket_handler)
        
    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        try:
            await self._handle_connection(ws)
        finally:
            self.clients.remove(ws)
```

2. Event Loop Management
```python
class AsyncManager:
    def __init__(self):
        self.loop = None
        self.initialized = False

    async def initialize(self):
        self.loop = asyncio.get_running_loop()
        self.initialized = True

    async def cleanup(self):
        if self.loop and self.loop.is_running():
            # Cleanup tasks
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
```

3. Template Rendering
```python
# Setup
aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader('templates')
)

# Usage
@aiohttp_jinja2.template('index.html')
async def index(request):
    return {'data': await get_data()}
```

### Resource Management Patterns

1. Connection Management
```python
class ConnectionManager:
    def __init__(self):
        self._connections = set()
        self._lock = asyncio.Lock()

    async def add(self, connection):
        async with self._lock:
            self._connections.add(connection)

    async def remove(self, connection):
        async with self._lock:
            self._connections.remove(connection)
```

2. Resource Cleanup
```python
class ResourceManager:
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()
```

### Error Handling Patterns

1. WebSocket Error Handling
```python
async def handle_websocket(ws):
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                await process_message(msg)
            elif msg.type == WSMsgType.ERROR:
                logger.error(f"WebSocket error: {ws.exception()}")
    except Exception as e:
        logger.error(f"WebSocket handler error: {e}")
    finally:
        await cleanup_connection(ws)
```

2. Request Error Handling
```python
@web.middleware
async def error_middleware(request, handler):
    try:
        response = await handler(request)
        return response
    except web.HTTPException as ex:
        return web.json_response({'error': str(ex)}, status=ex.status)
    except Exception as ex:
        logger.error(f"Unhandled error: {ex}")
        return web.json_response(
            {'error': 'Internal server error'},
            status=500
        )
```

### Data Flow Patterns

1. Real-time Updates
```python
class DataStream:
    def __init__(self):
        self.subscribers = set()

    async def publish(self, data):
        for subscriber in self.subscribers:
            try:
                await subscriber.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send to subscriber: {e}")
                await self.remove_subscriber(subscriber)
```

2. Data Caching
```python
class DataCache:
    def __init__(self):
        self.cache = {}
        self.ttl = {}
        self._lock = asyncio.Lock()

    async def get(self, key):
        async with self._lock:
            if key in self.cache and not self._is_expired(key):
                return self.cache[key]
            return None
```

### Integration Patterns

1. Memory Bank Integration
```python
class MemoryBankMonitor:
    def __init__(self, memory_bank):
        self.memory_bank = memory_bank
        self.subscribers = set()

    async def start_monitoring(self):
        while True:
            state = await self.memory_bank.get_state()
            await self.notify_subscribers(state)
            await asyncio.sleep(5)
```

2. Storage Integration
```python
class StorageMonitor:
    def __init__(self, storage_hub):
        self.storage_hub = storage_hub
        self.metrics = {}

    async def update_metrics(self):
        self.metrics = {
            'size': await self.storage_hub.get_size(),
            'usage': await self.storage_hub.get_usage(),
            'performance': await self.storage_hub.get_performance()
        }
```

### Testing Patterns

1. WebSocket Testing
```python
async def test_websocket():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('/ws') as ws:
            await ws.send_json({'type': 'test'})
            response = await ws.receive_json()
            assert response['status'] == 'ok'
```

2. Template Testing
```python
async def test_template_rendering():
    async with client.get('/') as response:
        assert response.status == 200
        text = await response.text()
        assert 'Dashboard' in text
```

### Monitoring Patterns

1. Performance Monitoring
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}

    async def record_metric(self, name, value):
        timestamp = time.time()
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append((timestamp, value))
```

2. Health Monitoring
```python
class HealthMonitor:
    async def check_health(self):
        return {
            'websocket': await self.check_websocket(),
            'memory': await self.check_memory(),
            'storage': await self.check_storage(),
            'web3': await self.check_web3()
        }
