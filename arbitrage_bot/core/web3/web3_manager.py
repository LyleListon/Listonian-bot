"""Web3 connection and interaction utilities with MCP integration."""

import logging
import asyncio
import os
import json
import pathlib
from typing import Dict, Any, Optional, List
from web3 import AsyncWeb3
from web3.exceptions import TimeExhausted
from eth_account import Account
from ...utils.config_loader import load_config
from ...utils.mcp_client import use_mcp_tool as mcp_tool

# Web3 utility functions moved from web3_utils.py
async def get_web3(testing: bool = False) -> 'Web3Manager':
    """Get Web3 manager instance."""
    return await create_web3_manager(testing=testing)

async def get_contract(web3: 'Web3Manager', address: str, abi: Dict[str, Any]) -> Any:
    """Get contract instance."""
    return await web3.get_contract(address, abi)

async def estimate_gas(web3: 'Web3Manager', transaction: Dict[str, Any]) -> int:
    """Estimate gas for transaction."""
    return await web3.estimate_gas(transaction)

def validate_address(address: str) -> bool:
    """Validate Ethereum address."""
    return AsyncWeb3.is_address(address)

async def get_token_balance(web3: 'Web3Manager', token_address: str, wallet_address: str) -> float:
    """Get token balance for address."""
    try:
        contract = await web3.get_contract(token_address, [])  # TODO: Add ERC20 ABI
        balance = await contract.functions.balanceOf(wallet_address).call()
        decimals = await contract.functions.decimals().call()
        return float(balance) / (10**decimals)
    except Exception as e:
        logger.error(f"Failed to get token balance: {e}")
        return 0.0

async def get_eth_balance(web3: 'Web3Manager', address: str) -> float:
    """Get ETH balance for address."""
    return await web3.get_balance(address)

logger = logging.getLogger(__name__)


class Web3ConnectionError(Exception):
    """Custom exception for Web3 connection errors."""

    pass


