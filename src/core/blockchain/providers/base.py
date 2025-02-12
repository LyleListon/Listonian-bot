"""Base provider interface for blockchain interactions."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from web3 import AsyncWeb3
from web3.types import RPCEndpoint, RPCResponse

class BaseProvider(ABC):
    """Abstract base class for Web3 providers.
    
    This class defines the interface that all providers must implement,
    ensuring consistent behavior across different provider implementations.
    """

    def __init__(self, url: str, chain_id: int, retry_count: int = 3):
        """Initialize the provider.
        
        Args:
            url: RPC endpoint URL
            chain_id: Network chain ID
            retry_count: Number of retry attempts for failed requests
        """
        self.url = url
        self.chain_id = chain_id
        self.retry_count = retry_count
        self._web3: Optional[AsyncWeb3] = None

    @property
    def web3(self) -> AsyncWeb3:
        """Get the Web3 instance.
        
        Returns:
            AsyncWeb3: The initialized Web3 instance
            
        Raises:
            RuntimeError: If provider is not connected
        """
        if not self._web3:
            raise RuntimeError("Provider not connected")
        return self._web3

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the blockchain network.
        
        This method should:
        1. Initialize the Web3 connection
        2. Verify the connection
        3. Set up middleware
        4. Configure retry logic
        
        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the blockchain network.
        
        This method should:
        1. Close any open connections
        2. Clean up resources
        3. Reset internal state
        """
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if provider is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        pass

    @abstractmethod
    async def make_request(
        self,
        method: Union[RPCEndpoint, str],
        params: Optional[Any] = None
    ) -> RPCResponse:
        """Make an RPC request to the blockchain.
        
        Args:
            method: RPC method to call
            params: Parameters for the RPC call
            
        Returns:
            RPCResponse: Response from the RPC call
            
        Raises:
            Web3Error: If request fails
        """
        pass

    @abstractmethod
    async def get_block_number(self) -> int:
        """Get the current block number.
        
        Returns:
            int: Current block number
            
        Raises:
            Web3Error: If request fails
        """
        pass

    @abstractmethod
    async def get_gas_price(self) -> int:
        """Get the current gas price.
        
        Returns:
            int: Current gas price in wei
            
        Raises:
            Web3Error: If request fails
        """
        pass

    @abstractmethod
    async def estimate_gas(
        self,
        transaction: Dict[str, Any]
    ) -> int:
        """Estimate gas cost for a transaction.
        
        Args:
            transaction: Transaction parameters
            
        Returns:
            int: Estimated gas cost
            
        Raises:
            Web3Error: If estimation fails
        """
        pass