"""RocketSwap V3 DEX implementation."""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from web3 import Web3

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager


class RocketSwapV3(BaseDEXV3):
    """RocketSwap V3 DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize RocketSwap V3 interface."""
        super().__init__(web3_manager, config)
        self.name = "RocketSwap"

    async def get_quote_from_quoter(
        self, amount_in: int, path: List[str]
    ) -> Optional[int]:
        """Get quote from quoter contract if available."""
        if not self.quoter:
            return None

        try:
            # First try quoteExactInput
            encoded_path = self._encode_path(path)
            contract_func = self.quoter.functions.quoteExactInput(
                encoded_path, amount_in
            )
            result = await self.web3_manager.call_contract_function(contract_func)
            if result:
                return int(result)

            # Fallback to quoteExactInputSingle
            contract_func = self.quoter.functions.quoteExactInputSingle(
                Web3.to_checksum_address(path[0]),  # tokenIn
                Web3.to_checksum_address(path[1]),  # tokenOut
                self.fee,  # fee
                amount_in,  # amountIn
                0,  # sqrtPriceLimitX96 (0 for no limit)
            )
            result = await self.web3_manager.call_contract_function(contract_func)
            if result:
                return int(result)

            return None

        except Exception as e:
            self.logger.error("Failed to get quote: %s", str(e))
            return None

    async def get_quote_with_impact(
        self, amount_in: int, path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get quote with price impact calculation."""
        try:
            # Get quote from quoter
            amount_out = await self.get_quote_from_quoter(amount_in, path)
            if not amount_out:
                return None

            # Calculate price impact
            # Use a smaller amount to get baseline price
            small_amount = amount_in // 1000 if amount_in > 1000 else amount_in
            baseline_out = await self.get_quote_from_quoter(small_amount, path)
            if not baseline_out:
                return None

            # Calculate impact and validate
            try:
                impact = 1 - (int(amount_out) * small_amount) / (
                    int(baseline_out) * amount_in
                )
                if impact < -1 or impact > 1:
                    self.logger.warning("Invalid price impact calculated: %s", impact)
                    return None
            except ZeroDivisionError:
                self.logger.error("Division by zero when calculating price impact")
                return None

            # Get gas estimate from quoter
            try:
                contract_func = self.quoter.functions.quoteExactInputSingle(
                    Web3.to_checksum_address(path[0]),  # tokenIn
                    Web3.to_checksum_address(path[1]),  # tokenOut
                    self.fee,  # fee
                    amount_in,  # amountIn
                    0,  # sqrtPriceLimitX96 (0 for no limit)
                )
                result = await self.web3_manager.call_contract_function(contract_func)
                gas_estimate = int(result) if isinstance(result, str) else 250000
            except Exception as e:
                self.logger.warning("Failed to get gas estimate: %s", str(e))
                gas_estimate = 250000  # Use default if estimate fails

            return {
                "amount_out": str(amount_out),
                "impact": str(float(impact)),  # Convert to float for JSON serialization
                "fee_rate": str(
                    float(self.fee) / 1000000
                ),  # Convert to float to avoid decimal division
                "fee": str(self.fee),  # Include raw fee value
                "estimated_gas": str(
                    gas_estimate
                ),  # Use actual gas estimate from quoter
            }

        except Exception as e:
            self.logger.error("Failed to get quote with impact: %s", str(e))
            return None

    async def get_token_price(self, token_address: str) -> float:
        """Get current price for a token."""
        try:
            # If token is WETH, return 1.0 since price is in WETH
            if token_address.lower() == self.weth_address.lower():
                return 1.0

            # Get quote for 1 token worth of WETH
            amount_in = 10**18  # 1 WETH
            quote = await self.get_quote_from_quoter(
                amount_in, [self.weth_address, token_address]
            )

            if quote:
                # Convert quote to float after ensuring it's a number
                return float(str(quote)) / (10**18)

            return 0.0

        except Exception as e:
            self.logger.error("Failed to get token price: %s", str(e))
            return 0.0

    async def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24-hour trading volume for a token pair."""
        try:
            # Get pool address
            pool_address = await self._get_pool_address(token0, token1)
            if pool_address == "0x0000000000000000000000000000000000000000":
                return Decimal(0)

            # Get pool contract
            pool = await self._get_pool_contract(pool_address)
            if not pool:
                return Decimal(0)

            # Get volume from Swap events in last 24h
            current_block = await self.web3_manager.w3.eth.block_number
            from_block = current_block - 7200  # ~24h of blocks

            # Get events
            events = await self._get_pool_events(pool, "Swap", from_block)

            # Calculate volume
            volume = Decimal(0)
            for event in events:
                amount0 = abs(Decimal(event["args"]["amount0"]))
                amount1 = abs(Decimal(event["args"]["amount1"]))
                volume += max(amount0, amount1)

            return volume

        except Exception as e:
            self.logger.error("Failed to get 24h volume: %s", str(e))
            return Decimal(0)

    async def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pairs."""
        try:
            total_liquidity = Decimal(0)

            # Get event signature
            event_signature = self._get_event_signature("PoolCreated")

            # Get logs using eth_getLogs
            logs = await self.web3_manager.w3.eth.get_logs(
                {
                    "address": self.factory_address,
                    "fromBlock": 0,
                    "toBlock": "latest",
                    "topics": [event_signature],
                }
            )

            # Limit to most recent 100 pools for performance
            for log in logs[-100:]:
                try:
                    # Process log using contract event
                    decoded = await self._process_log(
                        self.factory.events.PoolCreated(), dict(log)
                    )
                    pool_address = Web3.to_checksum_address(decoded["args"]["pool"])
                    pool = await self._get_pool_contract(pool_address)
                    if pool:
                        liquidity = await self._get_pool_liquidity(pool)
                        total_liquidity += liquidity

                except Exception as e:
                    self.logger.warning(
                        "Failed to get liquidity for pool %s: %s", pool_address, str(e)
                    )
                    continue

            return total_liquidity

        except Exception as e:
            self.logger.error("Failed to get total liquidity: %s", str(e))
            return Decimal(0)
