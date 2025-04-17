"""Pancakeswap DEX implementation."""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Any, Tuple
from web3 import Web3
from ..core.web3.web3_manager import Web3Manager
from .base_dex import BaseDEX

logger = logging.getLogger(__name__)


class Pancakeswap(BaseDEX):
    """Pancakeswap DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize Pancakeswap."""
        super().__init__(web3_manager, config)
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize Pancakeswap."""
        try:
            # Load contract ABIs
            with open("abi/pancakeswap_v3_factory.json", "r") as f:
                factory_abi = json.load(f)
            with open("abi/pancakeswap_v3_router.json", "r") as f:
                router_abi = json.load(f)
            with open("abi/pancakeswap_v3_quoter.json", "r") as f:
                quoter_abi = json.load(f)

            # Initialize contracts
            self.factory = self.web3_manager.w3.eth.contract( # Use web3_manager
                address=self.config["factory"], abi=factory_abi
            )
            self.router = self.web3_manager.w3.eth.contract( # Use web3_manager
                address=self.config["router"], abi=router_abi
            )
            self.quoter = self.web3_manager.w3.eth.contract( # Use web3_manager
                address=self.config["quoter"], abi=quoter_abi
            )

            self.initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Pancakeswap: {e}")
            return False

    async def get_pool_address(self, token_a: str, token_b: str, **kwargs) -> str:
        """Get pool address for token pair."""
        fee = kwargs.get("fee", 2500)  # Default to 0.25% fee tier for Pancakeswap
        try:
            pool = self.factory.functions.getPool(token_a, token_b, fee).call()
            if pool == "0x0000000000000000000000000000000000000000":
                raise ValueError(
                    f"No pool exists for {token_a}/{token_b} with fee {fee}"
                )
            return pool
        except Exception as e:
            logger.error(f"Failed to get pool address: {e}")
            raise

    async def get_reserves(self, pool_address: str) -> Tuple[Decimal, Decimal]:
        """Get token reserves from pool."""
        try:
            with open("abi/pancake_v3_pool.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.web3_manager.w3.eth.contract(address=pool_address, abi=pool_abi) # Use web3_manager

            # Get slot0 data which contains sqrt price
            slot0 = pool.functions.slot0().call()
            sqrt_price_x96 = slot0[0]

            # Get liquidity
            liquidity = pool.functions.liquidity().call()

            # Calculate reserves based on sqrt price and liquidity
            # This is a simplified calculation
            price = (sqrt_price_x96**2) / (2**192)
            reserve0 = Decimal(liquidity) / Decimal(price)
            reserve1 = Decimal(liquidity) * Decimal(price)

            return reserve0, reserve1
        except Exception as e:
            logger.error(f"Failed to get reserves: {e}")
            raise

    async def get_amounts_out(
        self, amount_in: Decimal, path: List[str], **kwargs
    ) -> List[Decimal]:
        """Calculate output amounts for a given input amount and path."""
        try:
            fee = kwargs.get("fee", 2500)  # Default to 0.25% fee tier
            amount_in_wei = self.to_wei(
                amount_in, await self.get_token_decimals(path[0])
            )

            # Use quoter contract to get quote
            quote = self.quoter.functions.quoteExactInputSingle(
                {
                    "tokenIn": path[0],
                    "tokenOut": path[1],
                    "fee": fee,
                    "amountIn": amount_in_wei,
                    "sqrtPriceLimitX96": 0,
                }
            ).call()

            amount_out = self.from_wei(quote[0], await self.get_token_decimals(path[1]))
            return [amount_in, amount_out]
        except Exception as e:
            logger.error(f"Failed to get amounts out: {e}")
            raise

    async def get_price_impact(
        self, amount_in: Decimal, amount_out: Decimal, pool_address: str
    ) -> float:
        """Calculate price impact for a trade."""
        try:
            with open("abi/pancake_v3_pool.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.web3_manager.w3.eth.contract(address=pool_address, abi=pool_abi) # Use web3_manager

            # Get current price from pool
            slot0 = pool.functions.slot0().call()
            current_price = (slot0[0] ** 2) / (2**192)

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
            with open("abi/pancake_v3_pool.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.web3_manager.w3.eth.contract(address=pool_address, abi=pool_abi) # Use web3_manager
            fee = pool.functions.fee().call()
            return Decimal(fee) / Decimal(1000000)  # Convert from bps to decimal
        except Exception as e:
            logger.error(f"Failed to get pool fee: {e}")
            raise

    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """Get pool information including liquidity, volume, etc."""
        try:
            with open("abi/pancake_v3_pool.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.web3_manager.w3.eth.contract(address=pool_address, abi=pool_abi) # Use web3_manager

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
                "fee_protocol": slot0[5],
            }
        except Exception as e:
            logger.error(f"Failed to get pool info: {e}")
            raise

    async def validate_pool(self, pool_address: str) -> bool:
        """Validate pool exists and is active."""
        try:
            with open("abi/pancake_v3_pool.json", "r") as f:
                pool_abi = json.load(f)
            pool = self.web3_manager.w3.eth.contract(address=pool_address, abi=pool_abi) # Use web3_manager

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
        **kwargs,
    ) -> int:
        """Estimate gas cost for a trade."""
        try:
            fee = kwargs.get("fee", 2500)  # Default to 0.25% fee tier
            deadline = kwargs.get(
                "deadline", self.web3_manager.w3.eth.get_block("latest").timestamp + 300 # Use web3_manager
            )

            # Convert amounts to wei
            amount_in_wei = self.to_wei(
                amount_in, await self.get_token_decimals(path[0])
            )
            amount_out_min_wei = self.to_wei(
                amount_out_min, await self.get_token_decimals(path[1])
            )

            # Prepare exact input params
            params = {
                "tokenIn": path[0],
                "tokenOut": path[1],
                "fee": fee,
                "recipient": to,
                "deadline": deadline,
                "amountIn": amount_in_wei,
                "amountOutMinimum": amount_out_min_wei,
                "sqrtPriceLimitX96": 0,
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
        **kwargs,
    ) -> Dict[str, Any]:
        """Build swap transaction."""
        try:
            fee = kwargs.get("fee", 2500)  # Default to 0.25% fee tier

            # Convert amounts to wei
            amount_in_wei = self.to_wei(
                amount_in, await self.get_token_decimals(path[0])
            )
            amount_out_min_wei = self.to_wei(
                amount_out_min, await self.get_token_decimals(path[1])
            )

            # Prepare exact input params
            params = {
                "tokenIn": path[0],
                "tokenOut": path[1],
                "fee": fee,
                "recipient": to,
                "deadline": deadline,
                "amountIn": amount_in_wei,
                "amountOutMinimum": amount_out_min_wei,
                "sqrtPriceLimitX96": 0,
            }

            # Build transaction
            return self.router.functions.exactInputSingle(params).build_transaction(
                {
                    "from": to,
                    "gas": await self.estimate_gas(
                        amount_in, amount_out_min, path, to, **kwargs
                    ),
                    "nonce": self.web3_manager.w3.eth.get_transaction_count(to), # Use web3_manager
                }
            )
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

    async def get_token_decimals(self, token_address: str) -> int:
        """Get token decimals."""
        if not self.initialized:
            await self.initialize()

        try:
            # Load ERC20 ABI
            with open("abi/erc20.json", "r") as f:
                erc20_abi = json.load(f)

            token_cs = Web3.to_checksum_address(token_address)
            token_contract = self.web3_manager.w3.eth.contract(address=token_cs, abi=erc20_abi)

            # Get decimals
            decimals = token_contract.functions.decimals().call()
            return decimals
        except Exception as e:
            logger.warning(f"Failed to get token decimals for {token_address}: {e}")
            return 18  # Default to 18 decimals

    async def get_token_pairs(self, max_pairs: int = 200) -> List[Any]:
        """Get token pairs from the DEX."""
        if not self.initialized:
            await self.initialize()

        try:
            # Create a dataclass for token pairs
            from dataclasses import dataclass

            @dataclass
            class TokenPair:
                token0_address: str
                token1_address: str
                pool_address: str
                reserve0: Decimal
                reserve1: Decimal
                fee: Decimal
                dex_id: str
                token0_decimals: int = 18
                token1_decimals: int = 18

            # Get supported tokens
            # For Pancakeswap, we'll use common tokens from the config
            supported_tokens = []

            # Add WETH
            weth_address = self.config.get("weth_address")
            if weth_address:
                supported_tokens.append(weth_address)

            # Add other common tokens
            for _, token_data in self.config.get("tokens", {}).items():
                if "address" in token_data:
                    supported_tokens.append(token_data["address"])

            # Get supported fees
            supported_fees = self.config.get("supported_fees", [100, 500, 2500, 10000])

            pairs = []

            # Create a TokenPair object for each valid pair
            for i, token0 in enumerate(supported_tokens):
                for token1 in supported_tokens[i+1:]:
                    for fee in supported_fees:
                        try:
                            # Check if pool exists
                            try:
                                pool_address = await self.get_pool_address(token0, token1, fee=fee)
                            except ValueError:
                                # No pool exists for this pair
                                continue

                            if pool_address and pool_address != "0x0000000000000000000000000000000000000000":
                                # Get pool info
                                pool_info = await self.get_pool_info(pool_address)

                                # Skip if pool info is empty
                                if not pool_info:
                                    continue

                                # Get token decimals
                                token0_decimals = await self.get_token_decimals(token0)
                                token1_decimals = await self.get_token_decimals(token1)

                                # Calculate reserves from liquidity and sqrtPriceX96
                                # This is a simplified calculation for V3 pools
                                liquidity = Decimal(str(pool_info.get("liquidity", 0)))
                                sqrt_price_x96 = Decimal(str(pool_info.get("sqrt_price_x96", 0)))

                                # Calculate reserves (simplified)
                                if sqrt_price_x96 > 0 and liquidity > 0:
                                    reserve0 = liquidity / sqrt_price_x96 * Decimal(2**96)
                                    reserve1 = liquidity * sqrt_price_x96 / Decimal(2**96)
                                else:
                                    reserve0 = Decimal(0)
                                    reserve1 = Decimal(0)

                                # Create a TokenPair object
                                pair = TokenPair(
                                    token0_address=token0,
                                    token1_address=token1,
                                    pool_address=pool_address,
                                    reserve0=reserve0,
                                    reserve1=reserve1,
                                    fee=Decimal(str(pool_info.get("fee", fee))) / Decimal("1000000"),  # Convert to percentage
                                    dex_id=self.id,
                                    token0_decimals=token0_decimals,
                                    token1_decimals=token1_decimals
                                )
                                pairs.append(pair)

                                # Limit the number of pairs
                                if len(pairs) >= max_pairs:
                                    return pairs
                        except Exception as e:
                            logger.debug(f"Error getting pair {token0}/{token1} with fee {fee}: {e}")
                            continue

            return pairs
        except Exception as e:
            logger.error(f"Failed to get token pairs: {e}")
            return []
