"""Baseswap DEX implementation."""

import json
import logging
import asyncio
from decimal import Decimal
from typing import Dict, List, Any, Tuple
from web3 import Web3
from ..core.web3.web3_manager import Web3Manager
from .base_dex import BaseDEX

logger = logging.getLogger(__name__)

class Baseswap(BaseDEX):
    """Baseswap DEX implementation."""
    
    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize Baseswap."""
        super().__init__(web3_manager, config)
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize Baseswap."""
        try:
            # Load contract ABIs
            with open("abi/baseswap_factory.json", "r") as f:
                factory_abi = json.load(f)
            with open("abi/baseswap_router_v3.json", "r") as f:
                router_abi = json.load(f)
            with open("abi/baseswap_quoter.json", "r") as f:
                quoter_abi = json.load(f)
                
            # Initialize contracts
            self.factory = self.w3.eth.contract(
                address=self.config["factory"],
                abi=factory_abi
            )
            self.router = self.w3.eth.contract(
                address=self.config["router"],
                abi=router_abi
            )
            self.quoter = self.w3.eth.contract(
                address=self.config["quoter"],
                abi=quoter_abi
            )

            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Baseswap: {e}")
            return False
        
    async def get_pool_address(self, token_a: str, token_b: str, **kwargs) -> str:
        """Get pool address for token pair."""
        try:
            loop = asyncio.get_event_loop()
            pool = await loop.run_in_executor(
                None,
                lambda: self.factory.functions.getPool(token_a, token_b).call()
            )
            if pool == "0x0000000000000000000000000000000000000000":
                raise ValueError(f"No pool exists for {token_a}/{token_b}")
            return pool
        except Exception as e:
            logger.error(f"Failed to get pool address: {e}")
            raise
            
    async def get_reserves(self, pool_address: str) -> Tuple[Decimal, Decimal]:
        """Get token reserves from pool."""
        try:
            with open("abi/baseswap_pair.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            # Get reserves directly from pool
            loop = asyncio.get_event_loop()
            reserves = await loop.run_in_executor(
                None,
                lambda: pool.functions.getReserves().call()
            )
            return (
                Decimal(reserves[0]),
                Decimal(reserves[1])
            )
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
            amount_in_wei = self.to_wei(amount_in, await self.get_token_decimals(path[0]))
            
            # Use quoter contract to get quote
            loop = asyncio.get_event_loop()
            quote = await loop.run_in_executor(
                None,
                lambda: self.quoter.functions.quoteExactInputSingle(
                    path[0],
                    path[1],
                    amount_in_wei,
                    0  # sqrt price limit
                ).call()
            )
            
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
            with open("abi/baseswap_pair.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            # Get current reserves
            loop = asyncio.get_event_loop()
            reserves = await loop.run_in_executor(
                None,
                lambda: pool.functions.getReserves().call()
            )
            reserve_in = Decimal(reserves[0])
            reserve_out = Decimal(reserves[1])
            
            # Calculate current price
            current_price = reserve_out / reserve_in
            
            # Calculate execution price
            execution_price = amount_out / amount_in
            
            # Calculate price impact
            price_impact = abs(execution_price - current_price) / current_price
            return float(price_impact)
        except Exception as e:
            logger.error(f"Failed to calculate price impact: {e}")
            raise
            
    async def get_pool_fee(self, pool_address: str) -> Decimal:
        """Get pool trading fee."""
        try:
            # Baseswap uses fixed 0.3% fee
            return Decimal("0.003")
        except Exception as e:
            logger.error(f"Failed to get pool fee: {e}")
            raise
            
    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """Get pool information including liquidity, volume, etc."""
        try:
            with open("abi/baseswap_pair.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            # Get basic pool info
            loop = asyncio.get_event_loop()
            token0 = await loop.run_in_executor(
                None,
                lambda: pool.functions.token0().call()
            )
            token1 = await loop.run_in_executor(
                None,
                lambda: pool.functions.token1().call()
            )
            reserves = await loop.run_in_executor(
                None,
                lambda: pool.functions.getReserves().call()
            )
            
            return {
                "token0": token0,
                "token1": token1,
                "reserve0": reserves[0],
                "reserve1": reserves[1],
                "timestamp": reserves[2],
                "fee": 3000  # 0.3% in basis points
            }
        except Exception as e:
            logger.error(f"Failed to get pool info: {e}")
            raise
            
    async def validate_pool(self, pool_address: str) -> bool:
        """Validate pool exists and is active."""
        try:
            with open("abi/baseswap_pair.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            # Check if pool has reserves
            loop = asyncio.get_event_loop()
            reserves = await loop.run_in_executor(
                None,
                lambda: pool.functions.getReserves().call()
            )
            return reserves[0] > 0 and reserves[1] > 0
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
            loop = asyncio.get_event_loop()
            latest_block = await loop.run_in_executor(
                None,
                lambda: self.w3.eth.get_block("latest")
            )
            deadline = latest_block.timestamp + kwargs.get("deadline", 300)
            
            # Convert amounts to wei
            amount_in_wei = self.to_wei(amount_in, await self.get_token_decimals(path[0]))
            amount_out_min_wei = self.to_wei(amount_out_min, await self.get_token_decimals(path[1]))
            
            # Prepare exact input params
            params = {
                "tokenIn": path[0],
                "tokenOut": path[1],
                "recipient": to,
                "deadline": deadline,
                "amountIn": amount_in_wei,
                "amountOutMinimum": amount_out_min_wei,
                "sqrtPriceLimitX96": 0
            }
            
            # Estimate gas
            gas = await loop.run_in_executor(
                None,
                lambda: self.router.functions.exactInputSingle(params).estimate_gas()
            )
            return gas
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
            # Convert amounts to wei
            amount_in_wei = self.to_wei(amount_in, await self.get_token_decimals(path[0]))
            amount_out_min_wei = self.to_wei(amount_out_min, await self.get_token_decimals(path[1]))
            
            # Prepare exact input params
            params = {
                "tokenIn": path[0],
                "tokenOut": path[1],
                "recipient": to,
                "deadline": deadline,
                "amountIn": amount_in_wei,
                "amountOutMinimum": amount_out_min_wei,
                "sqrtPriceLimitX96": 0
            }
            
            # Get nonce
            loop = asyncio.get_event_loop()
            nonce = await loop.run_in_executor(
                None,
                lambda: self.w3.eth.get_transaction_count(to)
            )
            
            # Build transaction
            return self.router.functions.exactInputSingle(params).build_transaction({
                "from": to,
                "gas": await self.estimate_gas(amount_in, amount_out_min, path, to, **kwargs),
                "nonce": nonce
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
