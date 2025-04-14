# Listonian Bot Integration Specifications

## DEX Integrations

### PancakeSwap

#### Connection Details
- **API Endpoint**: https://api.pancakeswap.finance/
- **Chain**: BNB Chain (BSC)
- **Factory Contract**: `0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73`
- **Router Contract**: `0x10ED43C718714eb63d5aA57B78B54704E256024E`
- **Integration Module**: `arbitrage_bot/integration/dex/pancakeswap.py`

#### Required Methods
- `get_token_price(token_address)`
- `get_reserves(pair_address)`
- `get_pairs()`
- `calculate_output_amount(input_token, output_token, input_amount)`
- `execute_swap(input_token, output_token, input_amount, min_output_amount, deadline)`

#### Authentication
- No authentication required for read operations
- Wallet signature required for transactions

#### Rate Limits
- 10 requests per second for public API
- No limits for direct contract interactions

---

### UniswapV3

#### Connection Details
- **API Endpoint**: https://api.uniswap.org/v1/
- **Chain**: Ethereum
- **Factory Contract**: `0x1F98431c8aD98523631AE4a59f267346ea31F984`
- **Router Contract**: `0xE592427A0AEce92De3Edee1F18E0157C05861564`
- **Integration Module**: `arbitrage_bot/integration/dex/uniswap_v3.py`

#### Required Methods
- `get_token_price(token_address)`
- `get_pool_liquidity(pool_address)`
- `get_pools()`
- `calculate_output_amount(input_token, output_token, input_amount, fee_tier)`
- `execute_swap(input_token, output_token, input_amount, min_output_amount, fee_tier, deadline)`

#### Authentication
- API key required for some endpoints
- Wallet signature required for transactions

#### Rate Limits
- 100 requests per minute with API key
- 30 requests per minute without API key

---

### SwapBased

#### Connection Details
- **API Endpoint**: https://api.swapbased.finance/
- **Chain**: Base
- **Factory Contract**: `0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6`
- **Router Contract**: `0x327Df1E6de05895d2ab08513aaDD9313Fe505d86`
- **Integration Module**: `arbitrage_bot/integration/dex/swapbased.py`

#### Required Methods
- `get_token_price(token_address)`
- `get_reserves(pair_address)`
- `get_pairs()`
- `calculate_output_amount(input_token, output_token, input_amount)`
- `execute_swap(input_token, output_token, input_amount, min_output_amount, deadline)`

#### Authentication
- No authentication required for read operations
- Wallet signature required for transactions

#### Rate Limits
- 20 requests per second for public API
- No limits for direct contract interactions

---

## MEV Protection Integrations

### Flashbots

#### Connection Details
- **API Endpoint**: https://relay.flashbots.net/
- **Supported Chains**: Ethereum
- **Integration Module**: `arbitrage_bot/integration/mev_protection/flashbots.py`

#### Required Methods
- `create_bundle(transactions)`
- `simulate_bundle(bundle)`
- `send_bundle(bundle, target_block_number)`
- `get_bundle_stats(bundle_id)`

#### Authentication
- Ethereum private key for signing bundles

#### Rate Limits
- 10 requests per second

---

### MEV-Blocker

#### Connection Details
- **API Endpoint**: https://rpc.mevblocker.io
- **Supported Chains**: Ethereum
- **Integration Module**: `arbitrage_bot/integration/mev_protection/mev_blocker.py`

#### Required Methods
- `send_private_transaction(transaction)`
- `get_transaction_status(tx_hash)`

#### Authentication
- No authentication required

#### Rate Limits
- 5 requests per second

---

## Flash Loan Integrations

### Aave

#### Connection Details
- **API Endpoint**: N/A (Direct contract interaction)
- **Lending Pool Contract**: `0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9` (Ethereum)
- **Integration Module**: `arbitrage_bot/integration/flash_loans/aave.py`

#### Required Methods
- `get_available_liquidity(token_address)`
- `execute_flash_loan(token_address, amount, params)`
- `calculate_fee(token_address, amount)`

#### Authentication
- Wallet signature required for transactions

#### Rate Limits
- No API rate limits (blockchain transaction limits apply)

---

### DyDx

