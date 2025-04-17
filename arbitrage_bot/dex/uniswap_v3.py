"""Uniswap V3 DEX implementation."""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Any, Tuple
from web3 import Web3
from ..core.web3.web3_manager import Web3Manager # Import Web3Manager

from .base_dex import BaseDEX

logger = logging.getLogger(__name__)


class UniswapV3(BaseDEX):
    """Uniswap V3 DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]): # Change signature
        """Initialize Uniswap V3."""
        super().__init__(web3_manager, config) # Pass web3_manager
        self.initialized = False # Add initialized flag
        self.factory = None
        self.router = None
        self.quoter = None

    async def initialize(self) -> bool:
        """Initialize Uniswap V3 contracts."""
        if self.initialized:
            return True
        try:
            logger.info(f"Initializing UniswapV3 DEX ({self.id})...")
            # Load contract ABIs
            # TODO: Improve ABI path handling (make relative to project root or config)
            factory_abi = None
            router_abi = None
            quoter_abi = None
            try:
                # TODO: Use Path objects for better path handling
                with open("abi/IUniswapV3Factory.json", "r") as f:
                    factory_abi = json.load(f)
                with open("abi/IUniswapV3Router.json", "r") as f:
                    router_abi = json.load(f)
                # Quoter is optional for some Uniswap V3 forks/deployments
                if "quoter" in self.config:
                    with open("abi/IUniswapV3QuoterV2.json", "r") as f: # Assuming V2 quoter ABI
                        quoter_abi = json.load(f)
            except FileNotFoundError as e:
                 logger.error(f"Missing ABI file for UniswapV3 ({self.id}): {e}")
                 # Allow initialization without quoter if not found but configured
                 if "quoter" in str(e) and "quoter" in self.config:
                     logger.warning("Proceeding without UniswapV3 quoter due to missing ABI.")
                     quoter_abi = None # Ensure it's None
                 else:
                     return False # Fail if factory/router ABI missing
            except Exception as e:
                 logger.error(f"Error loading ABI for UniswapV3 ({self.id}): {e}")
                 return False

            # Initialize contracts
            self.factory = self.web3_manager.w3.eth.contract(address=self.config["factory"], abi=factory_abi)
            self.router = self.web3_manager.w3.eth.contract(address=self.config["router"], abi=router_abi)

            # Initialize quoter only if config and ABI are present
            self.quoter = None
            if quoter_abi and "quoter" in self.config:
                try:
                    self.quoter = self.web3_manager.w3.eth.contract(address=self.config["quoter"], abi=quoter_abi)
                except Exception as e:
                    logger.error(f"Failed to initialize UniswapV3 quoter contract for {self.id}: {e}")
            elif "quoter" in self.config:
                 logger.warning(f"Quoter address provided for {self.id} but ABI failed to load.")
            else:
                 logger.info(f"No quoter configured or ABI found for {self.id}.")


            self.initialized = True
            logger.info(f"UniswapV3 DEX ({self.id}) initialized successfully.")
            return True
        except KeyError as e:
             logger.error(f"Missing key in config for UniswapV3 ({self.id}): {e}")
             return False
        except Exception as e:
            logger.error(f"Failed to initialize UniswapV3 ({self.id}): {e}", exc_info=True)
            return False


    async def get_pool_address(self, token_a: str, token_b: str, **kwargs) -> str:
        """Get pool address for token pair."""
        if not self.initialized: await self.initialize()
        fee = kwargs.get("fee", 3000)  # Default to 0.3% fee tier
        try:
            # Ensure addresses are checksummed
            token_a_cs = Web3.to_checksum_address(token_a)
            token_b_cs = Web3.to_checksum_address(token_b)
            pool = self.factory.functions.getPool(token_a_cs, token_b_cs, fee).call()
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
        if not self.initialized: await self.initialize()
        try:
            # TODO: Cache ABI loading
            with open("abi/IUniswapV3Pool.json", "r") as f:
                pool_abi = json.load(f)
            pool_cs = Web3.to_checksum_address(pool_address)
            pool = self.web3_manager.w3.eth.contract(address=pool_cs, abi=pool_abi) # Use web3_manager

            # Get slot0 data which contains sqrt price
            slot0 = pool.functions.slot0().call()
            sqrt_price_x96 = slot0[0]

            # Get liquidity
            liquidity = pool.functions.liquidity().call()

            # Calculate reserves based on sqrt price and liquidity
            # This is a simplified calculation
            if sqrt_price_x96 == 0: return Decimal(0), Decimal(0) # Avoid division by zero
            price = Decimal(sqrt_price_x96**2) / Decimal(2**192)
            if price == 0: return Decimal(0), Decimal(0) # Avoid division by zero

            # Need decimals to interpret reserves correctly, but they aren't stored here
            # Returning raw liquidity and price for now, needs adjustment based on context
            # reserve0 = Decimal(liquidity) / price
            # reserve1 = Decimal(liquidity) * price
            # Returning simplified values, requires context for proper interpretation
            # TODO: Fetch decimals and return actual reserve amounts
            logger.warning(f"get_reserves for UniswapV3 pool {pool_address} returning simplified liquidity/price due to missing decimals.")
            return Decimal(liquidity), price

        except Exception as e:
            logger.error(f"Failed to get reserves: {e}")
            raise

    async def get_amounts_out(
        self, amount_in: Decimal, path: List[str], **kwargs
    ) -> List[Decimal]:
        """Calculate output amounts for a given input amount and path."""
        if not self.initialized: await self.initialize()
        if not self.quoter:
             logger.error(f"Quoter not initialized for {self.id}, cannot get amounts out.")
             return [amount_in, Decimal(0)]
        try:
            fee = kwargs.get("fee", 3000)
            decimals_in = await self.get_token_decimals(path[0])
            decimals_out = await self.get_token_decimals(path[1])
            amount_in_wei = self.to_wei(amount_in, decimals_in)


            # Use quoter contract to get quote
            # Ensure addresses are checksummed
            token_in_cs = Web3.to_checksum_address(path[0])
            token_out_cs = Web3.to_checksum_address(path[1])

            quote_result = self.quoter.functions.quoteExactInputSingle(
                token_in_cs, token_out_cs, fee, amount_in_wei, 0  # sqrt price limit
            ).call()

            # quoteExactInputSingle returns (amountOut, sqrtPriceX96After, initializedTicksCrossed, gasEstimate)
            amount_out_wei = quote_result[0]
            amount_out = self.from_wei(amount_out_wei, decimals_out)
            return [amount_in, amount_out]
        except Exception as e:
            logger.error(f"Failed to get amounts out for {self.id}: {e}", exc_info=True)
            # Return input amount and zero output on error
            return [amount_in, Decimal(0)]


    async def get_price_impact(
        self, amount_in: Decimal, amount_out: Decimal, pool_address: str
    ) -> float:
        """Calculate price impact for a trade."""
        if not self.initialized: await self.initialize()
        try:
            # Get current price from pool
            # TODO: Cache ABI loading
            with open("abi/IUniswapV3Pool.json", "r") as f:
                pool_abi = json.load(f)
            pool_cs = Web3.to_checksum_address(pool_address)
            pool = self.web3_manager.w3.eth.contract(address=pool_cs, abi=pool_abi) # Use web3_manager
            slot0 = pool.functions.slot0().call()
            if slot0[0] == 0: return 1.0 # Avoid division by zero, max impact

            current_price = Decimal(slot0[0] ** 2) / Decimal(2**192)
            if current_price == 0 or amount_in == 0: return 1.0 # Avoid division by zero

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
        if not self.initialized: await self.initialize()
        try:
            # TODO: Cache ABI loading
            with open("abi/IUniswapV3Pool.json", "r") as f:
                pool_abi = json.load(f)
            pool_cs = Web3.to_checksum_address(pool_address)
            pool = self.web3_manager.w3.eth.contract(address=pool_cs, abi=pool_abi) # Use web3_manager
            fee = pool.functions.fee().call()
            return Decimal(fee) / Decimal(1000000)  # Fee is in hundredths of a bip (1e6)
        except Exception as e:
            logger.error(f"Failed to get pool fee: {e}")
            raise

    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """Get pool information including liquidity, volume, etc."""
        if not self.initialized: await self.initialize()
        try:
            # TODO: Cache ABI loading
            with open("abi/IUniswapV3Pool.json", "r") as f:
                pool_abi = json.load(f)
            pool_cs = Web3.to_checksum_address(pool_address)
            pool = self.web3_manager.w3.eth.contract(address=pool_cs, abi=pool_abi) # Use web3_manager

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
        if not self.initialized: await self.initialize()
        try:
            # TODO: Cache ABI loading
            with open("abi/IUniswapV3Pool.json", "r") as f:
                pool_abi = json.load(f)
            pool_cs = Web3.to_checksum_address(pool_address)
            pool = self.web3_manager.w3.eth.contract(address=pool_cs, abi=pool_abi) # Use web3_manager

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
        if not self.initialized: await self.initialize()
        try:
            fee = kwargs.get("fee", 3000)
            latest_block = await self.web3_manager.w3.eth.get_block("latest") # Use web3_manager
            deadline = kwargs.get(
                "deadline", latest_block.timestamp + 300
            )

            # Convert amounts to wei
            decimals_in = await self.get_token_decimals(path[0])
            decimals_out = await self.get_token_decimals(path[1])
            amount_in_wei = self.to_wei(amount_in, decimals_in)
            amount_out_min_wei = self.to_wei(amount_out_min, decimals_out)


            # Prepare exact input params
            # Ensure addresses are checksummed
            token_in_cs = Web3.to_checksum_address(path[0])
            token_out_cs = Web3.to_checksum_address(path[1])
            recipient_cs = Web3.to_checksum_address(to)

            params = {
                "tokenIn": token_in_cs,
                "tokenOut": token_out_cs,
                "fee": fee,
                "recipient": recipient_cs,
                "deadline": deadline,
                "amountIn": amount_in_wei,
                "amountOutMinimum": amount_out_min_wei,
                "sqrtPriceLimitX96": 0,
            }

            # Estimate gas
            # Need 'from' address for estimation
            from_address = recipient_cs # Assume recipient is sender for estimation
            gas_estimate = await self.router.functions.exactInputSingle(params).estimate_gas({'from': from_address})
            return gas_estimate
        except Exception as e:
            logger.error(f"Failed to estimate gas: {e}", exc_info=True)
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
        if not self.initialized: await self.initialize()
        try:
            fee = kwargs.get("fee", 3000)

            # Convert amounts to wei
            decimals_in = await self.get_token_decimals(path[0])
            decimals_out = await self.get_token_decimals(path[1])
            amount_in_wei = self.to_wei(amount_in, decimals_in)
            amount_out_min_wei = self.to_wei(amount_out_min, decimals_out)


            # Prepare exact input params
            # Ensure addresses are checksummed
            token_in_cs = Web3.to_checksum_address(path[0])
            token_out_cs = Web3.to_checksum_address(path[1])
            recipient_cs = Web3.to_checksum_address(to)

            params = {
                "tokenIn": token_in_cs,
                "tokenOut": token_out_cs,
                "fee": fee,
                "recipient": recipient_cs,
                "deadline": deadline,
                "amountIn": amount_in_wei,
                "amountOutMinimum": amount_out_min_wei,
                "sqrtPriceLimitX96": 0,
            }

            # Build transaction
            # 'from' address is needed for build_transaction
            from_address = recipient_cs # Assuming 'to' is the sender
            nonce = await self.web3_manager.w3.eth.get_transaction_count(from_address) # Use web3_manager
            gas_estimate = await self.estimate_gas(amount_in, amount_out_min, path, to, **kwargs)

            tx_params = {
                "from": from_address,
                "gas": int(gas_estimate * 1.2), # Add buffer
                "nonce": nonce,
                # Add gas price strategy if needed (e.g., maxFeePerGas, maxPriorityFeePerGas)
            }

            return self.router.functions.exactInputSingle(params).build_transaction(tx_params)
        except Exception as e:
            logger.error(f"Failed to build swap transaction: {e}", exc_info=True)
            raise

    async def decode_swap_error(self, error: Exception) -> str:
        """Decode swap error into human readable message."""
        try:
            # Extract revert reason if available
            if hasattr(error, "args") and len(error.args) > 0:
                # Handle potential dictionary in args[0]
                arg0 = error.args[0]
                if isinstance(arg0, dict) and 'message' in arg0:
                    return arg0['message']
                return str(arg0)
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
            # For UniswapV3, we'll use common tokens from the config
            supported_tokens = []

            # Add WETH
            weth_address = self.config.get("weth_address")
            if weth_address:
                supported_tokens.append(weth_address)

            # Add other common tokens
            for token_symbol, token_data in self.config.get("tokens", {}).items():
                if "address" in token_data:
                    supported_tokens.append(token_data["address"])

            # Get supported fees
            supported_fees = self.config.get("supported_fees", [500, 3000, 10000])

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
                                    price = (sqrt_price_x96 / Decimal(2**96))**2
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
