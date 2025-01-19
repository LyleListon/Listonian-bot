"""Base class for V2 DEX implementations."""

from typing import List, Optional, Tuple
from decimal import Decimal
from web3 import Web3

from .dex_registry import BaseDEX, QuoteResult

class BaseV2DEX(BaseDEX):
    """Base class for V2 DEX implementations with consistent pair handling."""

    def __init__(self, web3: Web3, config: dict):
        """Initialize V2 DEX."""
        super().__init__(web3, config)
        self.router = self._initialize_router()
        self.factory = self._initialize_factory()
        self.fee_denominator = config.get('fee_denominator', 1000)  # Default to 0.3% fee
        self.fee_numerator = config.get('fee_numerator', 3)

    def _initialize_router(self):
        """Initialize router contract."""
        router_address = self.config.get('router')
        if not router_address:
            raise ValueError(f"No router address configured for {self.name}")
        
        router_abi = self.config.get('router_abi')
        if not router_abi:
            self.logger.warning(f"No router ABI provided for {self.name}, loading from default location")
            # Implement ABI loading logic here
            
        return self.w3.eth.contract(address=router_address, abi=router_abi)

    def _initialize_factory(self):
        """Initialize factory contract."""
        factory_address = self.config.get('factory')
        if not factory_address:
            raise ValueError(f"No factory address configured for {self.name}")
            
        factory_abi = self.config.get('factory_abi')
        if not factory_abi:
            self.logger.warning(f"No factory ABI provided for {self.name}, loading from default location")
            # Implement ABI loading logic here
            
        return self.w3.eth.contract(address=factory_address, abi=factory_abi)

    async def get_pair_address(self, token_a: str, token_b: str) -> str:
        """Get pair address for token pair."""
        try:
            return await self.factory.functions.getPair(token_a, token_b).call()
        except Exception as e:
            self.log_error(e, {
                "method": "get_pair_address",
                "token_a": token_a,
                "token_b": token_b
            })
            return None

    async def get_quote(self, token_in: str, token_out: str, amount_in: int) -> QuoteResult:
        """
        Get quote for V2 swap.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount in wei
            
        Returns:
            QuoteResult: Quote details including amount out and path
        """
        try:
            # Check if pair exists
            pair = await self.get_pair_address(token_in, token_out)
            if not pair or pair == "0x" + "0" * 40:
                return QuoteResult(
                    amount_out=0,
                    fee=0,
                    price_impact=0.0,
                    path=[],
                    success=False,
                    error="No pair exists"
                )

            # Get amounts out
            amounts = await self.router.functions.getAmountsOut(
                amount_in,
                [token_in, token_out]
            ).call()

            if len(amounts) != 2:
                raise ValueError("Invalid amounts returned from router")

            # Calculate fee
            fee = (amount_in * self.fee_numerator) // self.fee_denominator

            return QuoteResult(
                amount_out=amounts[1],
                fee=fee,
                price_impact=0.0,  # Calculate this properly
                path=[token_in, token_out],
                success=True
            )

        except Exception as e:
            self.log_error(e, {
                "method": "get_quote",
                "token_in": token_in,
                "token_out": token_out,
                "amount_in": amount_in
            })
            return QuoteResult(
                amount_out=0,
                fee=0,
                price_impact=0.0,
                path=[],
                success=False,
                error=str(e)
            )

    async def check_liquidity(self, token_in: str, token_out: str) -> Decimal:
        """Check liquidity for token pair."""
        try:
            pair = await self.get_pair_address(token_in, token_out)
            if not pair or pair == "0x" + "0" * 40:
                return Decimal(0)

            # Get pair contract
            pair_abi = self.config.get('pair_abi')
            if not pair_abi:
                self.logger.warning(f"No pair ABI provided for {self.name}, loading from default location")
                # Implement ABI loading logic here

            pair_contract = self.w3.eth.contract(address=pair, abi=pair_abi)
            
            # Get reserves
            reserves = await pair_contract.functions.getReserves().call()
            token0 = await pair_contract.functions.token0().call()
            
            # Order reserves based on token addresses
            if token_in.lower() == token0.lower():
                reserve_in, reserve_out = reserves[0], reserves[1]
            else:
                reserve_in, reserve_out = reserves[1], reserves[0]
                
            # Convert to Decimal for precise math
            return Decimal(str(reserve_in))

        except Exception as e:
            self.log_error(e, {
                "method": "check_liquidity",
                "token_in": token_in,
                "token_out": token_out
            })
            return Decimal(0)

    async def get_reserves(self, token_a: str, token_b: str) -> Tuple[int, int]:
        """Get reserves for token pair."""
        try:
            pair = await self.get_pair_address(token_a, token_b)
            if not pair or pair == "0x" + "0" * 40:
                return (0, 0)

            pair_contract = self.w3.eth.contract(
                address=pair,
                abi=self.config.get('pair_abi')
            )
            
            reserves = await pair_contract.functions.getReserves().call()
            token0 = await pair_contract.functions.token0().call()
            
            if token_a.lower() == token0.lower():
                return reserves[0], reserves[1]
            return reserves[1], reserves[0]

        except Exception as e:
            self.log_error(e, {
                "method": "get_reserves",
                "token_a": token_a,
                "token_b": token_b
            })
            return (0, 0)
