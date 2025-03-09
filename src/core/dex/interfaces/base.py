"""Base interface for DEX implementations."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional, Tuple

from web3.types import ChecksumAddress

from ...blockchain.web3_manager import Web3Manager
from .types import (
    DEXType,
    LiquidityInfo,
    PoolInfo,
    SwapParams,
    SwapQuote,
    Token,
    TokenAmount
)


class BaseDEX(ABC):
    """Abstract base class for DEX implementations."""

    def __init__(
        self,
        web3_manager: Web3Manager,
        factory_address: ChecksumAddress,
        router_address: ChecksumAddress,
        protocol: DEXType
    ):
        """Initialize DEX interface.
        
        Args:
            web3_manager: Web3 manager instance
            factory_address: DEX factory contract address
            router_address: DEX router contract address
            protocol: DEX protocol type
        """
        self.web3 = web3_manager
        self.factory_address = factory_address
        self.router_address = router_address
        self.protocol = protocol

    @abstractmethod
    async def get_pool(
        self,
        token0: Token,
        token1: Token
    ) -> Optional[PoolInfo]:
        """Get pool information for a token pair.
        
        Args:
            token0: First token
            token1: Second token
            
        Returns:
            PoolInfo if pool exists, None otherwise
        """
        pass

    @abstractmethod
    async def get_pools(self) -> List[PoolInfo]:
        """Get all available pools.
        
        Returns:
            List of pool information
        """
        pass

    @abstractmethod
    async def get_reserves(
        self,
        pool_address: ChecksumAddress
    ) -> LiquidityInfo:
        """Get current reserves for a pool.
        
        Args:
            pool_address: Pool contract address
            
        Returns:
            Current liquidity information
            
        Raises:
            ValueError: If pool doesn't exist
        """
        pass

    @abstractmethod
    async def get_quote(
        self,
        input_amount: TokenAmount,
        output_token: Token,
        path: Optional[List[ChecksumAddress]] = None
    ) -> SwapQuote:
        """Get quote for swapping tokens.
        
        Args:
            input_amount: Amount of input token
            output_token: Output token
            path: Optional specific path to use
            
        Returns:
            Swap quote with price impact
            
        Raises:
            ValueError: If no valid path exists
        """
        pass

    @abstractmethod
    async def get_price(
        self,
        base_token: Token,
        quote_token: Token
    ) -> Decimal:
        """Get current price between tokens.
        
        Args:
            base_token: Base token
            quote_token: Quote token
            
        Returns:
            Current price (quote per base)
            
        Raises:
            ValueError: If no valid path exists
        """
        pass

    @abstractmethod
    async def execute_swap(
        self,
        params: SwapParams
    ) -> str:
        """Execute a swap transaction.
        
        Args:
            params: Swap parameters
            
        Returns:
            Transaction hash
            
        Raises:
            ValueError: If swap validation fails
            Web3Error: If transaction fails
        """
        pass

    @abstractmethod
    async def find_best_path(
        self,
        input_token: Token,
        output_token: Token,
        amount: Optional[TokenAmount] = None
    ) -> Tuple[List[ChecksumAddress], Decimal]:
        """Find best path between tokens.
        
        Args:
            input_token: Input token
            output_token: Output token
            amount: Optional amount to optimize for
            
        Returns:
            Tuple of (path, expected output amount)
            
        Raises:
            ValueError: If no valid path exists
        """
        pass

    @abstractmethod
    async def validate_pool(
        self,
        pool_info: PoolInfo
    ) -> bool:
        """Validate pool health and status.
        
        Args:
            pool_info: Pool to validate
            
        Returns:
            True if pool is healthy and usable
        """
        pass

    @abstractmethod
    async def monitor_price(
        self,
        pool_address: ChecksumAddress,
        callback: callable
    ) -> None:
        """Monitor price changes for a pool.
        
        Args:
            pool_address: Pool to monitor
            callback: Function to call on price change
        """
        pass

    async def get_token(
        self,
        address: ChecksumAddress
    ) -> Token:
        """Get token information.
        
        Args:
            address: Token contract address
            
        Returns:
            Token information
            
        Raises:
            ValueError: If token contract is invalid
        """
        # Default implementation using ERC20 interface
        try:
            contract = self.web3.get_contract(address, 'ERC20')
            return Token(
                address=address,
                symbol=await contract.functions.symbol().call(),
                decimals=await contract.functions.decimals().call(),
                name=await contract.functions.name().call()
            )
        except Exception as e:
            raise ValueError(f"Invalid token contract: {e}")

    def __str__(self) -> str:
        return f"{self.protocol.name} DEX at {self.router_address}"