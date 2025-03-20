# System Patterns and Architecture - March 18, 2025

## Core Architectural Patterns

### 1. Async First
```python
async def get_pool_data(contract: Contract) -> Dict[str, Any]:
    async with self._lock:
        return await contract.functions.currentState().call()
```
- All operations are async/await
- Proper error handling
- Resource management
- Event loop consideration

### 2. Thread Safety
```python
class Cache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._data = {}
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            return self._data.get(key)
```
- Lock management
- Atomic operations
- Resource protection
- State consistency

### 3. Resource Management
```python
@asynccontextmanager
async def managed_resource():
    try:
        yield resource
    finally:
        await cleanup()
```
- Context managers
- Cleanup handlers
- Error boundaries
- Resource tracking

### 4. Error Handling
```python
try:
    async with timeout(5):
        result = await operation()
except TimeoutError:
    logger.error("Operation timed out")
    raise OperationError("Timeout")
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise
```
- Context preservation
- Logging
- Recovery strategies
- Error propagation

## Implementation Patterns

### 1. DEX Integration
```python
class BaseDEX:
    async def get_price(self) -> Decimal:
        pass

class SwapBasedV3(BaseDEX):
    async def get_price(self) -> Decimal:
        data = await self.get_pool_data()
        return self.calculate_price(data)
```
- Inheritance hierarchy
- Interface contracts
- Version specifics
- Common functionality

### 2. Cache Management
```python
class Cache:
    async def set(self, key: str, value: Any, ttl: int) -> None:
        async with self._lock:
            self._data[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
```
- TTL-based invalidation
- Thread safety
- Memory efficiency
- Background cleanup

### 3. Web3 Interaction
```python
class Web3Manager:
    async def load_contract(self, address: str, abi: str) -> Contract:
        if not Web3.is_checksum_address(address):
            raise ValueError("Invalid address")
        return self.web3.eth.contract(address=address, abi=abi)
```
- Address validation
- Contract caching
- Provider management
- Transaction building

### 4. Storage Layer
```python
class DatabasePool:
    async def acquire(self):
        async with self._lock:
            conn = await self._pool.acquire()
            return ManagedConnection(conn, self._pool)
```
- Connection pooling
- Resource cleanup
- Transaction isolation
- Error handling

## Design Patterns

### 1. Singleton Management
```python
_instance = None

def get_instance() -> Manager:
    global _instance
    if _instance is None:
        _instance = Manager()
    return _instance
```
- Single source of truth
- Lazy initialization
- Thread safety
- Resource sharing

### 2. Factory Methods
```python
async def create_dex(name: str, version: int) -> BaseDEX:
    if version == 3:
        if name == "swapbased":
            return SwapBasedV3()
    raise ValueError("Unsupported DEX")
```
- Object creation
- Configuration
- Dependency injection
- Flexibility

### 3. Observer Pattern
```python
class PriceMonitor:
    async def notify_observers(self, price: Decimal) -> None:
        for observer in self._observers:
            await observer.on_price_change(price)
```
- Event notification
- State changes
- Decoupling
- Async updates

### 4. Strategy Pattern
```python
class ArbitrageStrategy:
    async def execute(self, path: List[Pool]) -> Decimal:
        return await self._strategy.calculate_profit(path)
```
- Interchangeable algorithms
- Runtime selection
- Clean separation
- Easy extension

## Best Practices

### 1. Validation
```python
def validate_address(address: str) -> bool:
    if not Web3.is_address(address):
        raise ValueError("Invalid address format")
    return Web3.to_checksum_address(address)
```
- Input validation
- Type checking
- Error messages
- Early returns

### 2. Logging
```python
logger = logging.getLogger(__name__)
logger.info("Operation started")
try:
    result = await operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
```
- Consistent format
- Error tracking
- Performance monitoring
- Debugging support

### 3. Configuration
```python
class Config:
    def __init__(self):
        self.load_env()
        self.validate()
```
- Environment variables
- Validation
- Defaults
- Documentation

### 4. Testing
```python
@pytest.mark.asyncio
async def test_operation():
    async with MockResource() as resource:
        result = await operation(resource)
        assert result.status == "success"
```
- Async testing
- Mocking
- Fixtures
- Coverage

Remember:
- Always use async/await
- Maintain thread safety
- Handle errors properly
- Clean up resources
- Validate inputs
- Log operations
