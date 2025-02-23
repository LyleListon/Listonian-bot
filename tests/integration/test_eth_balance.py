import os
import json
import asyncio
import aiohttp
from arbitrage_bot.utils.secure_env import init_secure_environment

async def get_eth_balance(wallet_address):
    try:
        # Initialize secure environment
        secure_env = init_secure_environment()
        
        # Get API key from secure environment
        api_key = secure_env.secure_load('ALCHEMY_API_KEY')
        if not api_key:
            raise ValueError("Failed to load ALCHEMY_API_KEY from secure environment")
            
        # Get wallet address from secure environment if none provided
        if not wallet_address:
            wallet_address = secure_env.secure_load('WALLET_ADDRESS')
            if not wallet_address:
                raise ValueError("No wallet address provided and failed to load from secure environment")
        
        data = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [wallet_address, "latest"]
        }
        
        url = "https://base-mainnet.g.alchemy.com/v2/{}".format(api_key)
        headers = {'Content-Type': 'application/json'}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=5) as response:
                result = await response.json()
                
                if 'error' in result:
                    raise ValueError("API error: {}".format(result['error']['message']))
                
                eth_balance = int(result['result'], 16)  # Convert hex to int
                eth_balance_in_eth = eth_balance / 1e18  # Convert wei to ETH
                print("Wallet Address: {}".format(wallet_address))
                print("ETH Balance: {:.6f} ETH".format(eth_balance_in_eth))
                return eth_balance
        
    except Exception as e:
        print("Error: {}".format(e))
        return 0

async def main():
    """Main entry point."""
    # Use None to get wallet from secure environment
    await get_eth_balance(None)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Test stopped by user")
    except Exception as e:
        print("Test error: {}".format(e))
        raise