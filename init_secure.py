"""
Initialize secure environment with configuration values
"""
import json
from arbitrage_bot.utils.secure_env import SecureEnvironment

def init_secure_storage():
    # Load config values
    with open('configs/config.json', 'r') as f:
        config = json.load(f)
    
    # Initialize secure environment
    secure_env = SecureEnvironment()
    
    # Store sensitive values
    secure_env.secure_store('ALCHEMY_API_KEY', config['network']['rpc_url'].split('/')[-1])
    secure_env.secure_store('PRIVATE_KEY', config['wallet']['private_key'])
    secure_env.secure_store('WALLET_ADDRESS', config['wallet']['address'])
    
    print("Secure environment initialized with values from config.json")

if __name__ == "__main__":
    init_secure_storage()
