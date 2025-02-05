# Secure Configuration Guide

## Environment Variables Required

### Wallet Configuration
- `WALLET_ADDRESS`: Your wallet address
- `WALLET_PRIVATE_KEY`: Your wallet's private key

### Network Configuration
- `NETWORK_RPC_URL`: RPC endpoint URL

### Flash Loan Configuration
- `FLASH_LOAN_CONTRACT`: Flash loan contract address
- `POOL_ADDRESS_PROVIDER`: Pool address provider

## Setup Instructions

1. Create a `.env` file in the project root
2. Add the required environment variables listed above
3. Never commit the `.env` file to version control
4. Keep your private key secure and never share it

## Configuration Files

The following files use these environment variables:
- `configs/wallet_config.json`
- `configs/config.json`

## Security Best Practices

1. Rotate credentials regularly
2. Use different wallets for development and production
3. Monitor wallet activity for unauthorized transactions
4. Keep environment variables secure and never expose them in logs or error messages