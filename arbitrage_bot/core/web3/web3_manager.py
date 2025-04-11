"""
Web3 Manager Implementation

This module provides Web3 functionality with proper async handling and
retry mechanisms.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from web3 import Web3, AsyncWeb3
from web3.contract import Contract
from web3.types import RPCEndpoint, RPCResponse

logger = logging.getLogger(__name__)


class Web3Manager:
    """
    Manager for Web3 interactions.

    This class provides:
    - Async Web3 initialization
    - Connection management
    - Transaction handling
    - Gas price estimation
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Web3 manager.

        Args:
            config: Web3 configuration
        """
        self._config = config

        # Configuration
        self._rpc_url = config.get("rpc_url", "https://mainnet.base.org") # Added default
        self._chain_id = config.get("chain_id", 8453) # Added default
        self._retry_count = config.get("retry_count", 3)
        self._retry_delay = config.get("retry_delay", 1.0)
        self._timeout = config.get("timeout", 30)

        # State
        self._web3: Optional[AsyncWeb3] = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the Web3 manager."""
        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing Web3 manager")

            try:
                # Create async Web3 instance
                self._web3 = AsyncWeb3(
                    AsyncWeb3.AsyncHTTPProvider(
                        self._rpc_url, request_kwargs={"timeout": self._timeout}
                    )
                )

                # Add custom middleware for POA chains
                # TODO: Confirm if Base (8453) needs POA middleware
                # if self._chain_id in (56, 97, 137, 80001):  # BSC, Polygon
                #     # Create custom POA middleware
                #     async def poa_middleware(make_request: Any, web3: AsyncWeb3) -> Any:
                #         async def middleware(
                #             method: RPCEndpoint, params: Any
                #         ) -> RPCResponse:
                #             # Add extraData field to block parameters
                #             if method == "eth_getBlockByNumber":
                #                 response = await make_request(method, params)
                #                 if "result" in response and response["result"]:
                #                     if "extraData" not in response["result"]:
                #                         response["result"]["extraData"] = "0x"
                #                 return response
                #             return await make_request(method, params)
                #
                #         return middleware
                #
                #     # Add middleware
                #     self._web3.middleware_onion.inject(poa_middleware, layer=0)

                # Verify connection
                if not await self._web3.is_connected():
                    raise ConnectionError(f"Failed to connect to {self._rpc_url}")

                # Verify chain ID
                chain_id = await self._web3.eth.chain_id
                if chain_id != self._chain_id:
                    raise ValueError(
                        f"Wrong chain ID: expected {self._chain_id}, got {chain_id}"
                    )

                self._initialized = True
                logger.info(f"Web3 manager initialized on chain {self._chain_id}")

            except Exception as e:
                logger.error(f"Failed to initialize Web3 manager: {e}", exc_info=True)
                raise

    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            if not self._initialized:
                return

            logger.info("Cleaning up Web3 manager")

            if self._web3 and self._web3.provider:
                try:
                    # Check if provider has close method (AsyncHTTPProvider does)
                    if hasattr(self._web3.provider, 'close'):
                        await self._web3.provider.close()
                except Exception as e:
                    logger.error(f"Error closing web3 provider: {e}")


            self._initialized = False

    @property
    def w3(self) -> AsyncWeb3:
        """Get the Web3 instance."""
        if not self._initialized or not self._web3:
            raise RuntimeError("Web3 manager not initialized")
        return self._web3

    async def get_gas_price(self) -> int:
        """
        Get current gas price.

        Returns:
            Gas price in wei
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")

        for attempt in range(self._retry_count):
            try:
                return await self.w3.eth.gas_price
            except Exception as e:
                 if "429" in str(e) or "Too Many Requests" in str(e):
                     if attempt < self._retry_count - 1:
                         delay = self._retry_delay * (2**attempt)
                         logger.warning(f"Rate limit hit getting gas price. Retrying in {delay:.2f}s...")
                         await asyncio.sleep(delay)
                     else:
                         logger.error(f"Rate limit persists after {self._retry_count} attempts getting gas price.")
                         raise # Re-raise after final attempt
                 else:
                     logger.error(f"Error getting gas price: {e}", exc_info=True)
                     raise # Re-raise other errors immediately
        # Should not be reached if retries fail, as error is re-raised
        raise RuntimeError("Failed to get gas price after retries.")


    async def estimate_gas(self, transaction: Dict[str, Any]) -> int:
        """
        Estimate gas for a transaction.

        Args:
            transaction: Transaction parameters

        Returns:
            Gas estimate in wei
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")

        # Remove gasPrice if present, use EIP-1559 fields if available
        tx_copy = transaction.copy()
        tx_copy.pop('gasPrice', None)

        for attempt in range(self._retry_count):
            try:
                return await self.w3.eth.estimate_gas(tx_copy)
            except Exception as e:
                 if "429" in str(e) or "Too Many Requests" in str(e):
                     if attempt < self._retry_count - 1:
                         delay = self._retry_delay * (2**attempt)
                         logger.warning(f"Rate limit hit estimating gas. Retrying in {delay:.2f}s...")
                         await asyncio.sleep(delay)
                     else:
                         logger.error(f"Rate limit persists after {self._retry_count} attempts estimating gas.")
                         raise # Re-raise after final attempt
                 else:
                     # Log specific revert reasons if available
                     if 'revert' in str(e).lower() or 'execution reverted' in str(e).lower():
                         logger.warning(f"Gas estimation failed (revert likely): {e}. Tx: {tx_copy}")
                     else:
                        logger.error(f"Error estimating gas: {e}", exc_info=True)
                     raise # Re-raise other errors immediately
        raise RuntimeError("Failed to estimate gas after retries.")


    async def send_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Send a transaction.

        Args:
            transaction: Transaction parameters

        Returns:
            Transaction hash
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")

        for attempt in range(self._retry_count):
            try:
                # Update gas price if not set (prefer EIP-1559 if supported)
                # TODO: Add EIP-1559 fee logic if needed
                if "gasPrice" not in transaction and "maxFeePerGas" not in transaction:
                    transaction["gasPrice"] = await self.get_gas_price()

                # Estimate gas if not set
                if "gas" not in transaction:
                    gas_estimate = await self.estimate_gas(transaction)
                    transaction["gas"] = int(gas_estimate * 1.1)  # 10% buffer

                # Send transaction
                tx_hash = await self.w3.eth.send_transaction(transaction)
                return tx_hash.hex()

            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                     if attempt < self._retry_count - 1:
                         delay = self._retry_delay * (2**attempt)
                         logger.warning(f"Rate limit hit sending transaction. Retrying in {delay:.2f}s...")
                         await asyncio.sleep(delay)
                     else:
                         logger.error(f"Rate limit persists after {self._retry_count} attempts sending transaction.")
                         raise # Re-raise after final attempt
                else:
                    logger.error(
                        f"Failed to send transaction (attempt {attempt + 1}): {e}",
                        exc_info=True,
                    )
                    raise # Re-raise other errors immediately
        raise RuntimeError("Failed to send transaction after retries.")


    async def get_transaction_receipt(
        self, tx_hash: str, timeout: float = None
    ) -> Dict[str, Any]:
        """
        Get transaction receipt.

        Args:
            tx_hash: Transaction hash
            timeout: Maximum time to wait in seconds

        Returns:
            Transaction receipt
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")

        timeout = timeout or self._timeout * self._retry_count # Adjust timeout based on retries
        deadline = asyncio.get_event_loop().time() + timeout

        while True:
            try:
                receipt = await self.w3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    return receipt

            except exceptions.TransactionNotFound:
                 logger.debug(f"Transaction {tx_hash} not found yet...")
            except Exception as e:
                # Handle potential rate limiting here too
                if "429" in str(e) or "Too Many Requests" in str(e):
                     logger.warning(f"Rate limit hit getting receipt for {tx_hash}. Waiting...")
                     # Wait longer if rate limited before checking deadline
                     await asyncio.sleep(self._retry_delay * 2) # Wait longer than standard sleep
                else:
                    logger.warning(f"Error getting receipt for {tx_hash}: {e}")

            if asyncio.get_event_loop().time() > deadline:
                raise TimeoutError(
                    f"Timeout waiting for receipt of transaction {tx_hash}"
                )

            await asyncio.sleep(1) # Standard wait between checks

    async def get_quote(
        self,
        factory: str,
        token_in: str,
        token_out: str,
        amount: str,
        version: str = "v3",  # Default to v3 for backward compatibility
    ) -> int:
        """
        Get quote from a DEX pool.

        Args:
            factory: Factory contract address
            token_in: Input token address
            token_out: Output token address
            amount: Amount of input token in wei
            version: DEX version ('v2' or 'v3')

        Returns:
            Quote amount in output token decimals
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")

        # Factory contract ABI (minimal for getPool/getPair)
        v3_factory_abi = [{"inputs": [{"internalType": "address", "name": "tokenA", "type": "address"},{"internalType": "address", "name": "tokenB", "type": "address"},{"internalType": "uint24", "name": "fee", "type": "uint24"}],"name": "getPool","outputs": [{"internalType": "address", "name": "pool", "type": "address"}],"stateMutability": "view","type": "function"}]
        v2_factory_abi = [{"constant": True,"inputs": [{"internalType": "address", "name": "tokenA", "type": "address"},{"internalType": "address", "name": "tokenB", "type": "address"}],"name": "getPair","outputs": [{"internalType": "address", "name": "pair", "type": "address"}],"payable": False,"stateMutability": "view","type": "function"}]
        # Pool contract ABIs (minimal needed)
        v3_pool_abi = [{"inputs": [],"name": "slot0","outputs": [{"internalType": "uint160","name": "sqrtPriceX96","type": "uint160"},{"internalType": "int24","name": "tick","type": "int24"}],"stateMutability": "view","type": "function"},{"inputs": [],"name": "liquidity","outputs": [{"internalType": "uint128","name": "","type": "uint128"}],"stateMutability": "view","type": "function"}]
        v2_pair_abi = [{"constant": True,"inputs": [],"name": "getReserves","outputs": [{"internalType": "uint112","name": "_reserve0","type": "uint112"},{"internalType": "uint112","name": "_reserve1","type": "uint112"},{"internalType": "uint32","name": "_blockTimestampLast","type": "uint32"}],"payable": False,"stateMutability": "view","type": "function"},{"constant": True,"inputs": [],"name": "token0","outputs": [{"internalType": "address","name": "","type": "address"}],"payable": False,"stateMutability": "view","type": "function"},{"constant": True,"inputs": [],"name": "token1","outputs": [{"internalType": "address","name": "","type": "address"}],"payable": False,"stateMutability": "view","type": "function"}]

        try:
            # Verify factory contract exists and has code
            factory_cs = Web3.to_checksum_address(factory)
            code = await self.w3.eth.get_code(factory_cs)
            if code == "0x" or code == b"0x":
                logger.error(f"No contract code at factory address {factory_cs}")
                raise ValueError(f"No contract code at factory address {factory_cs}")

            logger.debug(f"Contract code exists at factory address {factory_cs}")

            # Convert parameters
            amount_wei = int(amount)
            token_in_cs = Web3.to_checksum_address(token_in)
            token_out_cs = Web3.to_checksum_address(token_out)

            # Sort tokens
            token0, token1 = sorted([token_in_cs, token_out_cs])
            zeroForOne = token_in_cs == token0

            best_quote = 0

            if version == "v3":
                factory_contract = self.w3.eth.contract(
                    address=factory_cs, abi=v3_factory_abi
                )
                fee_tiers = [100, 500, 3000, 10000] # TODO: Make configurable?
                for fee in fee_tiers:
                    pool_address = None
                    # --- Add Retry Logic for getPool ---
                    for attempt in range(self._retry_count):
                         try:
                             logger.debug(f"Checking V3 pool (attempt {attempt+1}) for tokens {token0}, {token1} with fee {fee}")
                             pool_address = await factory_contract.functions.getPool(
                                 token0, token1, fee
                             ).call()
                             break # Success
                         except Exception as e:
                             if "429" in str(e) or "Too Many Requests" in str(e):
                                 if attempt < self._retry_count - 1:
                                     delay = self._retry_delay * (2**attempt)
                                     logger.warning(f"Rate limit hit getting V3 pool. Retrying in {delay:.2f}s...")
                                     await asyncio.sleep(delay)
                                 else:
                                     logger.error(f"Rate limit persists after {self._retry_count} attempts getting V3 pool.")
                                     pool_address = None; break
                             else:
                                 logger.warning(f"Error getting V3 pool (attempt {attempt+1}): {e}")
                                 pool_address = None; break
                    # --- End Retry Logic ---

                    if pool_address in ("0x0000000000000000000000000000000000000000", "0x", None):
                        logger.debug(f"No V3 pool found for fee tier {fee}")
                        continue
                    logger.debug(f"Found V3 pool at {pool_address} with fee {fee}")

                    pool_code = await self.w3.eth.get_code(pool_address)
                    if pool_code == "0x" or pool_code == b"0x":
                        logger.debug(f"No contract code at V3 pool address {pool_address}")
                        continue

                    try:
                        pool = self.w3.eth.contract(address=pool_address, abi=v3_pool_abi)
                        # --- Add Retry Logic for V3 pool calls if needed ---
                        slot0 = await pool.functions.slot0().call()
                        liquidity = await pool.functions.liquidity().call()
                        # --- End Retry Logic ---

                        if liquidity == 0:
                            logger.debug(f"V3 Pool {pool_address} has no liquidity")
                            continue

                        sqrt_price_x96 = slot0[0]
                        if sqrt_price_x96 == 0: continue # Avoid division by zero

                        # Simplified quote calculation
                        quote = (
                            (amount_wei * sqrt_price_x96) // (1 << 96)
                            if zeroForOne
                            else (amount_wei * (1 << 96)) // sqrt_price_x96
                        )
                        logger.debug(f"Got V3 quote {quote} from pool {pool_address}")
                        best_quote = max(best_quote, quote)

                    except Exception as e:
                        logger.warning(f"Error getting data from V3 pool {pool_address}: {e}")
                        continue

            elif version == "v2":
                factory_contract = self.w3.eth.contract(
                    address=factory_cs, abi=v2_factory_abi
                )
                pair_address = None
                # --- Add Retry Logic for getPair ---
                for attempt in range(self._retry_count):
                    try:
                        logger.debug(f"Checking V2 pair (attempt {attempt+1}) for tokens {token0}, {token1}")
                        pair_address = await factory_contract.functions.getPair(
                            token0, token1
                        ).call()
                        break # Success
                    except Exception as e:
                        if "429" in str(e) or "Too Many Requests" in str(e):
                            if attempt < self._retry_count - 1:
                                delay = self._retry_delay * (2**attempt)
                                logger.warning(f"Rate limit hit getting V2 pair. Retrying in {delay:.2f}s...")
                                await asyncio.sleep(delay)
                            else:
                                logger.error(f"Rate limit persists after {self._retry_count} attempts getting V2 pair.")
                                pair_address = None; break
                        else:
                            logger.warning(f"Error getting V2 pair (attempt {attempt+1}): {e}")
                            pair_address = None; break
                # --- End Retry Logic ---

                if pair_address in ("0x0000000000000000000000000000000000000000", "0x", None):
                    logger.debug(f"No V2 pair found for tokens {token0}, {token1} after retries.")
                else:
                    logger.debug(f"Found V2 pair at {pair_address}")
                    pair_code = await self.w3.eth.get_code(pair_address)
                    if pair_code == "0x" or pair_code == b"0x":
                        logger.debug(f"No contract code at V2 pair address {pair_address}")
                    else:
                        pair_contract = self.w3.eth.contract(address=pair_address, abi=v2_pair_abi)
                        # --- Add Retry Logic for getReserves ---
                        reserves = None
                        for attempt in range(self._retry_count):
                            try:
                                reserves = await pair_contract.functions.getReserves().call()
                                break # Success
                            except Exception as e:
                                if "429" in str(e) or "Too Many Requests" in str(e):
                                     if attempt < self._retry_count - 1:
                                        delay = self._retry_delay * (2**attempt)
                                        logger.warning(f"Rate limit hit getting V2 reserves. Retrying in {delay:.2f}s...")
                                        await asyncio.sleep(delay)
                                     else:
                                        logger.error(f"Rate limit persists after {self._retry_count} attempts getting V2 reserves.")
                                        reserves = None; break
                                else:
                                    logger.warning(f"Error reading V2 pair reserves (attempt {attempt+1}) {pair_address}: {e}")
                                    reserves = None; break
                        # --- End Retry Logic ---

                        if reserves:
                            reserve0, reserve1 = reserves[0], reserves[1]
                            if reserve0 == 0 or reserve1 == 0:
                                logger.debug(f"V2 Pair {pair_address} has zero reserves")
                            else:
                                pair_token0 = None
                                # --- Add Retry Logic for token0 call ---
                                for attempt in range(self._retry_count):
                                    try:
                                        pair_token0 = await pair_contract.functions.token0().call()
                                        break # Success
                                    except Exception as e:
                                        if "429" in str(e) or "Too Many Requests" in str(e):
                                            if attempt < self._retry_count - 1:
                                                delay = self._retry_delay * (2**attempt)
                                                logger.warning(f"Rate limit hit calling token0 on V2 pair {pair_address}. Retrying in {delay:.2f}s...")
                                                await asyncio.sleep(delay)
                                            else:
                                                logger.error(f"Rate limit persists after {self._retry_count} attempts calling token0 on V2 pair {pair_address}.")
                                                pair_token0 = None; break # Exit loop after final attempt fails
                                        else:
                                            logger.warning(f"Error calling token0 on V2 pair {pair_address} (attempt {attempt+1}): {e}")
                                            pair_token0 = None; break # Exit loop on non-rate-limit errors
                                # --- End Retry Logic ---

                                if pair_token0 is not None: # Proceed only if token0 call succeeded
                                    if token_in_cs == pair_token0:
                                        reserve_in, reserve_out = reserve0, reserve1
                                    else:
                                        reserve_in, reserve_out = reserve1, reserve0

                                    amount_in_with_fee = amount_wei * 997 # Assume 0.3% fee
                                    numerator = amount_in_with_fee * reserve_out
                                    denominator = (reserve_in * 1000) + amount_in_with_fee
                                    if denominator == 0: quote = 0
                                    else: quote = numerator // denominator

                                    logger.debug(f"Got V2 quote {quote} from pair {pair_address}")
                                    best_quote = max(best_quote, quote)


            else:
                logger.error(f"Unsupported DEX version: {version}")

            if best_quote > 0:
                return best_quote
            else:
                # Raise error only if no quote was found after trying all relevant methods/retries
                raise ValueError(
                    f"No valid pool/pair found or quote failed for tokens {token_in} and {token_out} (version: {version})"
                )

        except Exception as e:
            logger.error(f"Error getting quote: {e}", exc_info=True)
            raise

    async def get_pool_liquidity(self, factory: str, token0: str, token1: str) -> float:
        """
        Get pool liquidity in USD.

        Args:
            factory: Factory contract address
            token0: First token address
            token1: Second token address

        Returns:
            Pool liquidity in USD
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")

        try:
            # For now return a default value since we need complex calculations
            # involving token prices and reserves to get actual liquidity
            # TODO: Implement actual liquidity calculation
            logger.warning("get_pool_liquidity returning default value - needs implementation")
            return 1000000.0

        except Exception as e:
            logger.error(f"Error getting pool liquidity: {e}", exc_info=True)
            raise


async def create_web3_manager(config: Dict[str, Any]) -> Web3Manager:
    """
    Create and initialize a Web3 manager.

    Args:
        config: Web3 configuration

    Returns:
        Initialized Web3 manager
    """
    manager = Web3Manager(config)
    await manager.initialize()
    return manager
