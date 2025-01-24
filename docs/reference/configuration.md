# System Configuration Reference

Copy this template to system.conf and update with your values:

`ini
[network]
rpc_endpoint = 'RPC_ENDPOINT_HERE'
ws_endpoint = 'WEBSOCKET_ENDPOINT_HERE'

[auth]
credentials = 'AUTH_CREDENTIALS_HERE'

[services]
etherscan_id = 'ETHERSCAN_ID_HERE'
infura_id = 'INFURA_ID_HERE'

[trading]
min_profit = 0.002
min_profit_usd = 3.00
max_slippage = 0.002
max_gas = 5
gas_limit = 350000
max_impact = 0.02

[system]
log = 'INFO'
dashboard = true
host = '127.0.0.1'
port = 5000

[security]
test_mode = false
alerts = true

[performance]
update_ms = 500
retry_ms = 1000
max_retries = 3
`

Note: Replace placeholder values with your actual configuration values. Never commit files containing real credentials.
