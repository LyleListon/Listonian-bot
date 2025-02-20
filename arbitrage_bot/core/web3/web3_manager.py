"""Web3 connection and interaction utilities with MCP integration."""

import logging
import os
import json
import pathlib
from typing import Dict, Any, Optional, List
from web3 import Web3
from web3.providers import HTTPProvider
from web3.exceptions import TimeExhausted
from eth_account import Account
from ...utils.mcp_helper import call_mcp_tool
from ...utils.secure_env import SecureEnvironment, init_secure_environment
from ...utils.config_loader import load_config

logger = logging.getLogger(__name__)

class Web3ConnectionError(Exception):
    """Custom exception for Web3 connection errors."""
    pass

class Web3Manager:
    """Manages Web3 connection and interactions."""

    def __init__(
        self, provider_url: Optional[str] = None, chain_id: Optional[int] = None
    ):
        """Initialize Web3 manager."""
        self.provider_url = provider_url
        self.chain_id = int(chain_id) if chain_id else None
        self._web3 = None
        self.secure_env = init_secure_environment()
        
        # Load wallet credentials from secure environment
        self.wallet_address = self.secure_env.secure_load("WALLET_ADDRESS")
        private_key = self.secure_env.secure_load("PRIVATE_KEY")
        
        # Add detailed logging for wallet address
        logger.info("="*50)
        logger.info("WALLET CONFIGURATION")
        logger.info("="*50)
        logger.info(f"Using wallet address: {self.wallet_address}")
        logger.info(f"Address checksum: {Web3.to_checksum_address(self.wallet_address) if self.wallet_address else None}")
        logger.debug("="*50)
        
        if not self.wallet_address:
            raise ValueError("WALLET_ADDRESS not found in secure environment")
        if not private_key:
            raise ValueError("PRIVATE_KEY not found in secure environment")
            
        # Add 0x prefix to private key if missing
        self._private_key = private_key if private_key.startswith("0x") else f"0x{private_key}"
            
        # Initialize account
        try:
            self._account = Account.from_key(self._private_key)
            if self._account.address.lower() != self.wallet_address.lower():
                logger.error(f"Private key address: {self._account.address}")
                logger.error(f"Configured wallet: {self.wallet_address}")
                raise ValueError("Private key does not match wallet address")
        except Exception as e:
            logger.error(f"Failed to initialize account: {e}")
            raise
            
        # Cache for ABIs
        self._abi_cache = {}
            
        logger.info(f"Initialized Web3 manager with account: {self.wallet_address}")

    @property
    def w3(self):
        return self._web3

    def connect(self):
        """Initialize Web3 connection."""
        try:
            # Get provider URL from environment or config
            if not self.provider_url:
                config = load_config()
                logger.debug(f"Loading RPC URL from config: {config.get('network', {}).get('rpc_url')}")
                rpc_url = config.get('network', {}).get('rpc_url')
                if rpc_url and rpc_url.startswith('$SECURE:'):
                    logger.debug(f"Found secure reference: {rpc_url}")
                    var_name = rpc_url.replace('$SECURE:', '')
                    logger.debug(f"Loading secure variable: {var_name}")
                    self.provider_url = self.secure_env.secure_load(var_name)
                    logger.debug(f"Loaded secure RPC URL: {self.provider_url}")
                    if not self.provider_url:
                        raise ValueError(f"Failed to load secure variable: {var_name}")
                else:
                    self.provider_url = rpc_url or os.getenv("BASE_RPC_URL")
                    
                if not self.provider_url:
                    raise ValueError("No RPC URL configured")

            if not isinstance(self.provider_url, str):
                raise ValueError(f"Invalid RPC URL type: {type(self.provider_url)}")

            if not self.provider_url.startswith(("http://", "https://")):
                raise ValueError("Invalid RPC URL format - must start with http:// or https://")

            # Create Web3 instance with HTTP provider
            provider = HTTPProvider(
                endpoint_uri=str(self.provider_url),
                request_kwargs={
                    "headers": {
                        "Content-Type": "application/json",
                        "User-Agent": "arbitrage_bot/1.0.0",
                    },
                    "timeout": 30,
                },
            )
            self._web3 = Web3(provider)

            # Test connection
            try:
                block_number = self._web3.eth.block_number
                logger.info(
                    f"Successfully connected to network. Current block: {block_number}"
                )

                if not self.chain_id:
                    try:
                        self.chain_id = int(os.getenv("CHAIN_ID", "8453"))
                    except ValueError as e:
                        raise ValueError("Invalid CHAIN_ID format - must be an integer") from e
                    
                # Set up account
                self._web3.eth.default_account = self._account.address
                
                # Test account setup
                balance = self._web3.eth.get_balance(self._account.address)
                logger.info(f"Account {self._account.address} balance: {self._web3.from_wei(balance, 'ether')} ETH")
                
            except Exception as e:
                logger.error(f"Connection test failed: {str(e)}")
                raise Web3ConnectionError(
                    f"Failed to connect to Web3 provider: {str(e)}"
                )

            logger.info(f"Connected to Web3 provider: {self.provider_url}")
            logger.info(f"Using account: {self._account.address}")
            logger.info(f"Chain ID: {self.chain_id}")

        except Exception as e:
            logger.error(f"Failed to initialize Web3: {e}")
            raise

    def build_contract_transaction(
        self, contract: Any, method_name: str, *args, tx_params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Build and sign a contract transaction using EIP-1559."""
        try:
            # Build the function call
            fn = getattr(contract.functions, method_name)
            fn_instance = fn(*args)

            # Get chain ID
            chain_id = self._web3.eth.chain_id

            # Get the next nonce
            nonce = self._web3.eth.get_transaction_count(self._account.address)

            # Start with base transaction parameters including any provided params
            base_params = {
                'from': self._account.address,
                'nonce': nonce
            }

            # Add any custom parameters
            if tx_params:
                base_params.update({k: v for k, v in tx_params.items() if v is not None})

            # If no gas parameters provided, use EIP-1559 defaults
            if 'maxFeePerGas' not in base_params or 'maxPriorityFeePerGas' not in base_params:
                latest_block = self._web3.eth.get_block('latest')
                base_fee = latest_block['baseFeePerGas']

                priority_fee = self._web3.eth.max_priority_fee
                max_fee_per_gas = (base_fee * 2) + priority_fee

                base_params['maxFeePerGas'] = base_params.get('maxFeePerGas', max_fee_per_gas)
                base_params['maxPriorityFeePerGas'] = base_params.get('maxPriorityFeePerGas', priority_fee)

            # Estimate gas if not provided
            if 'gas' not in base_params:
                gas_estimate = fn_instance.estimate_gas(base_params)
                base_params['gas'] = int(gas_estimate * 1.2)  # Add 20% buffer for safety

            # Build EIP-1559 transaction
            final_params = {
                'chainId': chain_id,
                **base_params,
                'to': contract.address,
                'data': fn_instance._encode_transaction_data(),
                'type': 2  # EIP-1559
            }

            # Add value if provided
            if 'value' in kwargs:
                final_params['value'] = kwargs['value']

            # Log transaction parameters
            logger.info(f"Built EIP-1559 transaction for {method_name}: {final_params}")
            
            # Sign the transaction
            signed_tx = self._web3.eth.account.sign_transaction(final_params, self._private_key)
            return signed_tx
            
        except Exception as e:
            logger.error(f"Failed to build contract transaction for {method_name}: {e}")
            raise

    def send_transaction(self, signed_tx) -> str:
        """Send a signed transaction and wait for receipt."""
        try:
            # Send the raw transaction
            tx_hash = self._web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            logger.info(f"Transaction sent: {tx_hash.hex()}")  # Keep this as INFO for transaction tracking
            
            # Wait for transaction receipt
            receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            if receipt['status'] != 1:
                raise Exception(f"Transaction failed: {receipt}")
                
            logger.info(f"Transaction confirmed in block {receipt['blockNumber']}")  # Keep this as INFO for transaction tracking
            return receipt
            
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise

    def build_and_send_transaction(
        self, contract: Any, method_name: str, *args, tx_params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> str:
        """Build, sign, and send a contract transaction with EIP-1559 support."""
        try:
            # Build and sign transaction
            signed_tx = self.build_contract_transaction(contract, method_name, *args, tx_params=tx_params, **kwargs)
            
            # Send transaction and get receipt
            receipt = self.send_transaction(signed_tx)
            
            logger.info(f"Transaction sent successfully: {receipt['transactionHash'].hex()}")  # Keep this as INFO for transaction tracking
            return receipt
            
        except Exception as e:
            logger.error(f"Failed to execute transaction {method_name}: {e}")
            raise

    def get_eth_balance(self) -> float:
        """Get ETH balance for the wallet address."""
        return self.get_balance(self.wallet_address)

    def get_balance(self, address: str) -> float:
        """Get ETH balance for address."""
        try:
            balance = self.w3.eth.get_balance(address)
            return self._web3.from_wei(balance, "ether")
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            raise

    def use_mcp_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Use an MCP tool through the client."""
        try:
            return call_mcp_tool(server_name, tool_name, arguments)
        except Exception as e:
            logger.error(f"Failed to use MCP tool {tool_name} on {server_name}: {e}")
            raise
            
    def get_network_id(self) -> int:
        """Get the network/chain ID."""
        if not self.chain_id:
            self.chain_id = self._web3.eth.chain_id
        return self.chain_id

    def get_token_decimals(self, token_address: str) -> int:
        """Get token decimals."""
        try:
            contract = self.get_token_contract(token_address)
            if not contract:
                logger.error(f"No contract found for token {token_address}")
                return 18  # Default to 18 decimals if contract not found
            
            decimals = contract.functions.decimals().call()
            return decimals
        except Exception as e:
            logger.error(f"Failed to get decimals for token {token_address}: {e}")
            return 18  # Default to 18 decimals on error

    def get_token_contract(self, token_address: str) -> Any:
        """Get token contract instance."""
        try:
            # Load ERC20 ABI if not in cache
            if 'ERC20' not in self._abi_cache:
                abi_path = pathlib.Path(__file__).parent.parent.parent.parent / 'abi' / 'ERC20.json'
                with open(abi_path) as f:
                    self._abi_cache['ERC20'] = json.load(f)

            # Create contract instance
            contract = self._web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=self._abi_cache['ERC20']
            )
            return contract
        except Exception as e:
            logger.error(f"Failed to get contract for token {token_address}: {e}")
            return None

