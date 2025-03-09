"""
Initialize secure environment with configuration values and wallet credentials
"""
import json
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from arbitrage_bot.utils.secure_env import SecureEnvironment

def validate_environment():
    """Validate required environment variables and files"""
    required_files = [
        ('.env.production', 'Copy .env.production.template to .env.production and fill in your values'),
        ('configs/config.json', 'Ensure config.json exists with your network settings'),
        ('configs/wallet_config.json', 'Ensure wallet_config.json exists with your wallet settings')
    ]

    for file_path, message in required_files:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Missing {file_path}: {message}")

    # Create secure directory if it doesn't exist
    Path('secure').mkdir(exist_ok=True)


def init_secure_storage():
    """Initialize secure environment with encrypted storage"""
    try:
        # Validate environment
        validate_environment()

        # Load environment variables from .env.production
        load_dotenv(dotenv_path=os.path.abspath('.env.production'))

        # Initialize secure environment
        secure_env = SecureEnvironment()

        # Load secure environment variables
        secure_env.load_secure_env()
        
        # Store the actual private key and wallet address
        wallet_address = Web3.to_checksum_address(os.getenv('WALLET_ADDRESS'))
        private_key = os.getenv('PRIVATE_KEY')  # Added 0x prefix
        profit_recipient = Web3.to_checksum_address(os.getenv('PROFIT_RECIPIENT'))

        print("\nStoring credentials:")
        print(f"Wallet Address: {wallet_address}")
        print(f"Private Key: {private_key}")
        print(f"Profit Recipient: {profit_recipient}")

        # Store credentials securely
        print("\nSecuring sensitive data...")
        secure_env.secure_store('WALLET_ADDRESS', wallet_address)
        secure_env.secure_store('PRIVATE_KEY', private_key)
        secure_env.secure_store('PROFIT_RECIPIENT', profit_recipient)

        # Verify stored values
        print("\nVerifying stored values:")
        stored_address = secure_env.secure_load('WALLET_ADDRESS')
        stored_key = secure_env.secure_load('PRIVATE_KEY')
        stored_recipient = secure_env.secure_load('PROFIT_RECIPIENT')
        print(f"Stored Wallet Address: {stored_address}")
        print(f"Stored Private Key: {stored_key}")
        print(f"Stored Profit Recipient: {stored_recipient}")

        # Store Alchemy API key
        alchemy_api_key = os.getenv('ALCHEMY_API_KEY')
        secure_env.secure_store('ALCHEMY_API_KEY', alchemy_api_key)

        # Store RPC URL
        base_rpc_url = f"https://base-mainnet.g.alchemy.com/v2/{alchemy_api_key}"
        secure_env.secure_store('BASE_RPC_URL', base_rpc_url)

        # Update config files to use secure references
        config_path = 'configs/config.json'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Update config to use secure references
            if 'network' in config:
                config['network']['rpc_url'] = '$SECURE:BASE_RPC_URL'
            if 'wallet' in config:
                config['wallet']['wallet_address'] = '$SECURE:WALLET_ADDRESS'
                config['wallet']['profit_recipient'] = '$SECURE:PROFIT_RECIPIENT'

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)

        # Update wallet config
        wallet_config_path = 'configs/wallet_config.json'
        if os.path.exists(wallet_config_path):
            # Backup original
            shutil.copy(wallet_config_path, 'configs/wallet_config.json.bak')

            # Update with secure references
            wallet_config = {
                'address': '$SECURE:WALLET_ADDRESS',
                'private_key': '$SECURE:PRIVATE_KEY'
            }
            with open(wallet_config_path, 'w') as f:
                json.dump(wallet_config, f, indent=4)

        print("\n✅ Secure environment initialized successfully!")
        print("\nNotes:")
        print("- Sensitive data is now encrypted in the 'secure' directory")
        print("- Config files have been updated to use secure references")
        print("- Original wallet_config.json backed up as wallet_config.json.bak")
        print("\nYou can now safely commit the config files without exposing sensitive data.")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise


if __name__ == "__main__":
    init_secure_storage()
