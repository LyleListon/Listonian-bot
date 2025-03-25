# Real-Time Metrics Optimization Plan

## Current Status

### Working Features
- Dashboard successfully displays real-time metrics
- WebSocket connections established and maintain connection
- System metrics (CPU, Memory) updating correctly
- Initial state properly sent on connection
- Basic cleanup implemented with context managers

### Issues Identified
1. WebSocket Cleanup
   - Tasks not properly cancelled during disconnection
   - Error messages about sending after connection close
   - Resource leaks during connection cycling

2. Performance Metrics
   - CPU Usage: ~14.8%
   - Memory Usage: ~27.4%
   - Connection overhead needs optimization

## Optimization Strategy

### 1. Connection Management
- Implement proper connection state machine
- Add connection lifecycle tracking
- Improve resource cleanup on disconnection
- Add connection pooling for better scaling

### 2. Task Management
```python
class TaskState:
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class TaskManager:
    def __init__(self):
        self._tasks = {}
        self._state = {}
        self._lock = asyncio.Lock()

    async def add_task(self, name, coro):
        async with self._lock:
            task = asyncio.create_task(coro)
            self._tasks[name] = task
            self._state[name] = TaskState.RUNNING
            return task

    async def cancel_task(self, name):
        async with self._lock:
            if name in self._tasks:
                self._state[name] = TaskState.CANCELLING
                task = self._tasks[name]
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=1.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Task {name} cancellation timeout")
                self._state[name] = TaskState.CANCELLED
```

### 3. Memory Optimization
- Implement message batching
- Add TTL for cached metrics
- Use weak references for connection tracking
- Implement proper garbage collection hooks

### 4. Performance Improvements
- Add metrics aggregation
- Implement update throttling
- Add connection backpressure handling
- Optimize JSON serialization

## Implementation Plan

### Phase 1: Connection Stability
1. Implement robust connection state machine
2. Add proper task cancellation
3. Improve resource cleanup
4. Add connection lifecycle logging

### Phase 2: Memory Management
1. Implement proper memory tracking
2. Add resource pooling
3. Optimize message handling
4. Add memory usage monitoring

### Phase 3: Performance Optimization
1. Implement metrics batching
2. Add update throttling
3. Optimize serialization
4. Add performance monitoring

## Code Structure

### Connection Manager
```python
class ConnectionState:
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"

class ConnectionManager:
    def __init__(self):
        self._connections = WeakKeyDictionary()
        self._task_manager = TaskManager()
        self._lock = asyncio.Lock()

    async def connect(self, websocket):
        async with self._lock:
            self._connections[websocket] = {
                "state": ConnectionState.CONNECTING,
                "tasks": set(),
                "queues": set(),
                "connected_at": datetime.utcnow()
            }
            await websocket.accept()
            self._connections[websocket]["state"] = ConnectionState.CONNECTED

    async def disconnect(self, websocket):
        async with self._lock:
            if websocket in self._connections:
                self._connections[websocket]["state"] = ConnectionState.DISCONNECTING
                await self._cleanup_tasks(websocket)
                await self._cleanup_queues(websocket)
                self._connections[websocket]["state"] = ConnectionState.DISCONNECTED
                del self._connections[websocket]
```

### Metrics Service
```python
class MetricsService:
    def __init__(self):
        self._cache = {}
        self._cache_ttl = 1.0  # 1 second TTL
        self._subscribers = set()
        self._lock = asyncio.Lock()

    async def get_metrics(self):
        async with self._lock:
            now = time.time()
            if not self._cache or now - self._cache["timestamp"] > self._cache_ttl:
                metrics = await self._collect_metrics()
                self._cache = {
                    "data": metrics,
                    "timestamp": now
                }
            return self._cache["data"]

    async def broadcast_metrics(self, metrics):
        tasks = []
        for subscriber in self._subscribers:
            if not subscriber.full():
                tasks.append(subscriber.put_nowait(metrics))
        await asyncio.gather(*tasks, return_exceptions=True)
```

## Monitoring Plan

### Metrics to Track
1. Connection Statistics
   - Active connections
   - Connection duration
   - Disconnection rate
   - Error rate

2. Performance Metrics
   - Message latency
   - CPU usage
   - Memory usage
   - Garbage collection stats

3. Resource Usage
   - Task count
   - Queue sizes
   - Cache hit rate
   - Memory allocation

### Alerting Thresholds
- CPU Usage > 50%
- Memory Usage > 75%
- Error Rate > 1%
- Connection Failures > 5%
- Message Latency > 100ms

## Next Steps
1. Implement TaskManager class
2. Update ConnectionManager with state machine
3. Add metrics batching
4. Implement proper cleanup
5. Add comprehensive monitoring
6. Test connection cycling
7. Optimize resource usage
8. Add performance benchmarks

## Notes
- All implementations must follow asyncio patterns
- Proper error handling is critical
- Resource cleanup must be thorough
- Monitor memory usage carefully
- Test connection edge cases
- Document all changes
- Add comprehensive logging