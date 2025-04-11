"""
DEX Validator

This module provides functionality for validating discovered DEXes.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple

from eth_utils import to_checksum_address

# Assuming Web3Manager is correctly imported elsewhere if needed by the caller
from arbitrage_bot.core.web3.web3_manager import Web3Manager # Use absolute import
from .base import DEXInfo, DEXProtocolType

logger = logging.getLogger(__name__)


class DEXValidator:
    """
    Validator for DEX information.

    This class provides methods for validating DEX information, such as
    checking contract addresses and verifying protocol types.
    """

    def __init__(self, web3_manager: Web3Manager, config: Optional[Dict[str, Any]] = None): # Use specific type hint
        """
        Initialize the DEX validator.

        Args:
            web3_manager: Web3 manager for blockchain interactions
            config: Configuration dictionary
        """
        self.web3_manager = web3_manager
        self.config = config or {}
        self._lock = asyncio.Lock()
        self._initialized = False

        # Function signatures for different contract types
        self._function_signatures = {
            "factory_v2": {
                "getPair(address,address)": "0xe6a43905",
                "allPairs(uint256)": "0x1e3dd18b",
                "allPairsLength()": "0x574f2ba3",
                "createPair(address,address)": "0xc9c65396",
            },
            "factory_v3": {
                "getPool(address,address,uint24)": "0x1698ee82",
                "createPool(address,address,uint24)": "0xa1671295",
                "setOwner(address)": "0x13af4035",
            },
            "router_v2": {
                "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)": "0x38ed1739",
                "swapTokensForExactTokens(uint256,uint256,address[],address,uint256)": "0x8803dbee",
                "addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)": "0xe8e33700",
            },
            "router_v3": {
                "exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))": "0x414bf389",
                "exactInput((bytes,address,uint256,uint256,uint256))": "0xc04b8d59",
                "exactOutputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))": "0xdb3e2198",
            },
            "pair_v2": {
                "getReserves()": "0x0902f1ac",
                "swap(uint256,uint256,address,bytes)": "0x022c0d9f",
                "token0()": "0x0dfe1681",
                "token1()": "0xd21220a7",
            },
            "pool_v3": {
                "slot0()": "0x3850c7bd",
                "liquidity()": "0x1a686502",
                "swap(address,bool,int256,uint160,bytes)": "0x128acb08",
                "token0()": "0x0dfe1681",
                "token1()": "0xd21220a7",
            },
        }

    async def initialize(self) -> bool:
        """
        Initialize the DEX validator.

        Returns:
            True if initialization was successful, False otherwise
        """
        async with self._lock:
            if self._initialized:
                return True

            logger.info("Initializing DEX validator")

            # Check if web3_manager is initialized
            if not hasattr(self.web3_manager, "w3"):
                logger.error("Web3 manager not initialized")
                return False

            self._initialized = True
            logger.info("DEX validator initialized")
            return True

    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            self._initialized = False

    async def validate_dex(self, dex_info: DEXInfo) -> Tuple[bool, List[str]]:
        """
        Validate a DEX.

        Args:
            dex_info: DEX information

        Returns:
            Tuple of (is_valid, error_messages)
        """
        if not self._initialized:
            await self.initialize()

        errors = []

        try:
            # Validate factory address
            factory_valid, factory_errors = await self._validate_factory(dex_info)
            if not factory_valid:
                errors.extend(factory_errors)

            # Validate router address
            router_valid, router_errors = await self._validate_router(dex_info)
            if not router_valid:
                errors.extend(router_errors)

            # Validate quoter address if provided
            if dex_info.quoter_address:
                quoter_valid, quoter_errors = await self._validate_quoter(dex_info)
                if not quoter_valid:
                    errors.extend(quoter_errors)

            # Validate protocol type
            protocol_valid, protocol_errors = await self._validate_protocol_type(
                dex_info
            )
            if not protocol_valid:
                errors.extend(protocol_errors)

            # Check if any errors were found
            is_valid = len(errors) == 0

            if is_valid:
                logger.info(f"DEX {dex_info.name} validated successfully")
            else:
                logger.warning(f"DEX {dex_info.name} validation failed: {errors}")

            return is_valid, errors

        except Exception as e:
            logger.error(f"Error validating DEX {dex_info.name}: {e}")
            errors.append(f"Validation error: {str(e)}")
            return False, errors

    async def _validate_factory(self, dex_info: DEXInfo) -> Tuple[bool, List[str]]:
        """
        Validate factory address.

        Args:
            dex_info: DEX information

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            factory_cs = to_checksum_address(dex_info.factory_address)
            # Check if address is valid
            if not self.web3_manager.w3.is_address(factory_cs):
                errors.append(f"Invalid factory address: {factory_cs}")
                return False, errors

            # Check if contract exists
            code = await self.web3_manager.w3.eth.get_code(factory_cs)
            if code == b"" or code == "0x":
                errors.append(
                    f"Factory contract does not exist: {factory_cs}"
                )
                return False, errors

            # Check function signatures based on protocol type
            if dex_info.protocol_type == DEXProtocolType.UNISWAP_V2:
                signatures = self._function_signatures["factory_v2"]
            elif dex_info.protocol_type == DEXProtocolType.UNISWAP_V3:
                signatures = self._function_signatures["factory_v3"]
            else:
                # Skip signature check for other protocol types
                return True, []

            # Check if contract has required functions by checking bytecode
            for func_name, func_sig in signatures.items():
                if not await self._has_function(factory_cs, func_sig): # Pass address
                    errors.append(f"Factory contract missing function: {func_name}")

            return len(errors) == 0, errors

        except Exception as e:
            logger.error(f"Error validating factory address: {e}")
            errors.append(f"Factory validation error: {str(e)}")
            return False, errors

    async def _validate_router(self, dex_info: DEXInfo) -> Tuple[bool, List[str]]:
        """
        Validate router address.

        Args:
            dex_info: DEX information

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            router_cs = to_checksum_address(dex_info.router_address)
            # Check if address is valid
            if not self.web3_manager.w3.is_address(router_cs):
                errors.append(f"Invalid router address: {router_cs}")
                return False, errors

            # Check if contract exists
            code = await self.web3_manager.w3.eth.get_code(router_cs)
            if code == b"" or code == "0x":
                errors.append(
                    f"Router contract does not exist: {router_cs}"
                )
                return False, errors

            # Check function signatures based on protocol type
            if dex_info.protocol_type == DEXProtocolType.UNISWAP_V2:
                signatures = self._function_signatures["router_v2"]
            elif dex_info.protocol_type == DEXProtocolType.UNISWAP_V3:
                signatures = self._function_signatures["router_v3"]
            else:
                # Skip signature check for other protocol types
                return True, []

            # Check if contract has required functions by checking bytecode
            for func_name, func_sig in signatures.items():
                if not await self._has_function(router_cs, func_sig): # Pass address
                    errors.append(f"Router contract missing function: {func_name}")

            return len(errors) == 0, errors

        except Exception as e:
            logger.error(f"Error validating router address: {e}")
            errors.append(f"Router validation error: {str(e)}")
            return False, errors

    async def _validate_quoter(self, dex_info: DEXInfo) -> Tuple[bool, List[str]]:
        """
        Validate quoter address.

        Args:
            dex_info: DEX information

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            quoter_cs = to_checksum_address(dex_info.quoter_address)
            # Check if address is valid
            if not self.web3_manager.w3.is_address(quoter_cs):
                errors.append(f"Invalid quoter address: {quoter_cs}")
                return False, errors

            # Check if contract exists
            code = await self.web3_manager.w3.eth.get_code(quoter_cs)
            if code == b"" or code == "0x":
                errors.append(
                    f"Quoter contract does not exist: {quoter_cs}"
                )
                return False, errors

            # Skip function signature check for quoter
            return True, []

        except Exception as e:
            logger.error(f"Error validating quoter address: {e}")
            errors.append(f"Quoter validation error: {str(e)}")
            return False, errors

    async def _validate_protocol_type(
        self, dex_info: DEXInfo
    ) -> Tuple[bool, List[str]]:
        """
        Validate protocol type.

        Args:
            dex_info: DEX information

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            factory_cs = to_checksum_address(dex_info.factory_address)
            # Check bytecode for function signatures

            # Check for V2-specific functions
            is_v2 = await self._has_function(
                factory_cs, # Pass address
                self._function_signatures["factory_v2"]["getPair(address,address)"],
            )

            # Check for V3-specific functions
            is_v3 = await self._has_function(
                factory_cs, # Pass address
                self._function_signatures["factory_v3"][
                    "getPool(address,address,uint24)"
                ],
            )

            # Validate protocol type
            if dex_info.protocol_type == DEXProtocolType.UNISWAP_V2 and not is_v2:
                errors.append(
                    f"DEX {dex_info.name} is marked as Uniswap V2 but factory does not have V2 functions"
                )
            elif dex_info.protocol_type == DEXProtocolType.UNISWAP_V3 and not is_v3:
                errors.append(
                    f"DEX {dex_info.name} is marked as Uniswap V3 but factory does not have V3 functions"
                )

            return len(errors) == 0, errors

        except Exception as e:
            logger.error(f"Error validating protocol type: {e}")
            errors.append(f"Protocol type validation error: {str(e)}")
            return False, errors

    async def _has_function(self, contract_address: str, function_signature_hash: str) -> bool: # Changed to accept address
        """
        Check if a contract has a function with the given signature hash in its bytecode.

        Args:
            contract_address: Address of the contract
            function_signature_hash: 4-byte function signature hash (e.g., '0xe6a43905')

        Returns:
            True if the contract bytecode contains the function signature, False otherwise
        """
        try:
            # Get contract code
            code = await self.web3_manager.w3.eth.get_code(contract_address)
            code_hex = code.hex()

            # Check if function signature hash (without 0x prefix) is in code hex
            return function_signature_hash.lower().replace("0x", "") in code_hex.lower()

        except Exception as e:
            logger.error(f"Error checking function signature for {contract_address}: {e}")
            return False


async def create_dex_validator(
    web3_manager: Web3Manager, config: Optional[Dict[str, Any]] = None # Use specific type hint
) -> DEXValidator:
    """
    Create and initialize a DEX validator.

    Args:
        web3_manager: Web3 manager for blockchain interactions
        config: Configuration dictionary

    Returns:
        Initialized DEX validator
    """
    validator = DEXValidator(web3_manager, config)
    await validator.initialize()
    return validator