#### Connection Details
- **API Endpoint**: https://api.dydx.exchange/v3/
- **Solo Contract**: `0x1E0447b19BB6EcFdAe1e4AE1694b0C3659614e4e` (Ethereum)
- **Integration Module**: `arbitrage_bot/integration/flash_loans/dydx.py`

#### Required Methods
- `get_markets()`
- `get_market_liquidity(market_id)`
- `execute_flash_loan(token_address, amount, params)`

#### Authentication
- API key required for some endpoints
- Wallet signature required for transactions

#### Rate Limits
- 100 requests per minute with API key

---

## Blockchain Node Integrations

### Ethereum

#### Connection Details
- **RPC Endpoint**: https://mainnet.infura.io/v3/YOUR_API_KEY
- **WebSocket**: wss://mainnet.infura.io/ws/v3/YOUR_API_KEY
- **Chain ID**: 1
- **Integration Module**: `arbitrage_bot/integration/blockchain/ethereum.py`

#### Required Methods
- `get_gas_price()`
- `get_block(block_number)`
- `get_transaction(tx_hash)`
- `send_transaction(signed_tx)`
- `estimate_gas(tx_params)`
- `get_token_balance(token_address, wallet_address)`

#### Authentication
- API key required

#### Rate Limits
- Depends on provider plan

---

### BNB Chain

#### Connection Details
- **RPC Endpoint**: https://bsc-dataseed.binance.org/
- **WebSocket**: wss://bsc-ws-node.nariox.org:443
- **Chain ID**: 56
- **Integration Module**: `arbitrage_bot/integration/blockchain/bnb_chain.py`

#### Required Methods
- `get_gas_price()`
- `get_block(block_number)`
- `get_transaction(tx_hash)`
- `send_transaction(signed_tx)`
- `estimate_gas(tx_params)`
- `get_token_balance(token_address, wallet_address)`

#### Authentication
- No authentication required

#### Rate Limits
- 10 requests per second

---

### Base

#### Connection Details
- **RPC Endpoint**: https://mainnet.base.org
- **WebSocket**: wss://mainnet.base.org
- **Chain ID**: 8453
- **Integration Module**: `arbitrage_bot/integration/blockchain/base.py`

#### Required Methods
- `get_gas_price()`
- `get_block(block_number)`
- `get_transaction(tx_hash)`
- `send_transaction(signed_tx)`
- `estimate_gas(tx_params)`
- `get_token_balance(token_address, wallet_address)`

#### Authentication
- No authentication required

#### Rate Limits
- 20 requests per second

---

## API Integration

### External API

#### Endpoints

| Endpoint | Method | Description | Parameters | Response |
|----------|--------|-------------|------------|----------|
| `/api/v1/status` | GET | Get system status | None | JSON with system status |
| `/api/v1/opportunities` | GET | Get current arbitrage opportunities | `min_profit`, `max_slippage` | JSON array of opportunities |
| `/api/v1/trades` | GET | Get recent trades | `limit`, `offset` | JSON array of trades |
| `/api/v1/balance` | GET | Get wallet balances | `wallet_address` | JSON with token balances |
| `/api/v1/execute` | POST | Execute a trade | `opportunity_id`, `wallet_address` | JSON with transaction details |

#### Authentication
- API key required in headers: `X-API-KEY: your_api_key`

#### Rate Limits
- 100 requests per minute per API key

---

### Dashboard API

#### Endpoints

| Endpoint | Method | Description | Parameters | Response |
|----------|--------|-------------|------------|----------|
| `/api/dashboard/metrics` | GET | Get dashboard metrics | None | JSON with system metrics |
| `/api/dashboard/trades` | GET | Get trade history | `limit`, `offset`, `status` | JSON array of trades |
| `/api/dashboard/performance` | GET | Get performance metrics | `timeframe` | JSON with performance data |
| `/api/dashboard/tokens` | GET | Get token information | None | JSON array of tokens |
| `/api/dashboard/settings` | GET/POST | Get/update settings | Various settings | JSON with settings |

#### Authentication
- JWT token required in headers: `Authorization: Bearer your_jwt_token`

#### Rate Limits
- 200 requests per minute per user
