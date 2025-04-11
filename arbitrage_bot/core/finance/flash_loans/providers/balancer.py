"""
Balancer Flash Loan Provider

This module contains the implementation of the Balancer flash loan provider,
which uses Balancer's Vault to facilitate flash loans with zero fees.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional # Removed Tuple, cast
import json

from web3 import Web3
# from web3.types import ChecksumAddress, HexBytes, TxParams, Wei # All unused

from .....core.web3.interfaces import Web3Client, Transaction # Removed TransactionReceipt
from ..interfaces import ( # Removed FlashLoanProvider, TokenAmount
    FlashLoanCallback,
    FlashLoanParams,
    FlashLoanResult,
    FlashLoanStatus,
)

logger = logging.getLogger(__name__)

# ABI snippets for Balancer contracts
BALANCER_VAULT_ABI_SNIPPET = """
[
    {
        "inputs": [
            {
                "internalType": "address[]",
                "name": "tokens",
                "type": "address[]"
            },
            {
                "internalType": "uint256[]",
                "name": "amounts",
                "type": "uint256[]"
            },
            {
                "internalType": "bytes",
                "name": "userData",
                "type": "bytes"
            }
        ],
        "name": "flashLoan",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "FLASH_LOAN_FEE_PERCENTAGE",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "bytes32",
                "name": "poolId",
                "type": "bytes32"
            },
            {
                "internalType": "contract IERC20",
                "name": "token",
                "type": "address"
            }
        ],
        "name": "getPoolTokenInfo",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "cash",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "managed",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "lastChangeBlock",
                "type": "uint256"
            },
            {
                "internalType": "address",
                "name": "assetManager",
                "type": "address"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]
