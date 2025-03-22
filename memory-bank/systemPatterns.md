# System Patterns and Best Practices

## Secure Key Management

### Private Key Handling
1. Storage Pattern:
   ```python
   class SecureEnvironment:
       def secure_store(self, name: str, value: str):
           encrypted = self.encrypt_value(value)
           with open(self.secure_path / f'{name}.enc', 'w') as f:
               f.write(encrypted)
   ```

2. Decryption Pattern:
   ```python
   def decrypt_value(self, encrypted_value: str, key_name: str = None) -> str:
       try:
           decrypted = self.fernet.decrypt(base64.urlsafe_b64decode(encrypted_value))
           if key_name == 'PRIVATE_KEY':
               # Handle base64 encoded keys
               decrypted = base64.b64decode(decrypted).hex()
           return decrypted
       except Exception as e:
           logger.error(f"Failed to decrypt value: {e}")
           return None
   ```

### Configuration Loading
1. Secure Value Resolution:
   ```python
   def resolve_secure_values(config: Dict[str, Any]) -> Dict[str, Any]:
       resolved = config.copy()
       for section in resolved:
           if isinstance(resolved[section], dict):
               for key, value in resolved[section].items():
                   if value.startswith('$SECURE:'):
                       secure_value = secure_env.secure_load(value[8:])
                       resolved[section][key] = secure_value
       return resolved
   ```

2. Validation Pattern:
   ```python
   def validate_private_key(key: str) -> bool:
       return len(key) == 64 and all(c in '0123456789abcdefABCDEF' for c in key)
   ```

## Error Handling Patterns

### Secure Operations
1. Context Preservation:
   ```python
   try:
       value = secure_env.secure_load(name)
       if not value:
           raise ValueError(f"Failed to load secure value for {name}")
   except Exception as e:
       logger.error(f"Security operation failed: {e}")
       raise
   ```

2. Validation Chain:
   ```python
   def validate_config(config: Dict[str, Any]) -> None:
       # Resolve secure values first
       config = resolve_secure_values(config)
       # Then validate format
       validate_private_key(config['web3']['wallet_key'])
       # Finally configure dependent components
       config['flashbots']['auth_key'] = config['web3']['wallet_key']
   ```

## Logging Patterns

### Debug Information
1. Secure Operation Logging:
   ```python
   logger.debug(f"Loading secure value from {file_path}")
   logger.debug(f"Successfully loaded secure value for {name}")
   logger.error(f"Failed to decrypt value for {name}")
   ```

2. Validation Logging:
   ```python
   logger.debug(f"Attempting base64 decode for {key_name}")
   logger.debug(f"Successfully decoded {key_name} to hex: {value[:6]}...")
   ```

## Resource Management

### Initialization Pattern
```python
def init_secure_environment():
    load_dotenv('.env.production')
    secure_env = SecureEnvironment()
    env_vars = {var: os.getenv(var) for var in sensitive_vars}
    secure_env.secure_env(env_vars)
    secure_env.load_secure_env()
    return secure_env
```

### Cleanup Pattern
```python
def cleanup_secure_resources():
    for var in sensitive_vars:
        if var in os.environ:
            del os.environ[var]
```

## Configuration Management

### Loading Sequence
1. Load environment variables
2. Initialize secure environment
3. Load configuration file
4. Resolve secure values
5. Validate formats
6. Configure dependent components

### Validation Sequence
1. Check required sections
2. Validate field presence
3. Verify value formats
4. Configure cross-dependencies

## Testing Patterns

### Secure Operation Tests
```python
def test_secure_key_handling():
    # Given
    secure_env = SecureEnvironment()
    test_key = "0123456789abcdef" * 4
    
    # When
    secure_env.secure_store("TEST_KEY", test_key)
    loaded_key = secure_env.secure_load("TEST_KEY")
    
    # Then
    assert loaded_key == test_key
```

### Configuration Tests
```python
def test_config_validation():
    # Given
    config = load_test_config()
    
    # When
    validated_config = validate_config(config)
    
    # Then
    assert validate_private_key(validated_config['web3']['wallet_key'])
    assert validated_config['flashbots']['auth_key'] == validated_config['web3']['wallet_key']
```

## Documentation Requirements

### Code Documentation
- Include purpose and usage
- Document parameters and return values
- Explain security considerations
- Note format requirements

### Error Documentation
- List possible error conditions
- Document error handling
- Provide recovery steps
- Include logging details

### Configuration Documentation
- Specify required fields
- Document format requirements
- Explain validation rules
- List dependencies
