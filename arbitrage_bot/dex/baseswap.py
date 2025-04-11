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
        if self.initialized:
            return True
        try:
            logger.info(f"Initializing Baseswap DEX ({self.id})...")
            # Load contract ABIs
            factory_abi = None
            router_abi = None
            quoter_abi = None
            try:
                # TODO: Use Path objects for better path handling
                with open("abi/baseswap_factory.json", "r") as f:
                    factory_abi = json.load(f)
                with open("abi/baseswap_router_v3.json", "r") as f: # Assuming V3 router ABI
                    router_abi = json.load(f)
                # Only load quoter if present in config (likely for V3)
                if "quoter" in self.config:
                    with open("abi/baseswap_quoter.json", "r") as f:
                        quoter_abi = json.load(f)
            except FileNotFoundError as e:
                 logger.error(f"Missing ABI file for Baseswap ({self.id}): {e}")
                 # Allow initialization without quoter if not found but configured
                 if "quoter" in str(e) and "quoter" in self.config:
                     logger.warning("Proceeding without Baseswap quoter due to missing ABI.")
                     quoter_abi = None # Ensure it's None
                 else:
                     return False # Fail if factory/router ABI missing
            except Exception as e:
                 logger.error(f"Error loading ABI for Baseswap ({self.id}): {e}")
                 return False


            # Initialize contracts
            self.factory = self.web3_manager.w3.eth.contract( # Use web3_manager
                address=self.config["factory"], abi=factory_abi
            )
            self.router = self.web3_manager.w3.eth.contract( # Use web3_manager
                address=self.config["router"], abi=router_abi
            )
            # Only initialize quoter if ABI was loaded and key exists
            self.quoter = None
            if quoter_abi and "quoter" in self.config:
                try:
                    self.quoter = self.web3_manager.w3.eth.contract( # Use web3_manager
                        address=self.config["quoter"], abi=quoter_abi
                    )
                except Exception as e:
                     logger.error(f"Failed to initialize Baseswap quoter contract: {e}")
            elif "quoter" in self.config:
                 logger.warning(f"Quoter address provided for Baseswap ({self.id}) but ABI failed to load.")
            else:
                 logger.info(f"No quoter configured or ABI found for Baseswap ({self.id}).")


            self.initialized = True
            logger.info(f"Baseswap DEX ({self.id}) initialized successfully.")
            return True

        except KeyError as e:
             logger.error(f"Missing key in config for Baseswap ({self.id}): {e}")
             return False
        except Exception as e:
            logger.error(f"Failed to initialize Baseswap ({self.id}): {e}", exc_info=True)
            return False

    async def get_pool_address(self, token_a: str, token_b: str, **kwargs) -> str:
        """Get pool address for token pair."""
        if not self.initialized: await self.initialize()
        try:
            # Baseswap V2 uses getPair
            # TODO: Check config version to call correct factory function if needed
            token_a_cs = Web3.to_checksum_address(token_a)
            token_b_cs = Web3.to_checksum_address(token_b)
            pool = self.factory.functions.getPair(token_a_cs, token_b_cs).call() # Assuming V2 getPair
            if pool == "0x0000000000000000000000000000000000000000":
                raise ValueError(f"No pool exists for {token_a}/{token_b}")
            return pool
        except Exception as e:
            logger.error(f"Failed to get pool address: {e}")
            raise

    async def get_reserves(self, pool_address: str) -> Tuple[Decimal, Decimal]:
        """Get token reserves from pool."""
        if not self.initialized: await self.initialize()
        try:
            # TODO: Cache ABI loading
            with open("abi/baseswap_pair.json", "r") as f: # Assuming V2 pair ABI
                pool_abi = json.load(f)
            pool_cs = Web3.to_checksum_address(pool_address)
            pool = self.web3_manager.w3.eth.contract(address=pool_cs, abi=pool_abi) # Use web3_manager

            # Get reserves directly from pool
            reserves = pool.functions.getReserves().call()
            # TODO: Need decimals to return correct Decimal values
            # Fetch decimals or assume 18 for now
            # token0_addr = pool.functions.token0().call()
            # token1_addr = pool.functions.token1().call()
            # decimals0 = await self.get_token_decimals(token0_addr)
            # decimals1 = await self.get_token_decimals(token1_addr)
            # return (self.from_wei(reserves[0], decimals0), self.from_wei(reserves[1], decimals1))
            logger.warning(f"get_reserves for Baseswap pool {pool_address} returning raw reserves due to missing decimals.")
            return (Decimal(reserves[0]), Decimal(reserves[1]))
        except Exception as e:
            logger.error(f"Failed to get reserves: {e}")
            raise

    async def get_amounts_out(
        self, amount_in: Decimal, path: List[str], **kwargs
    ) -> List[Decimal]:
        """Calculate output amounts for a given input amount and path."""
        if not self.initialized: await self.initialize()
        # Use Router V2 logic as quoter might not exist
        try:
            decimals_in = await self.get_token_decimals(path[0])
            decimals_out = await self.get_token_decimals(path[-1])
            amount_in_wei = self.to_wei(amount_in, decimals_in)

            # Ensure addresses are checksummed
            path_cs = [Web3.to_checksum_address(addr) for addr in path]

            amounts_out_wei = self.router.functions.getAmountsOut(amount_in_wei, path_cs).call()

            amount_out = self.from_wei(amounts_out_wei[-1], decimals_out)
            return [amount_in, amount_out]

        except Exception as e:
            logger.error(f"Failed to get amounts out for {self.id}: {e}", exc_info=True)
            return [amount_in, Decimal(0)]


    async def get_price_impact(
        self, amount_in: Decimal, amount_out: Decimal, pool_address: str
    ) -> float:
        """Calculate price impact for a trade."""
        if not self.initialized: await self.initialize()
        try:
            # TODO: Cache ABI loading
            with open("abi/baseswap_pair.json", "r") as f: # Assuming V2 pair ABI
                pool_abi = json.load(f)
            pool_cs = Web3.to_checksum_address(pool_address)
            pool = self.web3_manager.w3.eth.contract(address=pool_cs, abi=pool_abi) # Use web3_manager

            # Get current reserves
            reserves = pool.functions.getReserves().call()
            # TODO: Need decimals and token order for accurate calculation
            reserve_in = Decimal(reserves[0]) # Simplified assumption
            reserve_out = Decimal(reserves[1]) # Simplified assumption

            if reserve_in == 0: return 1.0 # Avoid division by zero

            # Calculate current price
            current_price = reserve_out / reserve_in

            # Calculate execution price
            if amount_in == 0: return 0.0 # Avoid division by zero
            execution_price = amount_out / amount_in

            # Calculate price impact
            if current_price == 0: return 1.0 # Avoid division by zero
            price_impact = abs(execution_price - current_price) / current_price
            return float(price_impact)
        except Exception as e:
            logger.error(f"Failed to calculate price impact: {e}")
            raise

    async def get_pool_fee(self, pool_address: str) -> Decimal:
        """Get pool trading fee."""
        # Baseswap V2 uses fixed 0.3% fee (adjust if needed)
        return Decimal("0.003")


    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """Get pool information including liquidity, volume, etc."""
        if not self.initialized: await self.initialize()
        try:
            # TODO: Cache ABI loading
            with open("abi/baseswap_pair.json", "r") as f: # Assuming V2 pair ABI
                pool_abi = json.load(f)
            pool_cs = Web3.to_checksum_address(pool_address)
            pool = self.web3_manager.w3.eth.contract(address=pool_cs, abi=pool_abi) # Use web3_manager

            # Get basic pool info
            token0 = pool.functions.token0().call()
            token1 = pool.functions.token1().call()
            reserves = pool.functions.getReserves().call()

            return {
                "token0": token0,
                "token1": token1,
                "reserve0": reserves[0],
                "reserve1": reserves[1],
                "timestamp": reserves[2],
                "fee": 3000,  # 0.3% in basis points
            }
        except Exception as e:
            logger.error(f"Failed to get pool info: {e}")
            raise

    async def validate_pool(self, pool_address: str) -> bool:
        """Validate pool exists and is active."""
        if not self.initialized: await self.initialize()
        try:
            # TODO: Cache ABI loading
            with open("abi/baseswap_pair.json", "r") as f: # Assuming V2 pair ABI
                pool_abi = json.load(f)
            pool_cs = Web3.to_checksum_address(pool_address)
            pool = self.web3_manager.w3.eth.contract(address=pool_cs, abi=pool_abi) # Use web3_manager

            # Check if pool has reserves
            reserves = pool.functions.getReserves().call()
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
        **kwargs,
    ) -> int:
        """Estimate gas cost for a trade."""
        if not self.initialized: await self.initialize()
        try:
            latest_block = await self.web3_manager.w3.eth.get_block("latest") # Use web3_manager
            deadline = latest_block.timestamp + kwargs.get("deadline", 300)

            # Convert amounts to wei
            decimals_in = await self.get_token_decimals(path[0])
            decimals_out = await self.get_token_decimals(path[-1])
            amount_in_wei = self.to_wei(amount_in, decimals_in)
            amount_out_min_wei = self.to_wei(amount_out_min, decimals_out)


            # Prepare exact input params for V2 router
            path_cs = [Web3.to_checksum_address(addr) for addr in path]
            recipient_cs = Web3.to_checksum_address(to)
            from_address = recipient_cs # Assume recipient is sender for estimation

            # Use swapExactTokensForTokens for V2
            gas_estimate = await self.router.functions.swapExactTokensForTokens(
                 amount_in_wei,
                 amount_out_min_wei,
                 path_cs,
                 recipient_cs,
                 deadline
            ).estimate_gas({'from': from_address})

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
            # Convert amounts to wei
            decimals_in = await self.get_token_decimals(path[0])
            decimals_out = await self.get_token_decimals(path[-1])
            amount_in_wei = self.to_wei(amount_in, decimals_in)
            amount_out_min_wei = self.to_wei(amount_out_min, decimals_out)


            # Prepare exact input params for V2 router
            path_cs = [Web3.to_checksum_address(addr) for addr in path]
            recipient_cs = Web3.to_checksum_address(to)
            from_address = recipient_cs # Assuming 'to' is the sender

            # Get nonce
            nonce = await self.web3_manager.w3.eth.get_transaction_count(from_address) # Use web3_manager
            gas_estimate = await self.estimate_gas(amount_in, amount_out_min, path, to, deadline=deadline, **kwargs)

            tx_params = {
                "from": from_address,
                "gas": int(gas_estimate * 1.2), # Add buffer
                "nonce": nonce,
                # Add gas price strategy if needed
            }

            # Use swapExactTokensForTokens for V2
            return self.router.functions.swapExactTokensForTokens(
                 amount_in_wei,
                 amount_out_min_wei,
                 path_cs,
                 recipient_cs,
                 deadline
            ).build_transaction(tx_params)

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
