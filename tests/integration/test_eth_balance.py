import os
import json
import eventlet
from arbitrage_bot.utils.secure_env import init_secure_environment

def get_eth_balance(wallet_address):
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
        
        http = eventlet.import_patched('eventlet.green.urllib.request')
        data = json.dumps({
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [wallet_address, "latest"]
        }).encode('utf-8')
        
        req = http.Request(
            f"https://base-mainnet.g.alchemy.com/v2/{api_key}",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        response = http.urlopen(req, timeout=5).read()
        
        result = json.loads(response)
        if 'error' in result:
            raise ValueError(f"API error: {result['error']['message']}")
        
        eth_balance = int(result['result'], 16)  # Convert hex to int
        eth_balance_in_eth = eth_balance / 1e18  # Convert wei to ETH
        print(f"Wallet Address: {wallet_address}")
        print(f"ETH Balance: {eth_balance_in_eth:.6f} ETH")
        return eth_balance
        
    except Exception as e:
        print(f"Error: {e}")
        return 0

if __name__ == '__main__':
    # Use None to get wallet from secure environment
    get_eth_balance(None)