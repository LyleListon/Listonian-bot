"""Aerodrome V3 DEX implementation."""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Any, Optional
from web3 import Web3
from .base_dex import BaseDEX

logger = logging.getLogger(__name__)

class AerodromeV3(BaseDEX):
    """Aerodrome V3 DEX implementation supporting concentrated liquidity."""
    
    def __init__(self, web3: Web3, config: Dict[str, Any]):
        """Initialize Aerodrome V3 DEX."""
        super().__init__(web3, config)
        
        # Load contract ABIs
        with open("abi/aerodrome_v3_factory.json", "r") as f:
            self.factory_abi = json.load(f)
        with open("abi/aerodrome_v3_router.json", "r") as f:
            self.router_abi = json.load(f)
        with open("abi/aerodrome_v3_pool.json", "r") as f:
            self.pool_abi = json.load(f)
        with open("abi/aerodrome_v3_quoter.json", "r") as f:
            self.quoter_abi = json.load(f)
            
        # Get contract addresses from config
        factory_address = config.get("factory")
        router_address = config.get("router")
        quoter_address = config.get("quoter")
        
        logger.debug(f"Aerodrome V3 Config - Factory: {factory_address}, Router: {router_address}, Quoter: {quoter_address}")
        if not all([factory_address, router_address, quoter_address]):
            raise ValueError("Missing Aerodrome V3 contract addresses")
            
        # Initialize contracts
        self.factory = self.w3.eth.contract(
            address=factory_address,
            abi=self.factory_abi
        )
        self.router = self.w3.eth.contract(
            address=router_address,
            abi=self.router_abi
        )
        self.quoter = self.w3.eth.contract(
            address=quoter_address,
            abi=self.quoter_abi
        )
        
        # Cache for pool info
        self._pool_info_cache: Dict[str, Dict[str, Any]] = {}
        
    async def get_pool_address(
        self,
        token_a: str,
        token_b: str,
        fee: int
    ) -> str:
        """Get pool address for token pair and fee tier."""
        try:
            # Sort tokens to match factory's sorting
            token0, token1 = sorted([token_a, token_b])
            
            logger.debug(f"Calling factory.getPool with token0={token0}, token1={token1}, fee={fee}")
            # Get pool address
            pool_address = self.factory.functions.getPool(
                token0,
                token1,
                fee
            ).call()
            logger.debug(f"Factory returned pool address: {pool_address}")
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                raise ValueError(f"No pool found for {token_a}/{token_b} with fee {fee}")
                
            return pool_address
            
        except Exception as e:
            logger.error(f"Failed to get pool address: {e}")
            raise
            
    async def get_reserves(self, pool_address: str) -> Tuple[Decimal, Decimal]:
        """Get token reserves from pool."""
        try:
            pool = self.w3.eth.contract(
                address=pool_address,
                abi=self.pool_abi
            )
            
            # Get pool slot0 data
            slot0 = pool.functions.slot0().call()
            sqrt_price_x96 = slot0[0]
            
            # Get tokens and decimals
            token0 = pool.functions.token0().call()
            token1 = pool.functions.token1().call()
            decimals0 = await self.get_token_decimals(token0)
            decimals1 = await self.get_token_decimals(token1)
            
            # Calculate reserves from sqrt price
            price = (sqrt_price_x96 ** 2) / (2 ** 192)
            liquidity = pool.functions.liquidity().call()
            
            reserve0 = self.from_wei(liquidity, decimals0)
            reserve1 = self.from_wei(int(liquidity * price), decimals1)
            
            return reserve0, reserve1
            
        except Exception as e:
            logger.error(f"Failed to get reserves: {e}")
            raise
            
    async def get_amounts_out(
        self,
        amount_in: Decimal,
        path: List[str],
        fee: int = 3000
    ) -> List[Decimal]:
        """Calculate output amounts for a given input amount and path."""
        try:
            amount_in_wei = self.to_wei(
                amount_in,
                await self.get_token_decimals(path[0])
            )
            
            # Use quoter contract
            quote = self.quoter.functions.quoteExactInput(
                path,
                amount_in_wei
            ).call()
            
            # Convert output to decimals
            decimals_out = await self.get_token_decimals(path[-1])
            amount_out = self.from_wei(quote[0], decimals_out)
            
            return [amount_in, amount_out]
            
        except Exception as e:
            logger.error(f"Failed to get amounts out: {e}")
            raise
            
    async def get_price_impact(
        self,
        amount_in: Decimal,
        amount_out: Decimal,
        pool_address: str
    ) -> float:
        """Calculate price impact for a trade."""
        try:
            pool = self.w3.eth.contract(
                address=pool_address,
                abi=self.pool_abi
            )
            
            # Get current sqrt price
            slot0 = pool.functions.slot0().call()
            sqrt_price_x96_before = slot0[0]
            
            # Get tokens
            token0 = pool.functions.token0().call()
            token1 = pool.functions.token1().call()
            decimals0 = await self.get_token_decimals(token0)
            decimals1 = await self.get_token_decimals(token1)
            
            # Calculate price impact
            price_before = (sqrt_price_x96_before ** 2) / (2 ** 192)
            amount_in_wei = self.to_wei(amount_in, decimals0)
            amount_out_wei = self.to_wei(amount_out, decimals1)
            
            # Simulate price after trade
            sqrt_price_x96_after = int(
                sqrt_price_x96_before * 
                (1 + (amount_in_wei / (pool.functions.liquidity().call() * 2**96)))
            )
            price_after = (sqrt_price_x96_after ** 2) / (2 ** 192)
            
            return abs(1 - (price_after / price_before))
            
        except Exception as e:
            logger.error(f"Failed to calculate price impact: {e}")
            raise
            
    async def get_pool_fee(self, pool_address: str) -> Decimal:
        """Get pool trading fee."""
        try:
            pool = self.w3.eth.contract(
                address=pool_address,
                abi=self.pool_abi
            )
            # Get fee in basis points
            fee_bps = pool.functions.fee().call()
            return (Decimal(str(fee_bps)) / Decimal("1000000")).quantize(Decimal("0.000001"))  # Convert from basis points to decimal (e.g., 100 -> 0.0001)
            
        except Exception as e:
            logger.error(f"Failed to get pool fee: {e}")
            raise
            
    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """Get pool information including liquidity, volume, etc."""
        try:
            # Check cache first
            if pool_address in self._pool_info_cache:
                return self._pool_info_cache[pool_address]
                
            pool = self.w3.eth.contract(
                address=pool_address,
                abi=self.pool_abi
            )
            
            # Get tokens
            token0 = pool.functions.token0().call()
            token1 = pool.functions.token1().call()
            decimals0 = await self.get_token_decimals(token0)
            decimals1 = await self.get_token_decimals(token1)
            
            # Get pool data
            slot0 = pool.functions.slot0().call()
            liquidity = pool.functions.liquidity().call()
            fee = pool.functions.fee().call()
            
            # Calculate price and reserves
            sqrt_price_x96 = slot0[0]
            price = (sqrt_price_x96 ** 2) / (2 ** 192)
            
            info = {
                "address": pool_address,
                "token0": token0,
                "token1": token1,
                "decimals0": decimals0,
                "decimals1": decimals1,
                "liquidity": liquidity,
                "sqrt_price_x96": sqrt_price_x96,
                "price": price,
                "tick": slot0[1],
                "fee": (Decimal(str(fee)) / Decimal("1000000")).quantize(Decimal("0.000001"))  # Convert from basis points to decimal (e.g., 100 -> 0.0001)
            }
            
            # Cache the result
            self._pool_info_cache[pool_address] = info
            return info
            
        except Exception as e:
            logger.error(f"Failed to get pool info: {e}")
            raise
            
    async def validate_pool(self, pool_address: str) -> bool:
        """Validate pool exists and is active."""
        try:
            pool = self.w3.eth.contract(
                address=pool_address,
                abi=self.pool_abi
            )
            
            # Check liquidity
            liquidity = pool.functions.liquidity().call()
            if liquidity == 0:
                return False
                
            # Check if pool is initialized
            slot0 = pool.functions.slot0().call()
            if slot0[0] == 0:  # sqrt_price_x96 == 0
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate pool: {e}")
            return False
            
    async def estimate_gas(
        self,
        amount_in: Decimal,
        amount_out_min: Decimal,
        path: List[str],
        to: str,
        fee: int = 3000
    ) -> int:
        """Estimate gas cost for a trade."""
        try:
            amount_in_wei = self.to_wei(
                amount_in,
                await self.get_token_decimals(path[0])
            )
            amount_out_min_wei = self.to_wei(
                amount_out_min,
                await self.get_token_decimals(path[-1])
            )
            
            # Get deadline
            deadline = self.w3.eth.get_block('latest').timestamp + 300
            
            # Estimate gas
            return self.router.functions.exactInput(
                (
                    path,
                    amount_in_wei,
                    amount_out_min_wei,
                    to
                )
            ).estimate_gas()
            
        except Exception as e:
            logger.error(f"Failed to estimate gas: {e}")
            raise
            
    async def build_swap_transaction(
        self,
        amount_in: Decimal,
        amount_out_min: Decimal,
        path: List[str],
        to: str,
        deadline: int,
        fee: int = 3000
    ) -> Dict[str, Any]:
        """Build swap transaction."""
        try:
            amount_in_wei = self.to_wei(
                amount_in,
                await self.get_token_decimals(path[0])
            )
            amount_out_min_wei = self.to_wei(
                amount_out_min,
                await self.get_token_decimals(path[-1])
            )
            
            # Build transaction
            return self.router.functions.exactInput(
                (
                    path,
                    amount_in_wei,
                    amount_out_min_wei,
                    to
                )
            ).build_transaction({
                'from': to,
                'gas': await self.estimate_gas(
                    amount_in,
                    amount_out_min,
                    path,
                    to,
                    fee
                ),
                'nonce': self.w3.eth.get_transaction_count(to)
            })
            
        except Exception as e:
            logger.error(f"Failed to build swap transaction: {e}")
            raise
            
    async def decode_swap_error(self, error: Exception) -> str:
        """Decode swap error into human readable message."""
        try:
            error_str = str(error)
            
            if "LOK" in error_str:
                return "Price slippage check"
            elif "SPL" in error_str:
                return "Insufficient liquidity for swap"
            elif "TF" in error_str:
                return "Transfer failed"
            else:
                return f"Unknown error: {error_str}"
                
        except Exception as e:
            logger.error(f"Failed to decode error: {e}")
            return str(error)