def create_web3_manager(provider_url: Optional[str] = None, chain_id: Optional[int] = None) -> Web3Manager:
    """Create Web3Manager instance using environment variables."""
    try:
        # Get provider URL from config or environment if not provided
        if not provider_url:
            config = load_config()
            logger.debug(f"Loading RPC URL from config: {config.get('network', {}).get('rpc_url')}")
            rpc_url = config.get('network', {}).get('rpc_url')
            if rpc_url and rpc_url.startswith('$SECURE:'):
                logger.debug(f"Found secure reference: {rpc_url}")
                secure_env = init_secure_environment()
                var_name = rpc_url.replace('$SECURE:', '')
                logger.debug(f"Loading secure variable: {var_name}")
                provider_url = secure_env.secure_load(var_name)
            else:
                provider_url = rpc_url or os.getenv("BASE_RPC_URL")
            if not provider_url:
                raise ValueError("No RPC URL configured in config or environment")
            
        # Get chain ID from config or environment if not provided
        if not chain_id:
            config = load_config()
            chain_id = config.get('network', {}).get('chainId') or int(os.getenv("CHAIN_ID", "8453"))
            if not isinstance(chain_id, int):
                raise ValueError(f"Invalid chain ID format: {chain_id}")

        if not provider_url.startswith(("http://", "https://")):
            raise ValueError("Invalid RPC URL format - must start with http:// or https://")
        
        # Create manager with primary RPC URL
        manager = Web3Manager(provider_url=provider_url, chain_id=chain_id)
        
        try:
            logger.info("Connecting Web3Manager...")
            manager.connect()  # Ensure connection is established
            return manager
        except Exception as primary_error:
            # If primary RPC fails, try backup
            backup_url = os.getenv("BACKUP_RPC_URL")
            if backup_url:
                logger.warning(f"Primary RPC failed: {primary_error}. Trying backup RPC...")
                
                if not backup_url.startswith(("http://", "https://")):
                    logger.error("Invalid backup RPC URL format")
                    raise primary_error
                
                manager = Web3Manager(provider_url=backup_url, chain_id=chain_id)
                logger.info("Connecting Web3Manager with backup URL...")
                manager.connect()  # Ensure connection is established
                return manager
            else:
                raise primary_error
                
    except Exception as e:
        logger.error(f"Failed to create Web3Manager: {e}")
        raise
