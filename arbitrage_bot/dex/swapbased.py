"""SwapBased DEX implementation."""

import json
import logging
import asyncio
from decimal import Decimal
from typing import Dict, List, Any, Tuple
from web3 import Web3
from ..core.web3.web3_manager import Web3Manager
from .base_dex import BaseDEX

logger = logging.getLogger(__name__)

class SwapBased(BaseDEX):
    """SwapBased DEX implementation."""
    
    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize SwapBased DEX."""
        super().__init__(web3_manager, config)
        self.fee = config.get('fee', 3000)  # 0.3% default fee
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize SwapBased DEX."""
        try:
            # Initialize contracts with SwapBased V3 ABIs
            with open("abi/swapbased_factory.json", "r") as f:
                factory_abi = json.load(f)
            with open("abi/swapbased_router.json", "r") as f:
                router_abi = json.load(f)
            with open("abi/swapbased_pool.json", "r") as f:
                self.pool_abi = json.load(f)
                
            # Initialize contracts
            self.factory = self.w3.eth.contract(
                address=self.config["factory"],
                abi=factory_abi
            )
            self.router = self.w3.eth.contract(
                address=self.config["router"],
                abi=router_abi
            )
            
            logger.info(f"Initialized SwapBased DEX with factory {self.config['factory']}")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SwapBased: {e}")
            return False
        
    async def get_pool_address(self, token_a: str, token_b: str, **kwargs) -> str:
        """Get pool address for token pair."""
        try:
            loop = asyncio.get_event_loop()
            pool = await loop.run_in_executor(
                None,
                lambda: self.factory.functions.getPool(token_a, token_b, self.fee).call()
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
            pool = self.w3.eth.contract(address=pool_address, abi=self.pool_abi)
            
            # Get current price and liquidity from pool
            loop = asyncio.get_event_loop()
            slot0 = await loop.run_in_executor(
                None,
                lambda: pool.functions.slot0().call()
            )
            liquidity = await loop.run_in_executor(
                None,
                lambda: pool.functions.liquidity().call()
            )
            sqrtPriceX96 = Decimal(slot0[0])
            
            # Calculate reserves from sqrtPrice and liquidity
            price = (sqrtPriceX96 * sqrtPriceX96) / (2 ** 192)
            reserve1 = Decimal(liquidity) * price
            reserve0 = Decimal(liquidity) / price
            
            return (reserve0, reserve1)
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
            
            # Get pool address
            pool_address = await self.get_pool_address(path[0], path[1])
            pool = self.w3.eth.contract(address=pool_address, abi=self.pool_abi)
            
            # Get current price and liquidity
            loop = asyncio.get_event_loop()
            slot0 = await loop.run_in_executor(
                None,
                lambda: pool.functions.slot0().call()
            )
            liquidity = await loop.run_in_executor(
                None,
                lambda: pool.functions.liquidity().call()
            )
            sqrtPriceX96 = Decimal(slot0[0])
            
            # Calculate price and output amount
            price = (sqrtPriceX96 * sqrtPriceX96) / (2 ** 192)
            amount_out_wei = int(Decimal(amount_in_wei) * price)
            amount_out = self.from_wei(amount_out_wei, await self.get_token_decimals(path[1]))
            
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
            pool = self.w3.eth.contract(address=pool_address, abi=self.pool_abi)
            
            # Get current price from pool
            loop = asyncio.get_event_loop()
            slot0 = await loop.run_in_executor(
                None,
                lambda: pool.functions.slot0().call()
            )
            sqrtPriceX96 = Decimal(slot0[0])
            current_price = (sqrtPriceX96 * sqrtPriceX96) / (2 ** 192)
            
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
            pool = self.w3.eth.contract(address=pool_address, abi=self.pool_abi)
            loop = asyncio.get_event_loop()
            fee = await loop.run_in_executor(
                None,
                lambda: pool.functions.fee().call()
            )
            return Decimal(fee) / Decimal(1000000)  # Convert from bps (1e-6) to decimal
        except Exception as e:
            logger.error(f"Failed to get pool fee: {e}")
            raise
            
    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """Get pool information including liquidity, volume, etc."""
        try:
            pool = self.w3.eth.contract(address=pool_address, abi=self.pool_abi)
            
            # Get pool info
            loop = asyncio.get_event_loop()
            token0 = await loop.run_in_executor(
                None,
                lambda: pool.functions.token0().call()
            )
            token1 = await loop.run_in_executor(
                None,
                lambda: pool.functions.token1().call()
            )
            slot0 = await loop.run_in_executor(
                None,
                lambda: pool.functions.slot0().call()
            )
            liquidity = await loop.run_in_executor(
                None,
                lambda: pool.functions.liquidity().call()
            )
            fee = await loop.run_in_executor(
                None,
                lambda: pool.functions.fee().call()
            )
            
            return {
                "token0": token0,
                "token1": token1,
                "sqrtPriceX96": slot0[0],
                "tick": slot0[1],
                "liquidity": liquidity,
                "fee": fee
            }
        except Exception as e:
            logger.error(f"Failed to get pool info: {e}")
            raise
            
    async def validate_pool(self, pool_address: str) -> bool:
        """Validate pool exists and is active."""
        try:
            pool = self.w3.eth.contract(address=pool_address, abi=self.pool_abi)
            
            # Check if pool has liquidity
            loop = asyncio.get_event_loop()
            liquidity = await loop.run_in_executor(
                None,
                lambda: pool.functions.liquidity().call()
            )
            slot0 = await loop.run_in_executor(
                None,
                lambda: pool.functions.slot0().call()
            )
            
            return liquidity > 0 and slot0[0] > 0  # Check both liquidity and price are non-zero
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
                "fee": self.fee,
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
                "fee": self.fee,
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
