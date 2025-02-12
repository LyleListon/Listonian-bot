# Configuration System

## Overview
This directory contains all configuration files and schemas for the arbitrage bot system. The configuration system uses a layered approach with environment-specific overrides.

## Structure
```
configs/
├── default.json       # Base configuration
├── production.json    # Production overrides
├── local.json        # Local development settings
└── schemas/          # JSON schemas for validation
    ├── config.schema.json
    └── validation.js
```

## Configuration Files

### default.json
Base configuration that defines all available settings with default values. This file should:
- Include all possible configuration options
- Provide safe default values
- Include detailed comments for each setting
- Never contain sensitive information

### production.json
Production environment overrides. This file:
- Only includes settings that differ from default.json
- Contains production-specific optimizations
- References environment variables for sensitive data
- Focuses on performance and security

### local.json
Local development settings. This file:
- Overrides settings for local development
- Contains development-specific features
- Uses local endpoints and services
- May include debug settings

## Environment Variables
Sensitive information should be provided via environment variables:
- `PRIVATE_KEY` - Wallet private key
- `BASE_RPC_URL` - RPC endpoint URL
- `CHAIN_ID` - Network chain ID
- Other sensitive credentials

## Configuration Schema
The schema system validates all configuration files to ensure:
- Required fields are present
- Values are of correct type
- Enums contain valid values
- Nested objects are properly structured

## Usage
```python
from config import load_config

# Load configuration with environment-specific overrides
config = load_config()

# Access configuration values
rpc_url = config.network.rpc_url
gas_limit = config.trading.gas_limit
```

## Best Practices
1. Never commit sensitive data
2. Always validate against schema
3. Use environment variables for secrets
4. Document all configuration options
5. Keep overrides minimal
6. Version control configuration schema

## Validation
Run configuration validation:
```bash
python -m scripts.validate_config
```

Last Updated: 2025-02-10