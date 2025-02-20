import os
import json
from web3 import Web3
from eth_account.account import Account
from eth_utils import to_bytes
from eth_utils import to_hex
from web3.types import TxParams, Wei
from hexbytes import HexBytes
from typing import cast
from eth_utils.toolz import assoc

def test_basic_transaction():
    try:
        # Direct configuration
        wallet_address = Web3.to_checksum_address("0x257a30645bF0C91BC155bd9C01BD722322050F7b")
        private_key = "0x5127c66bfc607750f5bd309d45ab922255c514d3607b7ff8507f44e73f64dc0d"  # Corrected key
        rpc_url = "https://base-mainnet.g.alchemy.com/v2/kRXhWVt8YU_8LnGS20145F5uBDFbL_k0"
        chain_id = 8453  # Base network
        
        # Initialize Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Verify network connection
        print("\nVerifying network connection...")
        if not w3.is_connected():
            raise Exception("Failed to connect to Base network")
            
        network_version = w3.eth.chain_id
        print(f"Connected to network with chain ID: {network_version}")
        if network_version != chain_id:
            raise Exception(f"Wrong network! Expected chain ID {chain_id}, got {network_version}")
        
        # Initialize account
        account = w3.eth.account.from_key(private_key)
        account_address = Web3.to_checksum_address(account.address)
        print(f"\nAccount Details:")
        print(f"Address: {account_address}")
        print(f"Matches expected: {account_address.lower() == wallet_address.lower()}")
        
        if account_address.lower() != wallet_address.lower():
            print("\nError: Account address doesn't match expected wallet!")
            return False
            
        # Get balance
        balance = w3.eth.get_balance(account_address)
        balance_eth = w3.from_wei(balance, 'ether')
        balance_wei = balance
        print(f"Balance: {balance_eth:.6f} ETH")
        print(f"Balance in Wei: {balance_wei}")
        
        # Get latest block info
        latest_block = w3.eth.get_block('latest')
        print(f"\nLatest block info:")
        print(f"Block number: {latest_block['number']}")
        print(f"Gas limit: {latest_block['gasLimit']}")
        print(f"Gas used: {latest_block['gasUsed']}")
        
        # Prepare transaction
        print("\nPreparing transaction...")
        nonce = w3.eth.get_transaction_count(account_address)
        
        # Get gas price
        gas_price = w3.eth.gas_price
        print(f"Current gas price: {w3.from_wei(gas_price, 'gwei')} gwei")
        
        # Build transaction
        transaction = {
            'nonce': nonce,
            'gasPrice': gas_price,
            'gas': 21000,
            'to': account_address,
            'value': 0,
            'data': '0x',
            'chainId': chain_id
        }
        
        # Calculate transaction cost
        tx_cost = transaction['gasPrice'] * transaction['gas']
        print(f"\nTransaction Cost Analysis:")
        print(f"Gas Price: {w3.from_wei(gas_price, 'gwei')} gwei")
        print(f"Gas Limit: {transaction['gas']}")
        print(f"Total Cost: {w3.from_wei(tx_cost, 'ether')} ETH")
        print(f"Total Cost in Wei: {tx_cost}")
        print(f"Available Balance: {w3.from_wei(balance_wei, 'ether')} ETH")
        
        if tx_cost > balance_wei:
            raise Exception(f"Insufficient funds. Need {w3.from_wei(tx_cost, 'ether')} ETH, have {w3.from_wei(balance_wei, 'ether')} ETH")
        
        print("\nTransaction Parameters:")
        print(json.dumps({
            **transaction,
            'gasPrice': str(transaction['gasPrice']),
            'value': str(transaction['value']),
            'data': '0x'
        }, indent=2))
        
        # Sign transaction
        print("\nSigning transaction...")
        signed = w3.eth.account.sign_transaction(transaction, private_key)
        print("Transaction signed successfully")
        
        # Send transaction
        print("\nSending transaction...")
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction if hasattr(signed, 'rawTransaction') else signed.raw_transaction)
        print(f"Transaction sent!")
        print(f"Transaction Hash: {tx_hash.hex()}")
        
        # Wait for receipt
        print("\nWaiting for receipt...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        print(f"Transaction confirmed in block {receipt['blockNumber']}")
        print(f"Gas Used: {receipt['gasUsed']}")
        print(f"Status: {'Success' if receipt['status'] == 1 else 'Failed'}")
        
        return True
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing basic transaction...")
    test_basic_transaction()