# Security Checklist

Before submitting this PR, please confirm:

- [ ] No sensitive data (private keys, addresses, API keys) is included
- [ ] No .env files or environment variables are committed
- [ ] Configuration files use environment variable placeholders
- [ ] Sensitive data is documented in secure locations only

## Configuration Security

This project uses environment variables for sensitive data:
1. Copy `configs/wallet_config.json.example` to `wallet_config.json`
2. Replace placeholders with actual values
3. Never commit the actual configuration files

## Required Environment Variables

```
WALLET_ADDRESS=
WALLET_PRIVATE_KEY=
NETWORK_RPC_URL=
FLASH_LOAN_CONTRACT=
POOL_ADDRESS_PROVIDER=
```

Keep these values secure and never share them in PRs, issues, or documentation.
