"""
Initialize secure environment with configuration values
"""
import json
import os
from dotenv import load_dotenv
from arbitrage_bot.utils.secure_env import SecureEnvironment

def init_secure_storage():
    # Load environment variables
    load_dotenv('.env.production')
    
    # Load config values
    with open('configs/config.json', 'r') as f:
        config = json.load(f)
    
    # Initialize secure environment
    secure_env = SecureEnvironment()
    
    # Get private key from environment
    private_key = os.environ.get('PRIVATE_KEY')
    if not private_key:
        raise ValueError("PRIVATE_KEY environment variable is required")
    
    # Store sensitive values
    secure_env.secure_store('ALCHEMY_API_KEY', config['network']['rpc_url'].split('/')[-1])
    secure_env.secure_store('PRIVATE_KEY', private_key)
    secure_env.secure_store('WALLET_ADDRESS', config['wallet']['wallet_address'])
    
    print("Secure environment initialized with values from config.json and environment")

if __name__ == "__main__":
    init_secure_storage()
