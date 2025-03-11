# System Patterns

## Web3 Contract Handling Patterns

### Contract Creation Pattern
```python
# Always use the Web3Manager's contract method
contract = web3_manager.contract(address, abi)

# Never create contracts directly with web3.py
# BAD: contract = web3.eth.contract(address, abi)
```

### Async Contract Interaction Pattern
```python
# Always use async/await for contract calls
result = await contract.functions.method().call()

# Never use synchronous calls
# BAD: result = contract.functions.method().call()
```

### Property Access Pattern
```python
# Use instance variables for module access
self._eth = self.w3.eth

# Never use property setters for core modules
# BAD: @eth.setter
```

### Error Handling Pattern
```python
try:
    result = await contract.functions.method().call()
except Exception as e:
    logger.error(f"Contract call failed: {e}")
    # Always preserve context
    raise
```

## Resource Management Patterns

### Contract Instance Management
```python
# Initialize in constructor
self._raw_w3 = Web3(Web3.HTTPProvider(provider_url))
self.w3 = Web3ClientWrapper(self._raw_w3)

# Clean up in close method
async def close(self):
    if hasattr(self._raw_w3.provider, "close"):
        await self._raw_w3.provider.close()
```

### Lock Management
```python
# Use AsyncLock for thread safety
async with self._request_lock:
    result = await self.contract.functions.method().call()
```

## DEX Integration Patterns

### Factory Contract Pattern
```python
# Create factory contract
factory_contract = self.web3_manager.contract(
    address=dex.factory_address,
    abi=dex.factory_abi
)

# Get pool address
pool = await factory_contract.functions.getPool(
    token0,
    token1,
    fee
).call()
```

### Pool Contract Pattern
```python
# Create pool contract
pool_contract = self.web3_manager.contract(
    address=pool_address,
    abi=dex.pool_abi
)

# Get reserves
reserves = await pool_contract.functions.getReserves().call()
```

## Flash Loan Patterns

### Balancer Integration
```python
# Create vault contract
vault_contract = self.web3_manager.contract(
    address=config['balancer']['vault_address'],
    abi=vault_abi
)

# Execute flash loan
await vault_contract.functions.flashLoan(
    recipient,
    tokens,
    amounts,
    data
).call()
```

## Flashbots Integration Patterns

### Bundle Submission
```python
# Create bundle
bundle = await flashbots_provider.create_bundle([
    transaction1,
    transaction2
])

# Simulate bundle
simulation = await flashbots_provider.simulate_bundle(bundle)
```

## Error Handling Patterns

### Contract Call Retry Pattern
```python
@with_retry(retries=3, delay=1.0)
async def get_pool(self, token0: str, token1: str) -> str:
    return await self.factory_contract.functions.getPool(
        token0,
        token1
    ).call()
```

### Error Context Preservation
```python
try:
    result = await contract.functions.method().call()
except Exception as e:
    logger.error(
        f"Failed to call {method} on {contract.address}: {e}",
        exc_info=True
    )
    raise
```

## Logging Patterns

### Contract Interaction Logging
```python
logger.info(
    f"Contract call {method} on {contract.address} "
    f"with args: {args}"
)
result = await contract.functions[method](*args).call()
logger.debug(f"Contract call result: {result}")
```

### Error Logging
```python
logger.error(
    f"Contract {contract.address} error: {e}",
    exc_info=True,
    extra={
        'method': method,
        'args': args,
        'gas_used': gas_used
    }
)
```

## Testing Patterns

### Contract Mock Pattern
```python
class MockContract:
    async def functions(self):
        return {
            'method': lambda *args: {'call': lambda: result}
        }
```

### Integration Test Pattern
```python
async def test_contract_interaction():
    contract = web3_manager.contract(address, abi)
    result = await contract.functions.method().call()
    assert result == expected
```

## Performance Patterns

### Batch Contract Call Pattern
```python
async def get_multiple_pools(self, pairs: List[Tuple[str, str]]) -> List[str]:
    return await asyncio.gather(*[
        self.get_pool(token0, token1)
        for token0, token1 in pairs
    ])
```

### Caching Pattern
```python
@cached(ttl=300)  # 5 minutes
async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
    return await self.pool_contract.functions.getPoolInfo().call()
```

## Security Patterns

### Address Validation Pattern
```python
def validate_address(address: str) -> ChecksumAddress:
    if not Web3.is_address(address):
        raise ValueError(f"Invalid address: {address}")
    return Web3.to_checksum_address(address)
```

### Balance Verification Pattern
```python
async def verify_balance(self, token: str, amount: int) -> bool:
    balance = await self.get_token_balance(token)
    return balance >= amount
```

Remember:
- Always use async/await for contract interactions
- Always handle errors with proper context
- Always use proper resource management
- Always validate inputs and outputs
- Always use proper logging
- Always use proper testing patterns
