"""
Generate Flashbots Authentication Key

This script generates a new Ethereum private key specifically for Flashbots authentication.
This key is different from your wallet's private key and is only used for signing bundles.
"""

from eth_account import Account
import json
import os

# Enable Account creation
Account.enable_unaudited_hdwallet_features()

def generate_flashbots_auth():
    # Generate new account
    account = Account.create()
    
    # Get private key
    private_key = account.key.hex()
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
        
    # Get address
    address = account.address
    
    print("\nFlashbots Authentication Key Generated:")
    print(f"Address: {address}")
    print(f"Private Key: {private_key}")
    
    # Update configs/production.json
    config_path = 'configs/production.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        if 'flashbots' not in config:
            config['flashbots'] = {}
            
        config['flashbots']['auth_key'] = private_key
        config['flashbots']['relay_url'] = 'https://relay.flashbots.net'
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        print("\nConfiguration updated successfully!")
        print(f"Updated {config_path} with Flashbots authentication key")
    else:
        print("\nWarning: Could not find configs/production.json")
        print("Please manually add the following to your configuration:")
        print(json.dumps({
            'flashbots': {
                'auth_key': private_key,
                'relay_url': 'https://relay.flashbots.net'
            }
        }, indent=2))

if __name__ == "__main__":
    print("Generating new Flashbots authentication key...")
    generate_flashbots_auth()