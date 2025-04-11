"""Enhanced Base DEX V3 abstract class with improved multi-hop capabilities."""

from abc import abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Set
from decimal import Decimal, getcontext
from web3 import Web3
from web3.contract import Contract, AsyncContract
from .base_dex import BaseDEX
from ..web3.web3_manager import Web3Manager
import json
import logging


class BaseDEXV3(BaseDEX):
    """Abstract base class for V3 DEX implementations with enhanced multi-hop support."""

    EVENT_SIGNATURES = {
        "PoolCreated": "PoolCreated(address,address,uint24,int24,address)",
        "Swap": "Swap(address,address,int256,int256,uint160,uint128,int24)",
    }

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize base V3 DEX functionality."""
        super().__init__(web3_manager, config)
        self.quoter_address = config.get("quoter")
        self.quoter = None
        self.fee = config.get("fee", 3000)
        self.tick_spacing = config.get("tick_spacing", 60)

        # Multi-hop path support
        self.supported_fees = config.get("supported_fees", [500, 3000, 10000])

        # Fee tier names for logging
        self.fee_tier_names = {100: "0.01%", 500: "0.05%", 3000: "0.3%", 10000: "1%"}

        # Cache for pool existence
        self._pool_existence_cache: Dict[str, bool] = {}

    async def initialize(self) -> bool:
        """Initialize the V3 DEX interface."""
        try:
            # Initialize router and factory contracts
            self.router = await self.web3_manager.get_contract(
                address=self.router_address, abi_name=self.name.lower() + "_v3_router"
            )
            self.factory = await self.web3_manager.get_contract(
                address=self.factory_address, abi_name=self.name.lower() + "_v3_factory"
            )

            # Initialize quoter if available
            if self.quoter_address:
                self.quoter = await self.web3_manager.get_contract(
                    address=self.quoter_address,
                    abi_name=self.name.lower() + "_v3_quoter",
                )

                # Check if we have the gas optimizer
                if hasattr(self.web3_manager, "gas_optimizer"):
                    self.gas_optimizer = self.web3_manager.gas_optimizer
                else:
                    self.gas_optimizer = None

                self.logger.debug(
                    f"Initialized {self.name} V3 with quoter at {self.quoter_address}"
                )

            self.initialized = True
            return True

        except Exception as e:
            self._handle_error(e, "V3 DEX initialization")
            return False

    def _encode_path(self, path: List[str], fees: Optional[List[int]] = None) -> bytes:
        """
        Encode path for V3 router.

        Args:
            path: List of token addresses
            fees: List of fees for each hop (optional)

        Returns:
            Encoded path bytes
        """
        encoded = b""
        for i, token in enumerate(path):
            encoded += Web3.to_bytes(hexstr=token)
            # Add fee in between tokens
            if i < len(path) - 1:
                # Check if specific fees were provided
                if fees and len(fees) >= i + 1:
                    fee = fees[i]
                # Check if we have a fee list for different hops
                elif isinstance(self.fee, list) and len(self.fee) > i:
                    fee = self.fee[i]
                else:
                    # Use the default fee
                    fee = self.fee if not isinstance(self.fee, list) else self.fee[0]

                # Ensure fee is an integer
                if isinstance(fee, str):
                    fee = int(fee)

                encoded += fee.to_bytes(3, "big")
        return encoded

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
    ):
        """
        Execute a token swap.

        Args:
            amount_in: Input amount
            amount_out_min: Minimum output amount
            path: Token path
            to: Recipient address
            deadline: Transaction deadline
            gas: Gas limit (optional)
            maxFeePerGas: Max fee per gas (optional)
            maxPriorityFeePerGas: Max priority fee per gas (optional)
        """
        try:
            # Validate inputs
            self._validate_state()
            self._validate_path(path)
            self._validate_amounts(amount_in, amount_out_min)

            # Encode path for V3
            # If path has more than 2 tokens, we need to determine optimal fees for each hop
            if len(path) > 2:
                encoded_path = await self._encode_optimal_path(path, amount_in)
            else:
                # For simple swaps, use the default fee
                encoded_path = self._encode_path(path)

            # Build transaction parameters
            params = {
                "path": encoded_path,
                "recipient": Web3.to_checksum_address(to),
                "deadline": deadline,
                "amountIn": amount_in,
                "amountOutMinimum": amount_out_min,
            }

            # Add gas parameters if provided
            tx_params = {}
            if gas is not None:
                tx_params["gas"] = gas
            if maxFeePerGas is not None:
                tx_params["maxFeePerGas"] = maxFeePerGas
            if maxPriorityFeePerGas is not None:
                tx_params["maxPriorityFeePerGas"] = maxPriorityFeePerGas

            # Send transaction
            tx_hash = await self.web3_manager.build_and_send_transaction(
                self.router, "exactInput", params, tx_params=tx_params
            )
            receipt = await self.web3_manager.wait_for_transaction(tx_hash)

            # Log transaction
            self._log_transaction(tx_hash.hex(), amount_in, amount_out_min, path, to)

            return receipt

        except Exception as e:
            self._handle_error(e, "V3 swap")

    @abstractmethod
    async def get_quote_from_quoter(
        self, amount_in: int, path: List[str]
    ) -> Optional[int]:
        """Get quote from quoter contract if available. Should support multi-hop paths."""
        pass

    @abstractmethod
    async def get_quote_with_impact(
        self, amount_in: int, path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get quote with price impact calculation."""
        pass

    @abstractmethod
    async def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24-hour trading volume for a token pair."""
        pass

    @abstractmethod
    async def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pairs."""
        pass

    @abstractmethod
    async def get_token_price(self, token_address: str) -> float:
        """Get current price for a token."""
        pass

    async def get_token_decimals(self, token_address: str) -> int:
        """
        Get token decimals.

        Args:
            token_address: Token address

        Returns:
            Token decimals (default: 18)
        """
        try:
            # Try to get from cached tokens first
            if hasattr(self, "token_decimals") and token_address in self.token_decimals:
                return self.token_decimals[token_address]

            # Otherwise, fetch from contract
            token_contract = await self.web3_manager.get_contract(
                address=token_address, abi_name="ERC20"
            )
            contract_func = token_contract.functions.decimals()
            decimals = await self.web3_manager.call_contract_function(contract_func)
            return decimals
        except Exception as e:
            self.logger.warning(
                f"Failed to get token decimals for {token_address}: {e}"
            )
            return 18  # Default to 18 decimals

    async def _get_pool_address(self, token0: str, token1: str) -> str:
        """Get pool address for token pair."""
        try:
            contract_func = self.factory.functions.getPool(
                Web3.to_checksum_address(token0),
                Web3.to_checksum_address(token1),
                self.fee,
            )
            pool_address = await self.web3_manager.call_contract_function(contract_func)
            return Web3.to_checksum_address(pool_address)
        except Exception as e:
            self.logger.error("Failed to get pool address: %s", str(e))
            return "0x0000000000000000000000000000000000000000"

    async def _get_pool_address_with_fee(
        self, token0: str, token1: str, fee: int
    ) -> str:
        """
        Get pool address for token pair with specific fee.

        Args:
            token0: First token address
            token1: Second token address
            fee: Fee tier (e.g., 500, 3000, 10000)

        Returns:
            Pool address or zero address if not found
        """
        try:
            # Order tokens (lower address first)
            sorted_tokens = sorted(
                [Web3.to_checksum_address(token0), Web3.to_checksum_address(token1)]
            )

            contract_func = self.factory.functions.getPool(
                sorted_tokens[0], sorted_tokens[1], fee
            )
            pool_address = await self.web3_manager.call_contract_function(contract_func)
            return Web3.to_checksum_address(pool_address)
        except Exception as e:
            self.logger.debug(
                f"Failed to get pool address for {token0}/{token1} with fee {fee}: {e}"
            )
            return "0x0000000000000000000000000000000000000000"

    async def _pool_exists(self, token0: str, token1: str, fee: int) -> bool:
        """
        Check if a pool exists for a token pair with specific fee.

        Args:
            token0: First token address
            token1: Second token address
            fee: Fee tier

        Returns:
            True if pool exists
        """
        # Check cache first
        cache_key = f"{token0.lower()}-{token1.lower()}-{fee}"
        if cache_key in self._pool_existence_cache:
            return self._pool_existence_cache[cache_key]

        # Get pool address
        pool_address = await self._get_pool_address_with_fee(token0, token1, fee)

        # Check if pool exists (not zero address)
        exists = pool_address != "0x0000000000000000000000000000000000000000"

        # Cache result
        self._pool_existence_cache[cache_key] = exists

        # If pool exists, also cache the reverse order
        if exists:
            reverse_key = f"{token1.lower()}-{token0.lower()}-{fee}"
            self._pool_existence_cache[reverse_key] = exists

        if exists:
            self.logger.debug(f"Found pool for {token0}/{token1} with fee {fee}")

        return exists

    async def _get_pool_contract(self, pool_address: str) -> Optional[AsyncContract]:
        """Get pool contract instance."""
        try:
            return await self.web3_manager.get_contract(
                address=pool_address, abi_name=self.name.lower() + "_v3_pool"
            )
        except Exception as e:
            self.logger.error("Failed to get pool contract: %s", str(e))
            return None

    async def _get_pool_liquidity(self, pool_contract: AsyncContract) -> Decimal:
        """Get pool liquidity."""
        try:
            contract_func = pool_contract.functions.liquidity()
            liquidity = await self.web3_manager.call_contract_function(contract_func)
            return Decimal(
                str(liquidity)
            )  # Convert to string first to avoid float conversion issues
        except Exception as e:
            self.logger.error("Failed to get pool liquidity: %s", str(e))
            return Decimal(0)

    async def _get_pool_liquidity_by_tokens(
        self, token0: str, token1: str, fee: int = None
    ) -> Decimal:
        """
        Get pool liquidity for token pair.

        Args:
            token0: First token address
            token1: Second token address
            fee: Fee tier (optional)

        Returns:
            Pool liquidity
        """
        try:
            if fee is None:
                fee = self.fee if not isinstance(self.fee, list) else self.fee[0]

            # Get pool address
            pool_address = await self._get_pool_address_with_fee(token0, token1, fee)
            if pool_address == "0x0000000000000000000000000000000000000000":
                return Decimal(0)

            # Get pool contract
            pool_contract = await self._get_pool_contract(pool_address)
            if not pool_contract:
                return Decimal(0)

            # Get liquidity
            return await self._get_pool_liquidity(pool_contract)

        except Exception as e:
            self.logger.error(
                f"Failed to get pool liquidity for {token0}/{token1}: {e}"
            )
            return Decimal(0)

    def _get_event_signature(self, event_name: str) -> str:
        """Get event signature."""
        if event_name not in self.EVENT_SIGNATURES:
            msg = "Unknown event: " + event_name
            raise ValueError(msg)
        signature = self.EVENT_SIGNATURES[event_name]
        return Web3.keccak(text=signature).hex()

    async def _process_log(
        self, event_obj: Any, log_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single event log."""
        try:
            # Convert numeric values in log to strings
            processed_log = {
                "address": log_dict["address"],
                "topics": log_dict["topics"],
                "data": log_dict["data"],
                "blockNumber": str(log_dict["blockNumber"]),
                "transactionHash": (
                    log_dict["transactionHash"].hex()
                    if isinstance(log_dict["transactionHash"], bytes)
                    else log_dict["transactionHash"]
                ),
                "transactionIndex": str(log_dict["transactionIndex"]),
                "blockHash": (
                    log_dict["blockHash"].hex()
                    if isinstance(log_dict["blockHash"], bytes)
                    else log_dict["blockHash"]
                ),
                "logIndex": str(log_dict["logIndex"]),
                "removed": log_dict.get("removed", False),
            }

            # Process log using contract event
            decoded = event_obj.process_log(processed_log)

            # Convert numeric values in args to strings
            if "args" in decoded:
                decoded["args"] = {
                    key: str(value) if isinstance(value, (int, float)) else value
                    for key, value in decoded["args"].items()
                }

            return decoded
        except Exception as e:
            self.logger.warning("Failed to process log: %s", str(e))
            raise

    async def _get_pool_events(
        self,
        pool_contract: AsyncContract,
        event_name: str,
        from_block: int,
        to_block: str = "latest",
    ) -> List[Dict[str, Any]]:
        """Get pool events."""
        try:
            # Get event signature
            event_signature = self._get_event_signature(event_name)

            # Get logs using eth_getLogs
            logs = await self.web3_manager.w3.eth.get_logs(
                {
                    "address": pool_contract.address,
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "topics": [event_signature],
                }
            )

            # Process logs
            events = []
            event_obj = pool_contract.events[event_name]()

            for log in logs:
                try:
                    # Convert log to dict for processing
                    log_dict = dict(log)
                    # Process log
                    decoded = await self._process_log(event_obj, log_dict)
                    events.append(decoded)
                except Exception as e:
                    self.logger.warning("Failed to decode log: %s", str(e))
                    continue

            return events

        except Exception as e:
            self.logger.error("Failed to get pool events: %s", str(e))
            return []

    async def get_multi_hop_quote(
        self, amount_in: int, path: List[str]
    ) -> Optional[int]:
        """
        Get quote for a multi-hop path within the same DEX.

        Args:
            amount_in: Input amount in token units
            path: List of token addresses forming the path

        Returns:
            Expected output amount or None if quote fails
        """
        if not self.quoter:
            return None

        # If only 2 tokens, use simple quote
        if len(path) == 2:
            return await self.get_quote_from_quoter(amount_in, path)

        try:
            # Get best fee combination for the path
            _, fees, output = await self.find_best_path(path[0], path[-1], amount_in)
            if output > 0:
                return output

            # Fallback to default fees
            encoded_path = self._encode_path(path)

            # Get quote using exactInput
            quote_result = await self.web3_manager.call_contract_function(
                self.quoter.functions.quoteExactInput,
                encoded_path,  # bytes path
                amount_in,  # uint256 amountIn
            )

            # Return the output amount
            return (
                quote_result[0]
                if isinstance(quote_result, (list, tuple))
                else quote_result
            )

        except Exception as e:
            self.logger.error("Failed to get multi-hop quote: %s", str(e))
            return None

    async def supports_multi_hop(self) -> bool:
        """
        Check if this DEX supports multi-hop swaps.

        Returns:
            True if multi-hop is supported, False otherwise
        """
        # Check if quoter exists and has quoteExactInput function
        if not self.quoter:
            return False

        try:
            # Check if quoter has quoteExactInput function
            has_exact_input = any(
                func["name"] == "quoteExactInput"
                for func in self.quoter.abi
                if func["type"] == "function"
            )

            return has_exact_input
        except Exception as e:
            self.logger.error("Failed to check multi-hop support: %s", str(e))
            return False

    async def find_best_path(
        self, token_in: str, token_out: str, amount_in: int
    ) -> Tuple[List[str], List[int], int]:
        """
        Find the best path from token_in to token_out.

        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount

        Returns:
            Tuple of (path, fees, estimated output amount)
        """
        # Check direct path first
        best_output = 0
        best_path = [token_in, token_out]
        best_fees = [self.fee] if not isinstance(self.fee, list) else [self.fee[0]]

        try:
            # Get common tokens for intermediate hops
            common_tokens = await self._get_common_tokens()

            # Check all fee tiers for direct path
            for fee in self.supported_fees:
                # Check if pool exists
                if not await self._pool_exists(token_in, token_out, fee):
                    continue

                # Get quote
                output = await self._get_quote_with_fee(
                    token_in, token_out, amount_in, fee
                )
                if output and output > best_output:
                    best_output = output
                    best_fees = [fee]

            # Check one-hop paths through common tokens
            for mid_token in common_tokens:
                # Skip if mid token is input or output
                if (
                    mid_token.lower() == token_in.lower()
                    or mid_token.lower() == token_out.lower()
                ):
                    continue

                # Check for best fee combination
                for fee1 in self.supported_fees:
                    # Check if first hop pool exists
                    if not await self._pool_exists(token_in, mid_token, fee1):
                        continue

                    for fee2 in self.supported_fees:
                        # Check if second hop pool exists
                        if not await self._pool_exists(mid_token, token_out, fee2):
                            continue

                        # Get quotes for individual hops
                        mid_amount = await self._get_quote_with_fee(
                            token_in, mid_token, amount_in, fee1
                        )
                        if not mid_amount or mid_amount == 0:
                            continue

                        out_amount = await self._get_quote_with_fee(
                            mid_token, token_out, mid_amount, fee2
                        )
                        if not out_amount or out_amount == 0:
                            continue

                        # Check if path is better
                        if out_amount > best_output:
                            best_output = out_amount
                            best_path = [token_in, mid_token, token_out]
                            best_fees = [fee1, fee2]
                            self.logger.debug(
                                f"Found better 2-hop path: {best_path} with fees {best_fees}, output: {best_output}"
                            )

            return best_path, best_fees, best_output

        except Exception as e:
            self.logger.error(f"Error finding best path: {e}")
            return (
                [token_in, token_out],
                [self.fee if not isinstance(self.fee, list) else self.fee[0]],
                0,
            )

    async def _encode_optimal_path(self, path: List[str], amount_in: int) -> bytes:
        """
        Encode path with optimal fee tiers.

        Args:
            path: Token path
            amount_in: Input amount

        Returns:
            Encoded path bytes
        """
        try:
            # Get optimal fees for each hop
            optimal_fees = []

            # Loop through hops
            for i in range(len(path) - 1):
                token_in = path[i]
                token_out = path[i + 1]

                # Find best fee for this hop
                best_fee = self.fee if not isinstance(self.fee, list) else self.fee[0]
                best_output = 0

                for fee in self.supported_fees:
                    if await self._pool_exists(token_in, token_out, fee):
                        output = await self._get_quote_with_fee(
                            token_in, token_out, amount_in, fee
                        )
                        if output and output > best_output:
                            best_output = output
                            best_fee = fee

                optimal_fees.append(best_fee)

            # Encode path with optimal fees
            return self._encode_path(path, optimal_fees)
        except Exception as e:
            self.logger.error(f"Error encoding optimal path: {e}")
            return self._encode_path(path)  # Fallback to default encoding

    async def get_multi_hop_gas_estimate(
        self, path: List[str], fees: Optional[List[int]] = None
    ) -> int:
        """
        Estimate gas cost for a multi-hop swap.

        Args:
            path: List of token addresses forming the path
            fees: Optional list of fees for each hop

        Returns:
            Estimated gas cost
        """
        # Use gas optimizer if available
        if hasattr(self, "gas_optimizer") and self.gas_optimizer:
            return await self.gas_optimizer.estimate_multi_hop_gas(path, self.name)
        else:
            # Fallback to simple estimation
            return 180000 + (len(path) - 2) * 50000

    async def _get_common_tokens(self) -> List[str]:
        """
        Get common tokens for path finding.

        Returns:
            List of common token addresses
        """
        # Try to get from config
        common_tokens = self.config.get("common_tokens", [])

        # If not in config, use a default list of common tokens
        if not common_tokens:
            # Use WETH, USDC, USDT, DAI as common intermediary tokens
            common_tokens = [
                self.weth_address,  # WETH
                self.config.get("tokens", {})
                .get("USDC", {})
                .get("address", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),  # USDC
                self.config.get("tokens", {})
                .get("USDT", {})
                .get("address", "0x4D15a3a2286D883AF0AA1B3f21367843FAc63E07"),  # USDT
                self.config.get("tokens", {})
                .get("DAI", {})
                .get("address", "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"),  # DAI
            ]

        # Filter out None or empty addresses
        return [
            token
            for token in common_tokens
            if token and token != "0x0000000000000000000000000000000000000000"
        ]

    async def _get_quote_with_fee(
        self, token_in: str, token_out: str, amount_in: int, fee: int
    ) -> Optional[int]:
        """
        Get quote with specific fee tier.

        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount
            fee: Fee tier

        Returns:
            Output amount or None if quote fails
        """
        try:
            # Check if pool exists
            if not await self._pool_exists(token_in, token_out, fee):
                return None

            # Use appropriate quoter function
            if hasattr(self.quoter.functions, "quoteExactInputSingle"):
                # Use quoteExactInputSingle for V3 quoter
                quote_result = await self.web3_manager.call_contract_function(
                    self.quoter.functions.quoteExactInputSingle,
                    Web3.to_checksum_address(token_in),  # tokenIn
                    Web3.to_checksum_address(token_out),  # tokenOut
                    fee,  # fee
                    amount_in,  # amountIn
                    0,  # sqrtPriceLimitX96 (0 = no limit)
                )

                # Return the output amount
                if isinstance(quote_result, (list, tuple)):
                    return quote_result[0]
                else:
                    return quote_result
            else:
                # For other quoter types, use path encoding
                path = self._encode_path([token_in, token_out], [fee])
                quote_result = await self.web3_manager.call_contract_function(
                    self.quoter.functions.quoteExactInput,
                    path,  # bytes path
                    amount_in,  # uint256 amountIn
                )
                return (
                    quote_result
                    if not isinstance(quote_result, (list, tuple))
                    else quote_result[0]
                )
        except Exception as e:
            self.logger.debug(
                f"Failed to get quote for {token_in}/{token_out} with fee {fee}: {e}"
            )
            return None
