# Arbitrum Goerli Setup Guide

## Faucets
1. Official Arbitrum Goerli Faucet
   - Visit: https://goerli-faucet.arbitrum.io/
   - Connect wallet and request testnet ETH
   - Rate limit: 0.1 ETH per day

2. Alchemy Faucet
   - Visit: https://goerlifaucet.com/
   - Requires Alchemy account
   - Provides Goerli ETH (bridge to Arbitrum)

3. Paradigm Faucet
   - Visit: https://faucet.paradigm.xyz/
   - Multi-chain faucet including Arbitrum Goerli

## Key Contract Addresses
- WETH: 0xe39Ab88f8A4777030A534146A9Ca3B52bd5D43A3
- USDC: 0x8FB1E3fC51F3b789dED7557E680551d93Ea9d892
- Uniswap V3 Factory: 0x4893376342d5D7b3e31d4184c08b265e5aB2A3f6

## Bridge
- Official Bridge: https://bridge.arbitrum.io/
- Bridge Goerli ETH to Arbitrum Goerli

## Block Explorer
- Arbitrum Goerli Explorer: https://goerli.arbiscan.io/

## RPC Endpoints
- Public RPC: https://goerli-rollup.arbitrum.io/rpc
- Alchemy: https://arb-goerli.g.alchemy.com/v2/YOUR-API-KEY
- Infura: https://arbitrum-goerli.infura.io/v3/YOUR-API-KEY

## Network Details
- Network Name: Arbitrum Goerli
- Chain ID: 421613
- Currency Symbol: ETH
- Block Explorer URL: https://goerli.arbiscan.io/

## Next Steps
1. Get testnet ETH from faucets
2. Use wrap_eth_arbitrum.js to convert ETH to WETH
3. Run check_arbitrum_pools.js to verify Uniswap V3 setup
