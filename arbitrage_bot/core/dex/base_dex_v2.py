"""Base class for V2 DEX implementations."""

from typing import Dict, Any, List, Optional
from web3.types import TxReceipt
from decimal import Decimal
from web3 import Web3
import asyncio

from .base_dex import BaseDEX
from ..web3.web3_manager import Web3Manager


class BaseDEXV2(BaseDEX):
    """Base class implementing V2 DEX-specific functionality."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize V2 DEX interface."""
        super().__init__(web3_manager, config)
        self.fee = config.get("fee", 3000)  # 0.3% default fee for most V2 DEXs
        self.pair_abi = None
        self.weth_address = Web3.to_checksum_address(config["weth_address"])

        # Checksum addresses
        self.router_address = Web3.to_checksum_address(self.router_address)
        self.factory_address = Web3.to_checksum_address(self.factory_address)

    async def initialize(self) -> bool:
        """Initialize the V2 DEX interface."""
        try:
            # Load contract ABIs
            self.router_abi = await self.web3_manager._load_abi(
                self.name.lower() + "_router"
            )
            self.factory_abi = await self.web3_manager._load_abi(
                self.name.lower() + "_factory"
            )
            self.pair_abi = await self.web3_manager._load_abi(
                self.name.lower() + "_pair"
            )

            # Initialize contracts with checksummed addresses
            self.router = await self.web3_manager.get_contract(
                address=self.router_address, abi_name=self.name.lower() + "_router"
            )
            self.factory = await self.web3_manager.get_contract(
                address=self.factory_address, abi_name=self.name.lower() + "_factory"
            )

            # Initialize contracts
            self.initialized = True
            self.logger.info("%s interface initialized", self.name)
            return True

        except Exception as e:
            self._handle_error(e, "V2 DEX initialization")
            return False

    async def get_quote_with_impact(
        self, amount_in: int, path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get quote with price impact analysis for V2 pools."""
        try:
            # Validate inputs
            self._validate_path(path)
            self._validate_amounts(amount_in=amount_in)

            # Get pair address
            pair_address = await self._retry_async(
                self.web3_manager.call_contract_function,
                self.factory.functions.getPair,
                path[0],
                path[1],
                retries=3,
            )

            if pair_address == "0x0000000000000000000000000000000000000000":
                return None

            # Get pair contract
            pair = await self.web3_manager.get_contract(
                address=Web3.to_checksum_address(pair_address),
                abi_name=self.name.lower() + "_pair",
            )

            # Get reserves and token0 concurrently
            reserves, token0 = await asyncio.gather(
                self._retry_async(
                    self.web3_manager.call_contract_function,
                    pair.functions.getReserves,
                    retries=3,
                ),
                self._retry_async(
                    self.web3_manager.call_contract_function,
                    pair.functions.token0,
                    retries=3,
                ),
            )

            # Determine which reserve corresponds to which token
            if path[0].lower() == token0.lower():
                reserve_in = int(str(reserves[0]))
                reserve_out = int(str(reserves[1]))
            else:
                reserve_in = int(str(reserves[1]))
                reserve_out = int(str(reserves[0]))

            if reserve_in == 0 or reserve_out == 0:
                return None

            # Calculate amounts
            amount_out = self._get_amount_out(amount_in, reserve_in, reserve_out)

            # Calculate price impact
            price_impact = self._calculate_price_impact(
                amount_in, amount_out, reserve_in, reserve_out
            )

            return {
                "amount_in": amount_in,
                "amount_out": amount_out,
                "price_impact": price_impact,
                "liquidity_depth": min(reserve_in, reserve_out),
                "fee_rate": self.fee / 1000000,  # Convert from basis points
                "estimated_gas": 150000,  # Base estimate for V2 swap
                "min_out": int(amount_out * 0.995),  # 0.5% slippage default
            }

        except Exception as e:
            self._handle_error(e, "V2 quote calculation")
            return None

    async def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int,
        gas: Optional[int] = None,
        maxFeePerGas: Optional[int] = None,
        maxPriorityFeePerGas: Optional[int] = None,
    ) -> TxReceipt:
        """Execute a V2 swap."""
        try:
            # Use provided recipient address
            recipient = to
            self.logger.info("Using provided recipient address: %s", recipient)

            # Validate inputs
            self._validate_path(path)
            self._validate_amounts(amount_in, amount_out_min)

            # Get initial balances
            token_in_contract = await self.web3_manager.get_token_contract(path[0])
            token_out_contract = await self.web3_manager.get_token_contract(path[-1])

            balance_in_before = await self.web3_manager.call_contract_function(
                token_in_contract.functions.balanceOf, recipient
            )
            balance_out_before = await self.web3_manager.call_contract_function(
                token_out_contract.functions.balanceOf, recipient
            )

            # Get quote for gas estimation
            quote = await self.get_quote_with_impact(amount_in, path)
            if not quote:
                raise Exception("Failed to get quote for swap")

            # Execute swap using web3_manager
            # Calculate gas limit
            gas_limit = gas or int(
                quote["estimated_gas"] * 1.2
            )  # 20% buffer if not specified

            # Get gas parameters if not provided
            if not all([maxFeePerGas, maxPriorityFeePerGas]):
                block = await self.web3_manager.w3.eth.get_block("latest")
                maxFeePerGas = maxFeePerGas or block["baseFeePerGas"] * 2
                maxPriorityFeePerGas = (
                    maxPriorityFeePerGas
                    or await self.web3_manager.w3.eth.max_priority_fee
                )

            receipt = await self.web3_manager.build_and_send_transaction(
                self.router,
                "swapExactTokensForTokens",
                amount_in,
                amount_out_min,
                path,
                recipient,  # Use our wallet address
                deadline,
                value=0,  # No ETH value for token swaps
                gas=gas_limit,
                maxFeePerGas=maxFeePerGas,
                maxPriorityFeePerGas=maxPriorityFeePerGas,
            )

            if not receipt:
                self.logger.error("No receipt returned from transaction")
                return None

            if receipt and receipt["status"] == 1:
                # Get balances after trade
                balance_in_after = await self.web3_manager.call_contract_function(
                    token_in_contract.functions.balanceOf, recipient
                )
                balance_out_after = await self.web3_manager.call_contract_function(
                    token_out_contract.functions.balanceOf, recipient
                )

                # Verify balance changes
                in_diff = balance_in_before - balance_in_after
                out_diff = balance_out_after - balance_out_before

                if in_diff <= 0 or out_diff <= 0:
                    self.logger.error(
                        "Balance verification failed: in_diff=%s, out_diff=%s, expected_min_out=%s",
                        in_diff,
                        out_diff,
                        amount_out_min,
                    )
                    return None

                # Log transaction
                self._log_transaction(
                    receipt["transactionHash"].hex(),
                    amount_in,
                    out_diff,  # Use actual output amount
                    path,
                    recipient,
                )

                return receipt
            else:
                self.logger.error("Transaction failed or returned invalid receipt")
                return None

        except Exception as e:
            self._handle_error(e, "V2 swap execution")
            return None

    def _get_amount_out(self, amount_in: int, reserve_in: int, reserve_out: int) -> int:
        """Calculate output amount for V2 pools."""
        amount_in_with_fee = amount_in * (10000 - self.fee)
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in * 10000 + amount_in_with_fee
        return numerator // denominator

    def _calculate_price_impact(
        self, amount_in: int, amount_out: int, reserve_in: int, reserve_out: int
    ) -> float:
        """Calculate price impact percentage for V2 pools."""
        try:
            # Calculate price before trade
            price_before = Decimal(str(reserve_out)) / Decimal(str(reserve_in))

            # Calculate expected output without impact
            expected_out = Decimal(str(amount_in)) * price_before

            # Calculate actual price impact
            impact = (expected_out - Decimal(str(amount_out))) / expected_out

            # Adjust impact based on liquidity depth
            liquidity_factor = min(1, amount_in / reserve_in)
            adjusted_impact = impact * liquidity_factor

            return float(adjusted_impact)

        except Exception as e:
            self.logger.error("Failed to calculate price impact: %s", str(e))
            return 1.0  # Return 100% impact on error (will prevent trade)

    async def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24h trading volume for a token pair."""
        try:
            # Get pair address
            pair_address = await self._retry_async(
                self.web3_manager.call_contract_function,
                self.factory.functions.getPair,
                token0,
                token1,
                retries=3,
            )

            if pair_address == "0x0000000000000000000000000000000000000000":
                return Decimal("0")

            # Get pair contract
            pair = await self.web3_manager.get_contract(
                address=Web3.to_checksum_address(pair_address),
                abi_name=self.name.lower() + "_pair",
            )

            # Get reserves
            reserves = await self._retry_async(
                self.web3_manager.call_contract_function,
                pair.functions.getReserves,
                retries=3,
            )

            # Calculate volume (simplified - actual implementation would track events)
            volume = Decimal(str(reserves[0])) + Decimal(str(reserves[1]))
            return volume

        except Exception as e:
            self.logger.error("Failed to get 24h volume: %s", str(e))
            return Decimal("0")

    async def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pairs."""
        try:
            # Get all pairs (simplified - actual implementation would track all pairs)
            total_liquidity = Decimal("0")
            return total_liquidity

        except Exception as e:
            self.logger.error("Failed to get total liquidity: %s", str(e))
            return Decimal("0")

    async def get_token_price(self, token_address: str) -> float:
        """Get current token price."""
        try:
            # If token is WETH, return 1.0 since price is in WETH
            if token_address.lower() == self.weth_address.lower():
                return 1.0

            # Get pair address
            pair_address = await self._retry_async(
                self.web3_manager.call_contract_function,
                self.factory.functions.getPair,
                token_address,
                self.weth_address,
                retries=3,
            )

            if pair_address == "0x0000000000000000000000000000000000000000":
                return 0.0

            # Get pair contract
            pair = await self.web3_manager.get_contract(
                address=Web3.to_checksum_address(pair_address),
                abi_name=self.name.lower() + "_pair",
            )

            # Get reserves and token0 concurrently
            reserves, token0 = await asyncio.gather(
                self._retry_async(
                    self.web3_manager.call_contract_function,
                    pair.functions.getReserves,
                    retries=3,
                ),
                self._retry_async(
                    self.web3_manager.call_contract_function,
                    pair.functions.token0,
                    retries=3,
                ),
            )

            # Determine which reserve corresponds to which token
            if token_address.lower() == token0.lower():
                token_reserve = Decimal(str(reserves[0]))
                weth_reserve = Decimal(str(reserves[1]))
            else:
                token_reserve = Decimal(str(reserves[1]))
                weth_reserve = Decimal(str(reserves[0]))

            if token_reserve == 0 or weth_reserve == 0:
                return 0.0

            # Calculate price in WETH
            price = float(weth_reserve / token_reserve)
            return float(price)

        except Exception as e:
            self.logger.error("Failed to get token price: %s", str(e))
            return 0.0
