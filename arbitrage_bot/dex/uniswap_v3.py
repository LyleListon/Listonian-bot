"""Uniswap V3 DEX implementation."""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Any, Tuple
from web3 import Web3

from .base_dex import BaseDEX

logger = logging.getLogger(__name__)

class UniswapV3(BaseDEX):
    """Uniswap V3 DEX implementation."""
    
    def __init__(self, web3: Web3, config: Dict[str, Any]):
        """Initialize Uniswap V3."""
        super().__init__(web3, config)
        
        # Load contract ABIs
        with open("abi/IUniswapV3Factory.json", "r") as f:
            factory_abi = json.load(f)
        with open("abi/IUniswapV3Router.json", "r") as f:
            router_abi = json.load(f)
        with open("abi/IUniswapV3QuoterV2.json", "r") as f:
            quoter_abi = json.load(f)
            
        # Initialize contracts
        self.factory = self.w3.eth.contract(
            address=config["factory"],
            abi=factory_abi
        )
        self.router = self.w3.eth.contract(
            address=config["router"],
            abi=router_abi
        )
        self.quoter = self.w3.eth.contract(
            address=config["quoter"],
            abi=quoter_abi
        )
        
    async def get_pool_address(self, token_a: str, token_b: str, **kwargs) -> str:
        """Get pool address for token pair."""
        fee = kwargs.get("fee", 3000)  # Default to 0.3% fee tier
        try:
            pool = self.factory.functions.getPool(
                token_a,
                token_b,
                fee
            ).call()
            if pool == "0x0000000000000000000000000000000000000000":
                raise ValueError(f"No pool exists for {token_a}/{token_b} with fee {fee}")
            return pool
        except Exception as e:
            logger.error(f"Failed to get pool address: {e}")
            raise
            
    async def get_reserves(self, pool_address: str) -> Tuple[Decimal, Decimal]:
        """Get token reserves from pool."""
        try:
            with open("abi/IUniswapV3Pool.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            # Get slot0 data which contains sqrt price
            slot0 = pool.functions.slot0().call()
            sqrt_price_x96 = slot0[0]
            
            # Get liquidity
            liquidity = pool.functions.liquidity().call()
            
            # Calculate reserves based on sqrt price and liquidity
            # This is a simplified calculation
            price = (sqrt_price_x96 ** 2) / (2 ** 192)
            reserve0 = Decimal(liquidity) / Decimal(price)
            reserve1 = Decimal(liquidity) * Decimal(price)
            
            return reserve0, reserve1
        except Exception as e:
            logger.error(f"Failed to get reserves: {e}")
            raise
            
    async def get_amounts_out(
        self,
        amount_in: Decimal,
        path: List[str],
        **kwargs
    ) -> List[Decimal]:
        """Calculate output amounts for a given input amount and path."""
        try:
            fee = kwargs.get("fee", 3000)
            amount_in_wei = self.to_wei(amount_in, await self.get_token_decimals(path[0]))
            
            # Use quoter contract to get quote
            quote = self.quoter.functions.quoteExactInputSingle(
                path[0],
                path[1],
                fee,
                amount_in_wei,
                0  # sqrt price limit
            ).call()
            
            amount_out = self.from_wei(
                quote[0],
                await self.get_token_decimals(path[1])
            )
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
            # Get current price from pool
            with open("abi/IUniswapV3Pool.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            slot0 = pool.functions.slot0().call()
            current_price = (slot0[0] ** 2) / (2 ** 192)
            
            # Calculate execution price
            execution_price = float(amount_out) / float(amount_in)
            
            # Calculate price impact
            price_impact = abs(execution_price - current_price) / current_price
            return price_impact
        except Exception as e:
            logger.error(f"Failed to calculate price impact: {e}")
            raise
            
    async def get_pool_fee(self, pool_address: str) -> Decimal:
        """Get pool trading fee."""
        try:
            with open("abi/IUniswapV3Pool.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            fee = pool.functions.fee().call()
            return Decimal(fee) / Decimal(1000000)  # Convert from bps to decimal
        except Exception as e:
            logger.error(f"Failed to get pool fee: {e}")
            raise
            
    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """Get pool information including liquidity, volume, etc."""
        try:
            with open("abi/IUniswapV3Pool.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            # Get basic pool info
            token0 = pool.functions.token0().call()
            token1 = pool.functions.token1().call()
            fee = pool.functions.fee().call()
            liquidity = pool.functions.liquidity().call()
            slot0 = pool.functions.slot0().call()
            
            return {
                "token0": token0,
                "token1": token1,
                "fee": fee,
                "liquidity": liquidity,
                "sqrt_price_x96": slot0[0],
                "tick": slot0[1],
                "observation_index": slot0[2],
                "observation_cardinality": slot0[3],
                "observation_cardinality_next": slot0[4],
                "fee_protocol": slot0[5]
            }
        except Exception as e:
            logger.error(f"Failed to get pool info: {e}")
            raise
            
    async def validate_pool(self, pool_address: str) -> bool:
        """Validate pool exists and is active."""
        try:
            with open("abi/IUniswapV3Pool.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            # Check if pool has liquidity
            liquidity = pool.functions.liquidity().call()
            return liquidity > 0
        except Exception as e:
            logger.error(f"Failed to validate pool: {e}")
            return False
            
    async def estimate_gas(
        self,
        amount_in: Decimal,
        amount_out_min: Decimal,
        path: List[str],
        to: str,
        **kwargs
    ) -> int:
        """Estimate gas cost for a trade."""
        try:
            fee = kwargs.get("fee", 3000)
            deadline = kwargs.get("deadline", self.w3.eth.get_block("latest").timestamp + 300)
            
            # Convert amounts to wei
            amount_in_wei = self.to_wei(amount_in, await self.get_token_decimals(path[0]))
            amount_out_min_wei = self.to_wei(amount_out_min, await self.get_token_decimals(path[1]))
            
            # Prepare exact input params
            params = {
                "tokenIn": path[0],
                "tokenOut": path[1],
                "fee": fee,
                "recipient": to,
                "deadline": deadline,
                "amountIn": amount_in_wei,
                "amountOutMinimum": amount_out_min_wei,
                "sqrtPriceLimitX96": 0
            }
            
            # Estimate gas
            return self.router.functions.exactInputSingle(params).estimate_gas()
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
        **kwargs
    ) -> Dict[str, Any]:
        """Build swap transaction."""
        try:
            fee = kwargs.get("fee", 3000)
            
            # Convert amounts to wei
            amount_in_wei = self.to_wei(amount_in, await self.get_token_decimals(path[0]))
            amount_out_min_wei = self.to_wei(amount_out_min, await self.get_token_decimals(path[1]))
            
            # Prepare exact input params
            params = {
                "tokenIn": path[0],
                "tokenOut": path[1],
                "fee": fee,
                "recipient": to,
                "deadline": deadline,
                "amountIn": amount_in_wei,
                "amountOutMinimum": amount_out_min_wei,
                "sqrtPriceLimitX96": 0
            }
            
            # Build transaction
            return self.router.functions.exactInputSingle(params).build_transaction({
                "from": to,
                "gas": await self.estimate_gas(amount_in, amount_out_min, path, to, **kwargs),
                "nonce": self.w3.eth.get_transaction_count(to)
            })
        except Exception as e:
            logger.error(f"Failed to build swap transaction: {e}")
            raise
            
    async def decode_swap_error(self, error: Exception) -> str:
        """Decode swap error into human readable message."""
        try:
            # Extract revert reason if available
            if hasattr(error, "args") and len(error.args) > 0:
                return str(error.args[0])
            return str(error)
        except Exception as e:
            logger.error(f"Failed to decode error: {e}")
            return str(error)
