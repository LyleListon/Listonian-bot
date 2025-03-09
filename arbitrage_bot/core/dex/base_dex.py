"""Base DEX abstract class providing common functionality."""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, TypeVar, Union
from decimal import Decimal
from web3 import Web3
from ..web3.web3_manager import Web3Manager

class BaseDEX(ABC):
    """Abstract base class for DEX implementations."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize base DEX functionality."""
        self.web3_manager = web3_manager
        self.config = config
        self.router_address = Web3.to_checksum_address(config['router'])
        self.factory_address = Web3.to_checksum_address(config['factory'])
        self.weth_address = Web3.to_checksum_address(config['weth_address'])
        self.router = None
        self.factory = None
        self.initialized = False
        self.name = config.get('name', self.__class__.__name__)
        self.enabled = config.get('enabled', True)
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the DEX interface."""
        pass

    async def is_enabled(self) -> bool:
        """Check if DEX is enabled."""
        return bool(self.enabled)

    def get_method_signatures(self) -> Dict[str, str]:
        """Get method signatures for the DEX."""
        return {}
        
    def get_router_address(self) -> str:
        """Get router address."""
        return self.router_address

    async def get_supported_tokens(self) -> List[str]:
        """Get list of supported tokens."""
        # Return tokens from config
        return list(self.config.get('tokens', {}).keys())
        
    async def _retry_async(
        self,
        func: Callable,
        *args,
        retries: int = 3,
        delay: float = 1.0,
        **kwargs
    ) -> Any:
        """Retry an async function with exponential backoff."""
        for i in range(retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if i == retries - 1:
                    raise
                await asyncio.sleep(delay * (2 ** i))
                continue
        raise RuntimeError("Max retries exceeded")

    def _validate_state(self):
        """Validate DEX state."""
        if not self.initialized:
            raise RuntimeError("DEX not initialized")
        if not self.router:
            raise RuntimeError("Router not initialized")
        if not self.factory:
            raise RuntimeError("Factory not initialized")

    def _validate_path(self, path: List[str]):
        """Validate token path."""
        if not path or len(path) < 2:
            raise ValueError("Invalid path: must contain at least 2 tokens")
        for token in path:
            if not Web3.is_address(token):
                raise ValueError("Invalid token address in path: %s" % token)

    def _validate_amounts(self, amount_in: int, amount_out_min: int):
        """Validate swap amounts."""
        if amount_in <= 0:
            raise ValueError("Invalid amount_in: must be positive")
        if amount_out_min <= 0:
            raise ValueError("Invalid amount_out_min: must be positive")

    def _handle_error(self, error: Exception, context: str):
        """Handle and log errors."""
        self.logger.error("Failed to %s: %s", context, str(error))
        raise

    def _log_transaction(
        self,
        tx_hash: str,
        amount_in: int,
        amount_out: int,
        path: List[str],
        recipient: str
    ):
        """Log transaction details."""
        self.logger.info(
            "Transaction %s: Swapped %d %s for %d %s to %s",
            tx_hash,
            amount_in,
            path[0],
            amount_out,
            path[-1],
            recipient
        )

    async def _get_token_decimals(self, token_address: str) -> int:
        """Get token decimals."""
        try:
            token = await self.web3_manager.get_token_contract(token_address)
            if not token:
                return 18  # Default to 18 decimals

            contract_func = token.functions.decimals()
            result = await self.web3_manager.call_contract_function(contract_func)
            if isinstance(result, str):
                return int(result)
            return int(result)

        except Exception as e:
            self.logger.error("Failed to get token decimals: %s", str(e))
            return 18  # Default to 18 decimals

    async def _get_token_symbol(self, token_address: str) -> str:
        """Get token symbol."""
        try:
            token = await self.web3_manager.get_token_contract(token_address)
            if not token:
                return token_address[:8]  # Return truncated address if contract not found

            contract_func = token.functions.symbol()
            result = await self.web3_manager.call_contract_function(contract_func)
            return str(result)

        except Exception as e:
            self.logger.error("Failed to get token symbol: %s", str(e))
            return token_address[:8]  # Return truncated address on error

    async def _get_token_name(self, token_address: str) -> str:
        """Get token name."""
        try:
            token = await self.web3_manager.get_token_contract(token_address)
            if not token:
                return token_address  # Return address if contract not found

            contract_func = token.functions.name()
            result = await self.web3_manager.call_contract_function(contract_func)
            return str(result)

        except Exception as e:
            self.logger.error("Failed to get token name: %s", str(e))
            return token_address  # Return address on error

    async def _get_token_balance(self, token_address: str, owner_address: str) -> int:
        """Get token balance."""
        try:
            token = await self.web3_manager.get_token_contract(token_address)
            if not token:
                return 0

            contract_func = token.functions.balanceOf(
                Web3.to_checksum_address(owner_address)
            )
            result = await self.web3_manager.call_contract_function(contract_func)
            if isinstance(result, str):
                return int(result)
            return int(result)

        except Exception as e:
            self.logger.error("Failed to get token balance: %s", str(e))
            return 0

    async def _get_token_allowance(
        self,
        token_address: str,
        owner_address: str,
        spender_address: str
    ) -> int:
        """Get token allowance."""
        try:
            token = await self.web3_manager.get_token_contract(token_address)
            if not token:
                return 0

            contract_func = token.functions.allowance(
                Web3.to_checksum_address(owner_address),
                Web3.to_checksum_address(spender_address)
            )
            result = await self.web3_manager.call_contract_function(contract_func)
            if isinstance(result, str):
                return int(result)
            return int(result)

        except Exception as e:
            self.logger.error("Failed to get token allowance: %s", str(e))
            return 0

    async def _approve_token(
        self,
        token_address: str,
        spender_address: str,
        amount: int
    ) -> Optional[str]:
        """Approve token spending."""
        try:
            token = await self.web3_manager.get_token_contract(token_address)
            if not token:
                return None

            tx_hash = await self.web3_manager.build_and_send_transaction(
                token,
                'approve',
                Web3.to_checksum_address(spender_address),
                amount
            )
            await self.web3_manager.wait_for_transaction(tx_hash)
            return tx_hash.hex()

        except Exception as e:
            self.logger.error("Failed to approve token: %s", str(e))
            return None
