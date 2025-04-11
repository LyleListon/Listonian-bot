"""Base DEX interface for all DEX implementations."""  

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from web3 import Web3
from ..core.web3.web3_manager import Web3Manager # Import Web3Manager


class BaseDEX(ABC):
    """Abstract base class for DEX implementations."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]): # Change signature
        """Initialize base DEX."""
        self.web3_manager = web3_manager # Store the manager
        self.w3 = self.web3_manager.w3 # Keep self.w3 for compatibility
        self.config = config
        self.factory = None
        self.router = None
        # Add an id attribute based on config or class name for consistency
        self.id = config.get("id", self.__class__.__name__.lower())
        self.name = config.get("name", self.__class__.__name__)


    @abstractmethod
    async def initialize(self) -> bool: # Added abstract initialize method
        """Initialize the DEX asynchronously (e.g., load contracts)."""
        pass

    @abstractmethod
    async def get_pool_address(self, token_a: str, token_b: str, **kwargs) -> str:
        """Get pool address for token pair."""
        pass

    @abstractmethod
    async def get_reserves(self, pool_address: str) -> Tuple[Decimal, Decimal]:
        """Get token reserves from pool."""
        pass

    @abstractmethod
    async def get_amounts_out(
        self, amount_in: Decimal, path: List[str], **kwargs
    ) -> List[Decimal]:
        """Calculate output amounts for a given input amount and path."""
        pass

    @abstractmethod
    async def get_price_impact(
        self, amount_in: Decimal, amount_out: Decimal, pool_address: str
    ) -> float:
        """Calculate price impact for a trade."""
        pass

    @abstractmethod
    async def get_pool_fee(self, pool_address: str) -> Decimal:
        """Get pool trading fee."""
        pass

    @abstractmethod
    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """Get pool information including liquidity, volume, etc."""
        pass

    @abstractmethod
    async def validate_pool(self, pool_address: str) -> bool:
        """Validate pool exists and is active."""
        pass

    @abstractmethod
    async def estimate_gas(
        self,
        amount_in: Decimal,
        amount_out_min: Decimal,
        path: List[str],
        to: str,
        **kwargs,
    ) -> int:
        """Estimate gas cost for a trade."""
        pass

    @abstractmethod
    async def build_swap_transaction(
        self,
        amount_in: Decimal,
        amount_out_min: Decimal,
        path: List[str],
        to: str,
        deadline: int,
        **kwargs,
    ) -> Dict[str, Any]:
        """Build swap transaction."""
        pass

    @abstractmethod
    async def decode_swap_error(self, error: Exception) -> str:
        """Decode swap error into human readable message."""
        pass

    # --- Concrete Helper Methods ---

    async def get_token_decimals(self, token_address: str) -> int:
        """Get token decimals."""
        try:
            # Load ERC20 ABI
            # TODO: Consider loading ABIs once in __init__ or globally
            with open("abi/ERC20.json", "r") as f:
                import json
                erc20_abi = json.load(f)

            token_checksum = Web3.to_checksum_address(token_address)
            token = self.web3_manager.w3.eth.contract(address=token_checksum, abi=erc20_abi) # Use web3_manager
            # Web3.py contract calls don't need await for call()
            return token.functions.decimals().call()
        except Exception as e:
            # Log the error for better debugging
            # logger.error(f"Failed to get decimals for {token_address}: {e}", exc_info=True)
            raise ValueError(f"Failed to get decimals for {token_address}: {e}")

    def to_wei(self, amount: Decimal, decimals: int) -> int:
        """Convert decimal amount to wei amount."""
        if not isinstance(decimals, int) or decimals < 0:
            raise ValueError(f"Invalid decimals value: {decimals}")
        return int(amount * (Decimal(10)**decimals))

    def from_wei(self, amount: int, decimals: int) -> Decimal:
        """Convert wei amount to decimal amount."""
        if not isinstance(decimals, int) or decimals < 0:
            raise ValueError(f"Invalid decimals value: {decimals}")
        if decimals == 0:
            return Decimal(amount)
        return Decimal(amount) / (Decimal(10)**decimals)