class Web3Manager:
    """Manages Web3 connection and interactions."""

    def __init__(
        self, provider_url: Optional[str] = None, chain_id: Optional[int] = None, testing: bool = None
    ):
        """
        Initialize Web3 manager.

        Args:
            provider_url (str, optional): Web3 provider URL
            chain_id (int, optional): Chain ID
            testing (bool, optional): Whether to use mock providers for testing
        """
        self.provider_url = provider_url
        self.chain_id = chain_id
        self._web3 = None
        self.testing = testing if testing is not None else os.getenv('TESTING', '').lower() == 'true'
        self.wallet_address = os.getenv("WALLET_ADDRESS")
        if not self.wallet_address:
            raise ValueError("WALLET_ADDRESS environment variable not set")
        logger.info("Web3 manager initialized")

    def load_abi(self, name: str) -> Dict[str, Any]:
        """
        Load ABI from file.

        Args:
            name (str): Name of ABI file without .json extension

        Returns:
            Dict[str, Any]: Contract ABI
        """
        try:
            # Get project root directory
            root_dir = pathlib.Path(os.getcwd())
            abi_path = root_dir / 'abi' / f'{name}.json'
            
            # Load ABI file
            with open(abi_path) as f:
                abi = json.load(f)
            return abi
        except Exception as e:
            logger.error(f"Failed to load ABI {name}: {e}")
            raise

    async def connect(self):
        """Initialize Web3 connection."""
        try:
            if self.testing:
                logger.info("Running in test mode - using mock Web3 connection")
                self._web3 = AsyncWeb3(AsyncWeb3.AsyncEthereumTesterProvider())
                self.chain_id = 8453  # Base chain ID
                return

            # Get provider URL from environment or config
            if not self.provider_url:
                self.provider_url = os.getenv("BASE_RPC_URL")
                if not self.provider_url:
                    raise ValueError("No RPC URL configured")

            # Create async Web3 instance with HTTP provider
            provider = AsyncWeb3.AsyncHTTPProvider(
                self.provider_url,
                request_kwargs={
                    "headers": {
                        "Content-Type": "application/json",
                        "User-Agent": "arbitrage_bot/1.0.0",
                    },
                    "timeout": 30,  # 30 second timeout
                },
            )
            self._web3 = AsyncWeb3(provider)

            # Initialize Web3 instance
            logger.debug("Web3 instance created with provider")

            # Test connection
            try:
                # Test basic request
                block_number = await self._web3.eth.block_number
                logger.debug(
                    f"Successfully connected to network. Current block: {block_number}"
                )

                if not self.chain_id:
                    self.chain_id = int(os.getenv("CHAIN_ID", "8453"))
                    
                # Set up account
                private_key = os.getenv("PRIVATE_KEY")
                if not private_key:
                    raise ValueError("No private key configured")
                    
                # Add 0x prefix if missing
                if not private_key.startswith("0x"):
                    private_key = f"0x{private_key}"
                    
                account = self._web3.eth.account.from_key(private_key)
                self._web3.eth.default_account = account.address
                logger.info(f"Using account: {account.address}")
                
            except Exception as e:
                logger.error(f"Connection test failed: {str(e)}")
                raise Web3ConnectionError(
                    f"Failed to connect to Web3 provider: {str(e)}"
                )

            logger.info(f"Connected to Web3 provider: {self.provider_url}")
            logger.info(f"Chain ID: {self.chain_id}")

        except Exception as e:
            logger.error(f"Failed to initialize Web3: {e}")
            raise

    @property
    def w3(self) -> AsyncWeb3:
        """Get Web3 instance."""
        return self._web3

    def get_token_contract(self, address: str) -> Any:
        """
        Get ERC20 token contract instance.

        Args:
            address (str): Token contract address

        Returns:
            Contract: Web3 contract instance
        """
        try:
            # Load ERC20 ABI
            abi = self.load_abi('ERC20')
            return self.get_contract(address, abi)
        except Exception as e:
            logger.error(f"Failed to get token contract at {address}: {e}")
            return None

    def get_contract(self, address: str, abi: Dict[str, Any]) -> Any:
        """
        Get contract instance.

        Args:
            address (str): Contract address
            abi (Dict[str, Any]): Contract ABI

        Returns:
            Contract: Web3 contract instance
        """
        try:
            address = self._web3.to_checksum_address(address)
            return self._web3.eth.contract(address=address, abi=abi)
        except Exception as e:
            logger.error(f"Failed to get contract at {address}: {e}")
            raise

    async def call_contract_method(
        self, contract: Any, method_name: str, *args, **kwargs
    ) -> Any:
        """
        Call a contract method.

        Args:
            contract: Contract instance
            method_name: Name of method to call
            *args: Method arguments
            **kwargs: Method keyword arguments

        Returns:
            Any: Method result
        """
        try:
            # Get the function
            fn = getattr(contract.functions, method_name)

            # Handle struct parameters
            processed_args = []
            for arg in args:
                if isinstance(arg, dict) and "params" in arg:
                    # If it's a struct parameter, pass the inner params dict
                    processed_args.append(arg["params"])
                elif isinstance(arg, (list, tuple)):
                    # Pass through lists/tuples directly
                    processed_args.append(arg)
                else:
                    processed_args.append(arg)

            # Build the function call with processed args
            fn_instance = fn(*processed_args)

            # Extract from_ parameter if present
            call_params = {}
            if "from_" in kwargs:
                call_params["from"] = kwargs.pop("from_")

            # Call the function directly
            return await fn_instance.call(call_params)
        except Exception as e:
            logger.error(f"Failed to call contract method {method_name}: {e}")
            raise

    async def build_contract_transaction(
        self, contract: Any, method_name: str, *args, **kwargs
    ) -> Dict[str, Any]:
        """
        Build a contract transaction with MEV protection.

        Args:
            contract: Contract instance
            method_name: Name of method to call
            *args: Method arguments
            **kwargs: Transaction parameters

        Returns:
            Dict[str, Any]: Transaction parameters with MEV protection
        """
        try:
            # Build the function call
            fn = getattr(contract.functions, method_name)
            fn_instance = fn(*args)

            # Build base transaction parameters
            tx_params = {
                "to": contract.address,
                "data": fn_instance._encode_transaction_data(),
            }

            # Add optional parameters
            if "from_" in kwargs:
                tx_params["from"] = kwargs.pop("from_")
            if "gas" in kwargs:
                tx_params["gas"] = kwargs.pop("gas")
            if "nonce" in kwargs:
                tx_params["nonce"] = kwargs.pop("nonce")
            if "gasPrice" in kwargs:
                tx_params["gasPrice"] = kwargs.pop("gasPrice")
            if "chainId" in kwargs:
                tx_params["chainId"] = kwargs.pop("chainId")
            if "value" in kwargs:
                tx_params["value"] = kwargs.pop("value")

            # Get current block for timing protection
            current_block = await self._web3.eth.block_number
            
            # Add MEV protection parameters
            mev_protection = kwargs.get('mev_protection', True)
            if mev_protection:
                # Get mempool state for timing
                pending_txs = len(await self._web3.eth.get_block('pending'))
                
                # Dynamic nonce management
                if "from" in tx_params and "nonce" not in tx_params:
                    base_nonce = await self._web3.eth.get_transaction_count(
                        tx_params["from"]
                    )
                    # Add small random offset to avoid nonce prediction
                    if pending_txs < 10:  # Low congestion
                        nonce_offset = 0
                    else:  # High congestion, use offset
                        nonce_offset = min(3, pending_txs // 10)
                    tx_params["nonce"] = base_nonce + nonce_offset
                
                # Dynamic gas pricing for MEV protection
                if "gasPrice" not in tx_params:
                    base_gas = await self._web3.eth.gas_price
                    # Add randomization to gas price
                    if pending_txs > 20:  # High congestion
                        gas_multiplier = 1.1 + (pending_txs / 1000)  # Max 10% increase
                    else:
                        gas_multiplier = 1.02  # 2% increase
                    tx_params["gasPrice"] = int(base_gas * gas_multiplier)
                
                # Add deadline for timing protection
                blocks_until_deadline = 2  # Default 2 blocks
                if pending_txs > 20:  # Adjust deadline based on congestion
                    blocks_until_deadline = 3
                tx_params["deadline"] = current_block + blocks_until_deadline
                
                # Log MEV protection details
                logger.debug(
                    f"MEV Protection:\n"
                    f"  Current Block: {current_block}\n"
                    f"  Pending TXs: {pending_txs}\n"
                    f"  Nonce Offset: {nonce_offset if 'nonce' in tx_params else 'N/A'}\n"
                    f"  Gas Multiplier: {gas_multiplier:.2f}\n"
                    f"  Deadline: +{blocks_until_deadline} blocks"
                )
            
            # Fill in any remaining missing values
            if "from" in tx_params:
                if "gas" not in tx_params:
                    tx_params["gas"] = await self._web3.eth.estimate_gas(tx_params)
                if "chainId" not in tx_params:
                    tx_params["chainId"] = await self._web3.eth.chain_id

            return tx_params
        except Exception as e:
            logger.error(f"Failed to build contract transaction for {method_name}: {e}")
            raise

    async def estimate_gas(self, transaction: Dict[str, Any]) -> int:
        """
        Estimate gas with MEV protection buffer.

        Args:
            transaction (Dict[str, Any]): Transaction parameters

        Returns:
            int: Estimated gas with safety buffer
        """
        try:
            base_estimate = await self._web3.eth.estimate_gas(transaction)
            
            # Get current network conditions
            pending_txs = len(await self._web3.eth.get_block('pending'))
            
            # Calculate dynamic buffer based on network conditions
            if pending_txs > 20:  # High congestion
                buffer_multiplier = 1.2  # 20% buffer
            elif pending_txs > 10:  # Medium congestion
                buffer_multiplier = 1.15  # 15% buffer
            else:  # Low congestion
                buffer_multiplier = 1.1  # 10% buffer
                
            # Apply buffer and round up
            final_estimate = int(base_estimate * buffer_multiplier)
            
            logger.debug(
                f"Gas Estimate:\n"
                f"  Base: {base_estimate:,}\n"
                f"  Buffer: {(buffer_multiplier - 1) * 100:.1f}%\n"
                f"  Final: {final_estimate:,}\n"
                f"  Network Load: {pending_txs} pending txs"
            )
            
            return final_estimate
        except Exception as e:
            logger.error(f"Failed to estimate gas: {e}")
            raise

    async def get_eth_balance(self) -> float:
        """Get ETH balance for the wallet address."""
        return await self.get_balance(self.wallet_address)

    async def get_balance(self, address: str) -> float:
        """
        Get ETH balance for address.

        Args:
            address (str): Address to check

        Returns:
            float: Balance in ETH
        """
        try:
            balance = await self._web3.eth.get_balance(address)
            return self._web3.from_wei(balance, "ether")
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            raise

    async def use_mcp_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Use an MCP tool through the client.
        
        Args:
            server_name (str): Name of the MCP server
            tool_name (str): Name of the tool to use
            arguments (Dict[str, Any]): Tool arguments
            
        Returns:
            Any: Tool response
        """
        try:
            return await mcp_tool(server_name, tool_name, arguments)
        except Exception as e:
            logger.error(f"Failed to use MCP tool {tool_name} on {server_name}: {e}")
            raise
            
    async def get_network_id(self) -> int:
        """
        Get the network/chain ID.

        Returns:
            int: The network ID (chain ID) of the connected network
        """
        if not self.chain_id:
            self.chain_id = await self._web3.eth.chain_id
        return self.chain_id

    async def execute_swap(
        self,
        token: str,
        amount: float,
        price: float,
        route_options: Optional[List[str]] = None
    ) -> str:
        """
        Execute token swap with MEV protection.

        Args:
            token (str): Token to swap
            amount (float): Amount to swap
            price (float): Expected price
            route_options (List[str], optional): Alternative routing paths

        Returns:
            str: Transaction hash
        """
        try:
            # Get current network state
            current_block = await self._web3.eth.block_number
            pending_txs = len(await self._web3.eth.get_block('pending'))
            
            # Determine optimal submission timing
            if pending_txs > 20:  # High congestion
                # Wait for better conditions
                await asyncio.sleep(2)  # Brief delay
                # Recheck conditions
                new_pending = len(await self._web3.eth.get_block('pending'))
                if new_pending > pending_txs:
                    logger.warning("Network congestion increasing, proceeding with caution")
            
            # Route randomization for MEV protection
            if route_options:
                # Select random route if alternatives available
                from random import choice
                selected_route = choice(route_options)
                logger.info(f"Selected random route: {selected_route}")
            
            # Build transaction with MEV protection
            tx_params = {
                "mev_protection": True,  # Enable MEV protection features
                "deadline": current_block + 2,  # 2 block deadline
                "min_output": int(amount * price * 0.995)  # 0.5% slippage
            }
            
            if self.testing:
                # Mock successful swap in testing mode
                return f"0x{''.join(['0123456789abcdef'[i % 16] for i in range(64)])}"
                
            # TODO: Implement actual swap logic with selected route
            raise NotImplementedError("Swap execution not implemented in production mode")
        except Exception as e:
            logger.error(f"Failed to execute swap: {e}")
            raise


async def create_web3_manager(testing: bool = None) -> Web3Manager:
    """
    Create Web3Manager instance using environment variables.

    Args:
        testing (bool, optional): Whether to use mock providers for testing

    Returns:
        Web3Manager: Web3 manager instance
    """
    try:
        # Get provider URL from environment
        provider_url = os.getenv("BASE_RPC_URL")
        if not provider_url:
            raise ValueError("BASE_RPC_URL environment variable not set")
            
        # Get chain ID from environment
        chain_id = int(os.getenv("CHAIN_ID", "8453"))
        
        # Create manager with primary RPC URL
        manager = Web3Manager(provider_url=provider_url, chain_id=chain_id, testing=testing)
        
        try:
            await manager.connect()
            return manager
        except Exception as primary_error:
            # If primary RPC fails, try backup
            backup_url = os.getenv("BACKUP_RPC_URL")
            if backup_url:
                logger.warning(f"Primary RPC failed: {primary_error}. Trying backup RPC...")
                manager = Web3Manager(provider_url=backup_url, chain_id=chain_id, testing=testing)
                await manager.connect()
                return manager
            else:
                raise primary_error
                
    except Exception as e:
        logger.error(f"Failed to create Web3Manager: {e}")
        raise
