# Technical Context - March 18, 2025

## Technology Stack

### Core Technologies
- Python 3.12+
- Web3.py
- asyncio
- aiohttp
- SQLAlchemy (async)

### Infrastructure
- Base Mainnet
- Private RPC endpoints
- Flashbots RPC (pending)
- Multicall contract

### Development Tools
- VSCode
- pytest
- mypy
- black
- isort

## Implementation Details

### Web3 Layer (`arbitrage_bot/core/web3.py`)
```python
class Web3Manager:
    """Manages Web3 interactions and contract operations."""
    def __init__(self):
        self._lock = asyncio.Lock()
        self._contract_cache = {}
        self._provider = None
```
- Thread-safe contract management
- Connection pooling
- Error handling
- Transaction building

### Storage Layer (`arbitrage_bot/core/storage.py`)
```python
class DatabasePool:
    """Manages database connections and transactions."""
    async def acquire(self):
        async with self._lock:
            return await self._pool.acquire()
```
- Connection pooling
- Transaction isolation
- Resource cleanup
- Error context

### Cache System (`arbitrage_bot/core/cache.py`)
```python
class Cache:
    """Thread-safe TTL cache implementation."""
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            return await self._get_with_ttl(key)
```
- TTL-based invalidation
- Memory management
- Thread safety
- Background cleanup

### DEX Interface (`arbitrage_bot/core/dex.py`)
```python
class BaseDEX:
    """Base class for DEX implementations."""
    async def get_price(self, token_pair: Tuple[str, str]) -> Decimal:
        async with self._lock:
            return await self._fetch_price(token_pair)
```
- Version abstraction
- Price calculation
- Liquidity validation
- Error handling

## Key Components

### Contract Interaction
1. Loading
   ```python
   contract = await load_contract(address, abi_name)
   ```

2. Execution
   ```python
   async with timeout(5):
       result = await contract.functions.method().call()
   ```

3. Transaction Building
   ```python
   tx = await build_transaction(params)
   signed = await sign_transaction(tx)
   ```

### Data Management
1. Storage
   ```python
   async with pool.acquire() as conn:
       await conn.execute(query, params)
   ```

2. Caching
   ```python
   value = await cache.get(key)
   if value is None:
       value = await fetch_data()
       await cache.set(key, value, ttl=300)
   ```

3. State Management
   ```python
   async with state_lock:
       current = await get_state()
       updated = await update_state(current)
   ```

## Critical Paths

### Price Discovery
1. Pool Data
   ```python
   data = await pool.get_current_state()
   price = calculate_price(data)
   ```

2. Validation
   ```python
   if not validate_liquidity(data, min_amount):
       raise InsufficientLiquidity()
   ```

### Transaction Flow
1. Preparation
   ```python
   bundle = await prepare_bundle(transactions)
   simulation = await simulate_bundle(bundle)
   ```

2. Execution
   ```python
   if simulation.profit > min_profit:
       result = await execute_bundle(bundle)
   ```

## Error Handling

### Pattern
```python
try:
    async with timeout(TIMEOUT):
        result = await operation()
except TimeoutError:
    logger.error("Operation timed out")
    raise OperationTimeout()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### Recovery
```python
async def with_retry(operation, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return await operation()
        except RetryableError:
            await asyncio.sleep(1 << attempt)
```

## Performance Considerations

### Concurrency
- Use asyncio for I/O operations
- Implement proper locking
- Batch operations where possible
- Monitor resource usage

### Caching
- TTL-based invalidation
- Memory limits
- Thread safety
- Background cleanup

### Resource Management
- Connection pooling
- Context managers
- Cleanup handlers
- Memory monitoring

## Security Measures

### Input Validation
```python
def validate_address(address: str) -> str:
    if not Web3.is_address(address):
        raise ValueError("Invalid address")
    return Web3.to_checksum_address(address)
```

### Transaction Safety
```python
async def validate_transaction(tx: Dict[str, Any]) -> bool:
    simulation = await simulate_transaction(tx)
    return (
        simulation.success and
        simulation.gas_used < MAX_GAS and
        simulation.price_impact < MAX_IMPACT
    )
```

## Next Steps
1. Flashbots Integration
   - Bundle submission
   - MEV protection
   - Transaction privacy

2. Multi-path Arbitrage
   - Path optimization
   - Price impact analysis
   - Risk assessment

3. Performance Optimization
   - Batch operations
   - Cache tuning
   - Resource monitoring

Remember:
- Always use async/await
- Implement proper locking
- Handle errors appropriately
- Clean up resources
- Validate inputs
- Monitor performance
