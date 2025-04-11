"""Aerodrome V2 DEX implementation."""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Any, Optional
from web3 import Web3
from .base_dex import BaseDEX

logger = logging.getLogger(__name__)


class AerodromeV2(BaseDEX):
    """Aerodrome V2 DEX implementation supporting both stable and volatile pools."""

    def __init__(self, web3: Web3, config: Dict[str, Any]):
        """Initialize Aerodrome V2 DEX."""
        super().__init__(web3, config)

        # Load contract ABIs
        with open("abi/aerodrome_v2_factory.json", "r") as f:
            self.factory_abi = json.load(f)
        with open("abi/aerodrome_v2_router.json", "r") as f:
            self.router_abi = json.load(f)
        with open("abi/aerodrome_v2_pool.json", "r") as f:
            self.pool_abi = json.load(f)

        # Get contract addresses from config
        factory_address = config.get("factory")
        router_address = config.get("router")

        if not factory_address or not router_address:
            raise ValueError("Missing Aerodrome contract addresses")

        # Initialize contracts
        self.factory = self.w3.eth.contract(
            address=factory_address, abi=self.factory_abi
        )
        self.router = self.w3.eth.contract(address=router_address, abi=self.router_abi)

        # Cache for pool info
        self._pool_info_cache: Dict[str, Dict[str, Any]] = {}

    async def get_pool_address(
        self, token_a: str, token_b: str, stable: bool = False
    ) -> str:
        """Get pool address for token pair."""
        try:
            # Sort tokens to match factory's sorting
            token0, token1 = sorted([token_a, token_b])

            # Get pool address
            pool_address = self.factory.functions.getPair(token0, token1, stable).call()

            if pool_address == "0x0000000000000000000000000000000000000000":
                raise ValueError(
                    f"No {'stable' if stable else 'volatile'} pool found for {token_a}/{token_b}"
                )

            return pool_address

        except Exception as e:
            logger.error(f"Failed to get pool address: {e}")
            raise

    async def get_reserves(self, pool_address: str) -> Tuple[Decimal, Decimal]:
        """Get token reserves from pool."""
        try:
            pool = self.w3.eth.contract(address=pool_address, abi=self.pool_abi)

            # Get pool metadata
            metadata = pool.functions.metadata().call()
            decimals_0 = metadata[0]
            decimals_1 = metadata[1]

            # Get reserves
            reserves = pool.functions.getReserves().call()
            reserve_0 = self.from_wei(reserves[0], decimals_0)
            reserve_1 = self.from_wei(reserves[1], decimals_1)

            return reserve_0, reserve_1

        except Exception as e:
            logger.error(f"Failed to get reserves: {e}")
            raise

    async def get_amounts_out(
        self,
        amount_in: Decimal,
        path: List[str],
        stable_path: Optional[List[bool]] = None,
    ) -> List[Decimal]:
        """Calculate output amounts for a given input amount and path."""
        try:
            if stable_path is None:
                # Default to volatile pools
                stable_path = [False] * (len(path) - 1)

            amount_in_wei = self.to_wei(
                amount_in, await self.get_token_decimals(path[0])
            )

            amounts = self.router.functions.getAmountsOut(
                amount_in_wei, path, stable_path
            ).call()

            # Convert amounts to decimals
            result = []
            for i, amount in enumerate(amounts):
                decimals = await self.get_token_decimals(path[i])
                result.append(self.from_wei(amount, decimals))

            return result

        except Exception as e:
            logger.error(f"Failed to get amounts out: {e}")
            raise

    async def get_price_impact(
        self, amount_in: Decimal, amount_out: Decimal, pool_address: str
    ) -> float:
        """Calculate price impact for a trade."""
        try:
            # Get pool info
            pool = self.w3.eth.contract(address=pool_address, abi=self.pool_abi)

            # Get reserves and metadata
            metadata = pool.functions.metadata().call()
            reserves = pool.functions.getReserves().call()

            # Convert to same decimals
            reserve_0 = self.from_wei(reserves[0], metadata[0])
            reserve_1 = self.from_wei(reserves[1], metadata[1])

            # Calculate price impact
            if metadata[4]:  # stable pool
                # Use x^3*y + y^3*x formula
                k_before = (reserve_0**3) * reserve_1 + (reserve_1**3) * reserve_0
                k_after = ((reserve_0 + amount_in) ** 3) * (reserve_1 - amount_out) + (
                    (reserve_1 - amount_out) ** 3
                ) * (reserve_0 + amount_in)
                impact = abs(1 - (k_after / k_before))
            else:
                # Use standard x*y formula
                k_before = reserve_0 * reserve_1
                k_after = (reserve_0 + amount_in) * (reserve_1 - amount_out)
                impact = abs(1 - (k_after / k_before))

            return float(impact)

        except Exception as e:
            logger.error(f"Failed to calculate price impact: {e}")
            raise

    async def get_pool_fee(self, pool_address: str) -> Decimal:
        """Get pool trading fee."""
        try:
            pool = self.w3.eth.contract(address=pool_address, abi=self.pool_abi)
            # Get fee in basis points
            fee_bps = pool.functions.fee().call()
            return (Decimal(str(fee_bps)) / Decimal("1000000")).quantize(
                Decimal("0.000001")
            )  # Convert from basis points to decimal (500 -> 0.0005)

        except Exception as e:
            logger.error(f"Failed to get pool fee: {e}")
            raise

    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """Get pool information including liquidity, volume, etc."""
        try:
            # Check cache first
            if pool_address in self._pool_info_cache:
                return self._pool_info_cache[pool_address]

            pool = self.w3.eth.contract(address=pool_address, abi=self.pool_abi)

            # Get metadata
            metadata = pool.functions.metadata().call()

            # Get reserves
            reserves = pool.functions.getReserves().call()

            # Get tokens
            token0 = metadata[5]
            token1 = metadata[6]

            info = {
                "address": pool_address,
                "token0": token0,
                "token1": token1,
                "decimals0": metadata[0],
                "decimals1": metadata[1],
                "reserve0": self.from_wei(reserves[0], metadata[0]),
                "reserve1": self.from_wei(reserves[1], metadata[1]),
                "stable": metadata[4],
                "fee": (
                    Decimal("0.0001") if metadata[4] else Decimal("0.0005")
                ),  # 0.01% for stable, 0.05% for volatile
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
            # Check factory is not paused
            is_paused = self.factory.functions.isPaused().call()
            if is_paused:
                return False

            # Get pool info
            pool = self.w3.eth.contract(address=pool_address, abi=self.pool_abi)

            # Check reserves
            reserves = pool.functions.getReserves().call()
            if reserves[0] == 0 or reserves[1] == 0:
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
        stable_path: Optional[List[bool]] = None,
    ) -> int:
        """Estimate gas cost for a trade."""
        try:
            if stable_path is None:
                stable_path = [False] * (len(path) - 1)

            amount_in_wei = self.to_wei(
                amount_in, await self.get_token_decimals(path[0])
            )
            amount_out_min_wei = self.to_wei(
                amount_out_min, await self.get_token_decimals(path[-1])
            )

            # Get deadline
            deadline = self.w3.eth.get_block("latest").timestamp + 300  # 5 minutes

            # Estimate gas
            return self.router.functions.swapExactTokensForTokens(
                amount_in_wei, amount_out_min_wei, path, stable_path, to, deadline
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
        stable_path: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        """Build swap transaction."""
        try:
            if stable_path is None:
                stable_path = [False] * (len(path) - 1)

            amount_in_wei = self.to_wei(
                amount_in, await self.get_token_decimals(path[0])
            )
            amount_out_min_wei = self.to_wei(
                amount_out_min, await self.get_token_decimals(path[-1])
            )

            # Build transaction
            return self.router.functions.swapExactTokensForTokens(
                amount_in_wei, amount_out_min_wei, path, stable_path, to, deadline
            ).build_transaction(
                {
                    "from": to,
                    "gas": await self.estimate_gas(
                        amount_in, amount_out_min, path, to, stable_path
                    ),
                    "nonce": self.w3.eth.get_transaction_count(to),
                }
            )

        except Exception as e:
            logger.error(f"Failed to build swap transaction: {e}")
            raise

    async def decode_swap_error(self, error: Exception) -> str:
        """Decode swap error into human readable message."""
        try:
            error_str = str(error)

            if "INSUFFICIENT_OUTPUT_AMOUNT" in error_str:
                return "Insufficient output amount - high slippage or low liquidity"
            elif "EXCESSIVE_INPUT_AMOUNT" in error_str:
                return "Excessive input amount - try smaller trade size"
            elif "EXPIRED" in error_str:
                return "Transaction deadline expired"
            elif "TRANSFER_FAILED" in error_str:
                return "Token transfer failed - check allowance and balance"
            else:
                return f"Unknown error: {error_str}"

        except Exception as e:
            logger.error(f"Failed to decode error: {e}")
            return str(error)
