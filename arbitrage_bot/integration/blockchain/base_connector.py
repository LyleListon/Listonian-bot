"""Base connector for blockchain integrations."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class BaseBlockchainConnector(ABC):
    """Base class for blockchain connectors."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize the blockchain connector.
        
        Args:
            name: Name of the blockchain network.
            config: Configuration dictionary.
        """
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)
        self.chain_id = config.get("chain_id")
        self.rpc_url = config.get("rpc_url")
        self.ws_url = config.get("ws_url")
        self.explorer_url = config.get("explorer_url")
        
        logger.info(f"Initialized {name} blockchain connector")
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the blockchain.
        
        Returns:
            True if connection is successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the blockchain."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to the blockchain.
        
        Returns:
            True if connected, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_latest_block_number(self) -> int:
        """Get the latest block number.
        
        Returns:
            The latest block number.
        """
        pass
    
    @abstractmethod
    def get_block(self, block_number: int) -> Dict[str, Any]:
        """Get a block by number.
        
        Args:
            block_number: The block number.
            
        Returns:
            Block information.
        """
        pass
    
    @abstractmethod
    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get a transaction by hash.
        
        Args:
            tx_hash: The transaction hash.
            
        Returns:
            Transaction information.
        """
        pass
    
    @abstractmethod
    def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Get a transaction receipt by hash.
        
        Args:
            tx_hash: The transaction hash.
            
        Returns:
            Transaction receipt information.
        """
        pass
    
    @abstractmethod
    def get_balance(self, address: str, token_address: Optional[str] = None) -> float:
        """Get the balance of an address.
        
        Args:
            address: The address to check.
            token_address: The token address. If None, gets the native token balance.
            
        Returns:
            The balance.
        """
        pass
    
    @abstractmethod
    def get_gas_price(self) -> int:
        """Get the current gas price.
        
        Returns:
            The gas price in wei.
        """
        pass
    
    @abstractmethod
    def estimate_gas(self, tx: Dict[str, Any]) -> int:
        """Estimate the gas required for a transaction.
        
        Args:
            tx: The transaction parameters.
            
        Returns:
            The estimated gas.
        """
        pass
    
    @abstractmethod
    def send_transaction(self, tx: Dict[str, Any]) -> str:
        """Send a transaction.
        
        Args:
            tx: The transaction parameters.
            
        Returns:
            The transaction hash.
        """
        pass
    
    @abstractmethod
    def wait_for_transaction_receipt(
        self, tx_hash: str, timeout: int = 120, poll_interval: float = 0.1
    ) -> Dict[str, Any]:
        """Wait for a transaction receipt.
        
        Args:
            tx_hash: The transaction hash.
            timeout: The timeout in seconds.
            poll_interval: The poll interval in seconds.
            
        Returns:
            The transaction receipt.
        """
        pass
    
    @abstractmethod
    def call_contract(
        self,
        contract_address: str,
        function_name: str,
        function_args: List[Any],
        abi: List[Dict[str, Any]],
    ) -> Any:
        """Call a contract function.
        
        Args:
            contract_address: The contract address.
            function_name: The function name.
            function_args: The function arguments.
            abi: The contract ABI.
            
        Returns:
            The function result.
        """
        pass
