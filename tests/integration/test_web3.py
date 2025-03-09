from web3 import Web3
from arbitrage_bot.utils.secure_env import init_secure_environment
import os

def test_wallet_connection():
    print("Initializing secure environment...")
    secure_env = init_secure_environment()
    
    # Get RPC URL and wallet credentials from secure storage
    rpc_url = os.getenv('BASE_RPC_URL')
    wallet_address = os.getenv('WALLET_ADDRESS')
    
    print(f"\nConnecting to Base network...")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print("❌ Failed to connect to Base network")
        return
    
    print("✓ Connected to Base network")
    
    # Check wallet balance
    balance = w3.eth.get_balance(wallet_address)
    eth_balance = w3.from_wei(balance, 'ether')
    
    print(f"\nWallet Status:")
    print(f"Address: {wallet_address}")
    print(f"Balance: {eth_balance:.4f} ETH")
    
    # Check network
    chain_id = w3.eth.chain_id
    print(f"Chain ID: {chain_id} (Base)")
    
    print("\n✅ Wallet connection test complete!")

if __name__ == "__main__":
    test_wallet_connection()