"""

FLASH_LOAN_CALLBACK_ABI_SNIPPET = """
[
    {
        "inputs": [
            {
                "internalType": "address[]",
                "name": "tokens",
                "type": "address[]"
            },
            {
                "internalType": "uint256[]",
                "name": "amounts",
                "type": "uint256[]"
            },
            {
                "internalType": "uint256[]",
                "name": "feeAmounts",
                "type": "uint256[]"
            },
            {
                "internalType": "bytes",
                "name": "userData",
                "type": "bytes"
            }
        ],
        "name": "receiveFlashLoan",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]
"""

# Default contract addresses
DEFAULT_CONTRACTS = {
    # Balancer V2 Vault on Ethereum mainnet
    "mainnet": {"vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8"},
    # Balancer V2 Vault on Polygon
    "polygon": {"vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8"},
    # Balancer V2 Vault on Arbitrum
    "arbitrum": {"vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8"},
    # Balancer V2 Vault on Optimism
    "optimism": {"vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8"},
    # Balancer V2 Vault on Base
    "base": {"vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8"},
}

# Common pool IDs for reference
COMMON_POOL_IDS = {
    "mainnet": {
        "WETH-USDC": "0x96646936b91d6b9d7d0c47c496afbf3d6ec7b6f8000200000000000000000019",
        "WETH-DAI": "0x0b09dea16768f0799065c475be02919503cb2a3500020000000000000000001a",
        "WETH-WBTC": "0xa6f548df93de924d73be7d25dc02554c6bd66db500020000000000000000000e",
    }
}

# Token addresses to cache common tokens
COMMON_TOKENS = {
    "mainnet": {
        "ETH": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    }
}

# Flash loan fee multiplier (used for calculations)
# Most Balancer pools have 0% flash loan fees, but this can change
# We add a safety buffer of 0.01% (0.0001) to account for any changes
FEE_BUFFER = Decimal("0.0001")
DEFAULT_FEE_PERCENTAGE = Decimal("0")
DEFAULT_FEE_SCALE = Decimal("1e18")


class BalancerFlashLoanProvider:
    """
    Balancer flash loan provider implementation.

    This provider leverages Balancer's Vault to facilitate flash loans with
    typically zero fees, making it an optimal choice for capital efficiency.
    """

    def __init__(self, web3_client: Web3Client, config: Dict[str, Any] = None):
        """
        Initialize the Balancer flash loan provider.

        Args:
            web3_client: Web3 client for blockchain interactions
            config: Configuration parameters for the provider
        """
        self.web3_client = web3_client
        self.config = config or {}

        # Configuration
        self.network = self.config.get("network", "mainnet")
        self.vault_address = self.config.get(
            "vault_address", DEFAULT_CONTRACTS.get(self.network, {}).get("vault")
        )

        if not self.vault_address:
            raise ValueError(
                f"No Balancer Vault address found for network: {self.network}"
            )

        # Ensure address is checksummed
        self.vault_address = Web3.to_checksum_address(self.vault_address)

        # Contract objects (initialized later)
        self.vault_contract = None

        # Cache of supported tokens (initialized later)
        self._supported_tokens: List[str] = []
        self._pool_liquidity: Dict[str, Dict[str, Decimal]] = {}

        # Fee information (initialized later)
        self._fee_percentage: Optional[Decimal] = None

        # State
        self._initialization_lock = asyncio.Lock()
        self._is_initialized = False
        self._flash_loan_lock = asyncio.Lock()
        self._active_callbacks: Dict[str, FlashLoanCallback] = {}

        logger.info(
            f"Created BalancerFlashLoanProvider for network {self.network} "
            f"with vault address {self.vault_address}"
        )

    @property
    def name(self) -> str:
        """Get the name of the flash loan provider."""
        return f"Balancer-{self.network}"

    @property
    def supported_tokens(self) -> List[str]:
        """Get a list of supported token addresses."""
        return self._supported_tokens

    async def initialize(self) -> None:
        """
        Initialize the flash loan provider.

        This method initializes the contract objects, loads supported tokens,
        and gets the current fee percentage.
        """
        async with self._initialization_lock:
            if self._is_initialized:
                logger.debug("Balancer flash loan provider already initialized")
                return

            logger.info(f"Initializing Balancer flash loan provider for {self.network}")

            try:
                # Create contract objects
                vault_abi = json.loads(BALANCER_VAULT_ABI_SNIPPET)
                self.vault_contract = self.web3_client.get_contract(
                    address=self.vault_address, abi=vault_abi
                )

                # Get fee percentage
                fee_percentage = await self._get_fee_percentage()
                self._fee_percentage = fee_percentage
                logger.info(f"Balancer flash loan fee percentage: {fee_percentage}")

                # Load supported tokens
                self._supported_tokens = await self._load_supported_tokens()

                self._is_initialized = True
                logger.info(f"Balancer flash loan provider initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize Balancer flash loan provider: {e}")
                self._is_initialized = False
                raise

    async def _ensure_initialized(self) -> None:
        """Ensure the provider is initialized."""
        if not self._is_initialized:
            await self.initialize()

    async def _get_fee_percentage(self) -> Decimal:
        """
        Get the fee percentage for flash loans.

        Returns:
            Fee percentage as a decimal
        """
        try:
            fee_percentage_raw = await self.web3_client.call_contract_function(
                contract=self.vault_contract,
                function_name="FLASH_LOAN_FEE_PERCENTAGE",
                args=[],
            )

            # Convert from Balancer's representation (1e18 scale) to decimal
            fee_percentage = Decimal(fee_percentage_raw) / DEFAULT_FEE_SCALE

            # Add safety buffer
            fee_percentage += FEE_BUFFER

            return fee_percentage

        except Exception as e:
            logger.warning(f"Failed to get fee percentage, using default: {e}")
            return DEFAULT_FEE_PERCENTAGE + FEE_BUFFER

    async def _load_supported_tokens(self) -> List[str]:
        """
        Load supported tokens for flash loans.

        Returns:
            List of supported token addresses
        """
        # Start with common tokens for the network
        tokens = COMMON_TOKENS.get(self.network, {}).values()
        return [Web3.to_checksum_address(token) for token in tokens]

    async def execute_flash_loan(
        self, params: FlashLoanParams, callback: FlashLoanCallback
    ) -> FlashLoanResult:
        """
        Execute a flash loan.

        Args:
            params: Parameters for the flash loan
            callback: Callback to handle the flash loan

        Returns:
            Result of the flash loan operation
        """
        await self._ensure_initialized()

        async with self._flash_loan_lock:
            start_time = time.time()
            logger.info(
                f"Executing Balancer flash loan for {len(params.token_amounts)} tokens"
            )

            # Initialize result with pending status
            result = FlashLoanResult(
                success=False,
                status=FlashLoanStatus.PENDING,
                tokens_borrowed=params.token_amounts,
            )

            try:
                # Validate parameters
                tokens = [amount.token_address for amount in params.token_amounts]
                amounts = [amount.raw_amount for amount in params.token_amounts]

                # Ensure all token addresses are checksummed
                tokens = [Web3.to_checksum_address(token) for token in tokens]

                # Check liquidity for all tokens
                for token, amount in zip(tokens, params.token_amounts):
                    if not await self.check_liquidity(token, amount.amount):
                        error_msg = f"Insufficient liquidity for token {token}, amount {amount.amount}"
                        logger.error(error_msg)

                        result.status = FlashLoanStatus.FAILED
                        result.error_message = error_msg
                        result.execution_time = time.time() - start_time

                        return result

                # Register callback for later handling
                callback_id = f"{int(time.time() * 1000)}-{hash(callback)}"
                self._active_callbacks[callback_id] = callback

                # Prepare user data (can be customized based on needs)
                user_data = params.callback_data or b""

                # Prepare transaction
                vault_function = self.vault_contract.functions.flashLoan(
                    params.receiver_address,  # Receiver address
                    tokens,  # Token addresses
                    amounts,  # Token amounts
                    user_data,  # User data
                )

                # Set up transaction parameters
                tx_params = params.transaction_params.copy()

                # Add default parameters if not provided
                if "from" not in tx_params:
                    tx_params["from"] = self.web3_client.get_default_account()

                if "gas" not in tx_params:
                    # Estimate gas with a safety buffer
                    estimated_gas = await self.estimate_gas(params)
                    tx_params["gas"] = int(estimated_gas * 1.2)  # 20% buffer

                # Convert transaction parameters to web3's format
                tx = Transaction(
                    from_address=tx_params.get("from"),
                    to_address=self.vault_address,
                    data=vault_function.build_transaction().get("data"),
                    gas=tx_params.get("gas"),
                    gas_price=tx_params.get("gasPrice"),
                    max_fee_per_gas=tx_params.get("maxFeePerGas"),
                    max_priority_fee_per_gas=tx_params.get("maxPriorityFeePerGas"),
                    value=tx_params.get("value", 0),
                    nonce=tx_params.get("nonce"),
                )

                # Send transaction
                tx_hash = await self.web3_client.send_transaction(tx)

                if not tx_hash:
                    logger.error("Failed to send flash loan transaction")
                    result.status = FlashLoanStatus.FAILED
                    result.error_message = "Failed to send transaction"
                    result.execution_time = time.time() - start_time
                    return result

                # Update result with transaction hash
                result.transaction_hash = tx_hash

                # Wait for transaction receipt
                receipt = await self.web3_client.wait_for_transaction_receipt(
                    tx_hash, timeout=300  # 5 minutes timeout
                )

                # Update result with receipt
                result.transaction_receipt = receipt

                # Calculate total fees paid
                fee_percentage = await self.get_flash_loan_fee("", Decimal("0"))
                total_fee = Decimal("0")
                for amount in params.token_amounts:
                    token_fee = amount.amount * fee_percentage
                    total_fee += token_fee

                result.fee_paid = total_fee
                result.gas_used = receipt.gas_used if receipt else None

                # Determine status from receipt
                if receipt and receipt.status == 1:
                    result.status = FlashLoanStatus.EXECUTED
                    result.success = True
                    logger.info(f"Flash loan executed successfully: {tx_hash}")

                    # Call the completion callback
                    try:
                        await callback.on_flash_loan_completed(result)
                    except Exception as callback_error:
                        logger.error(f"Error in completion callback: {callback_error}")

                else:
                    result.status = FlashLoanStatus.REVERTED
                    result.error_message = "Transaction reverted"
                    logger.error(f"Flash loan transaction reverted: {tx_hash}")

                    # Call the failure callback
                    try:
                        await callback.on_flash_loan_failed(result)
                    except Exception as callback_error:
                        logger.error(f"Error in failure callback: {callback_error}")

            except Exception as e:
                logger.error(f"Error executing flash loan: {e}")
                result.status = FlashLoanStatus.FAILED
                result.error_message = str(e)

                # Call the failure callback
                try:
                    await callback.on_flash_loan_failed(result)
                except Exception as callback_error:
                    logger.error(f"Error in failure callback: {callback_error}")

            finally:
                # Remove callback registration
                if "callback_id" in locals():
                    self._active_callbacks.pop(callback_id, None)

                # Update execution time
                result.execution_time = time.time() - start_time

            return result

    async def get_flash_loan_fee(self, token_address: str, amount: Decimal) -> Decimal:
        """
        Get the fee for a flash loan.

        Args:
            token_address: Address of the token to borrow
            amount: Amount to borrow

        Returns:
            Fee for the flash loan as a decimal percentage
        """
        await self._ensure_initialized()

        if self._fee_percentage is not None:
            return self._fee_percentage

        # If we couldn't get the fee from the contract, use the default
        return DEFAULT_FEE_PERCENTAGE + FEE_BUFFER

    async def check_liquidity(self, token_address: str, amount: Decimal) -> bool:
        """
        Check if there's enough liquidity for a flash loan.

        Args:
            token_address: Address of the token to borrow
            amount: Amount to borrow

        Returns:
            True if there's enough liquidity, False otherwise
        """
        await self._ensure_initialized()

        # Checksummed address
        token_address = Web3.to_checksum_address(token_address)

        # Convert amount to raw amount
        decimals = 18  # Default to 18 decimals
        raw_amount = int(amount * (10**decimals))

        try:
            # For a proper implementation, you would need to query the Balancer
            # pools that contain this token and check their liquidity.
            # For simplicity, we'll use a placeholder implementation.

            # In a real implementation, this would query pool data by token
            max_amount = await self.max_flash_loan(token_address)

            return amount <= max_amount

        except Exception as e:
            logger.error(f"Error checking liquidity for {token_address}: {e}")
            return False

    async def max_flash_loan(self, token_address: str) -> Decimal:
        """
        Get the maximum amount that can be borrowed in a flash loan.

        Args:
            token_address: Address of the token to borrow

        Returns:
            Maximum amount that can be borrowed
        """
        await self._ensure_initialized()

        # Checksummed address
        token_address = Web3.to_checksum_address(token_address)

        try:
            # In a real implementation, you would query the Balancer pools
            # to determine the available liquidity.
            # For now, we'll use placeholder values.

            # Get network
            network = self.network.lower()

            # Default large values (would be queried from pools in reality)
            default_max_amounts = {
                "mainnet": {
                    COMMON_TOKENS["mainnet"]["WETH"]: Decimal("1000"),  # 1,000 WETH
                    COMMON_TOKENS["mainnet"]["DAI"]: Decimal("5000000"),  # 5M DAI
                    COMMON_TOKENS["mainnet"]["USDC"]: Decimal("5000000"),  # 5M USDC
                    COMMON_TOKENS["mainnet"]["USDT"]: Decimal("5000000"),  # 5M USDT
                    COMMON_TOKENS["mainnet"]["WBTC"]: Decimal("100"),  # 100 WBTC
                }
            }

            # Get default for network and token
            network_amounts = default_max_amounts.get(network, {})
            max_amount = network_amounts.get(token_address, Decimal("0"))

            # In a real implementation, you would adjust this based on
            # actual pool balances.

            return max_amount

        except Exception as e:
            logger.error(f"Error getting max flash loan for {token_address}: {e}")
            return Decimal("0")

    async def estimate_gas(self, params: FlashLoanParams) -> int:
        """
        Estimate the gas required for a flash loan.

        Args:
            params: Parameters for the flash loan

        Returns:
            Estimated gas required
        """
        await self._ensure_initialized()

        try:
            # Validate parameters
            tokens = [
                Web3.to_checksum_address(amount.token_address)
                for amount in params.token_amounts
            ]
            amounts = [amount.raw_amount for amount in params.token_amounts]
            user_data = params.callback_data or b""

            # Create transaction for estimation
            vault_function = self.vault_contract.functions.flashLoan(
                params.receiver_address,  # Receiver address
                tokens,  # Token addresses
                amounts,  # Token amounts
                user_data,  # User data
            )

            # Estimate gas
            estimated_gas = await self.web3_client.estimate_gas(
                Transaction(
                    from_address=params.transaction_params.get(
                        "from", self.web3_client.get_default_account()
                    ),
                    to_address=self.vault_address,
                    data=vault_function.build_transaction().get("data"),
                    value=params.transaction_params.get("value", 0),
                )
            )

            # Add safety buffer (20%) for gas estimation
            estimated_gas = int(estimated_gas * 1.2)

            return estimated_gas

        except Exception as e:
            logger.error(f"Error estimating gas: {e}")

            # Return a high gas estimate as fallback
            return 900000

    async def close(self) -> None:
        """Close the flash loan provider and clean up resources."""
        logger.info("Closing Balancer flash loan provider")

        # Clean up resources
        self._supported_tokens = []
        self._pool_liquidity = {}
        self._fee_percentage = None
        self._is_initialized = False
