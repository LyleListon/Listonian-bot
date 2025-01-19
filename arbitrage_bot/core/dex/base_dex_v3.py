"""Base class for V3 DEX implementations."""

from typing import List, Optional, Tuple
from decimal import Decimal
from web3 import Web3

from .dex_registry import BaseDEX, QuoteResult

class BaseV3DEX(BaseDEX):
    """Base class for V3 DEX implementations with consistent path encoding."""

    def __init__(self, web3: Web3, config: dict):
        """Initialize V3 DEX."""
        super().__init__(web3, config)
        self.quoter = self._initialize_quoter()
        self.factory = self._initialize_factory()
        self.default_fee_tiers = config.get('fee_tiers', [100, 500, 3000, 10000])

    def _initialize_quoter(self):
        """Initialize quoter contract."""
        quoter_address = self.config.get('quoter')
        if not quoter_address:
            raise ValueError(f"No quoter address configured for {self.name}")
        
        quoter_abi = self.config.get('quoter_abi')
        if not quoter_abi:
            self.logger.warning(f"No quoter ABI provided for {self.name}, loading from default location")
            # Implement ABI loading logic here
            
        return self.w3.eth.contract(address=quoter_address, abi=quoter_abi)

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

    def encode_path(self, token_in: str, token_out: str, fee: int) -> bytes:
        """
        Encode path for V3 swap.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            fee: Fee tier (e.g., 500, 3000, 10000)
            
        Returns:
            bytes: Encoded path for the swap
        """
        # Convert addresses to bytes, removing '0x' prefix
        token_in_bytes = bytes.fromhex(token_in[2:])
        token_out_bytes = bytes.fromhex(token_out[2:])
        
        # Convert fee to exactly 3 bytes
        fee_bytes = fee.to_bytes(3, 'big')
        
        # Concatenate as: token_in + fee + token_out
        return token_in_bytes + fee_bytes + token_out_bytes

    async def get_pool_address(self, token_a: str, token_b: str, fee: int) -> str:
        """Get pool address for token pair and fee tier."""
        try:
            return await self.factory.functions.getPool(token_a, token_b, fee).call()
        except Exception as e:
            self.log_error(e, {
                "method": "get_pool_address",
                "token_a": token_a,
                "token_b": token_b,
                "fee": fee
            })
            return None

    async def get_quote(self, token_in: str, token_out: str, amount_in: int) -> QuoteResult:
        """
        Get quote for V3 swap.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount in wei
            
        Returns:
            QuoteResult: Quote details including amount out and path
        """
        best_quote = None
        best_fee = None
        error = None

        for fee in self.default_fee_tiers:
            try:
                # Check if pool exists
                pool = await self.get_pool_address(token_in, token_out, fee)
                if not pool or pool == "0x" + "0" * 40:  # Skip if pool doesn't exist
                    continue

                # Encode path for quote
                path = self.encode_path(token_in, token_out, fee)
                
                # Get quote from contract
                quote = await self.quoter.functions.quoteExactInput(
                    path,
                    amount_in
                ).call()

                if best_quote is None or quote > best_quote:
                    best_quote = quote
                    best_fee = fee

            except Exception as e:
                error = str(e)
                self.log_error(e, {
                    "method": "get_quote",
                    "token_in": token_in,
                    "token_out": token_out,
                    "amount_in": amount_in,
                    "fee": fee
                })

        if best_quote is not None:
            return QuoteResult(
                amount_out=best_quote,
                fee=best_fee,
                price_impact=0.0,  # Calculate this properly
                path=[token_in, token_out],
                success=True
            )
        else:
            return QuoteResult(
                amount_out=0,
                fee=0,
                price_impact=0.0,
                path=[],
                success=False,
                error=error
            )

    async def check_liquidity(self, token_in: str, token_out: str) -> Decimal:
        """Check liquidity across all fee tiers."""
        total_liquidity = Decimal(0)

        for fee in self.default_fee_tiers:
            try:
                pool = await self.get_pool_address(token_in, token_out, fee)
                if not pool or pool == "0x" + "0" * 40:
                    continue
                    
                # Implement liquidity checking logic here
                # This will be DEX-specific as different V3 DEXes may have
                # different ways of reporting liquidity
                
            except Exception as e:
                self.log_error(e, {
                    "method": "check_liquidity",
                    "token_in": token_in,
                    "token_out": token_out,
                    "fee": fee
                })

        return total_liquidity
