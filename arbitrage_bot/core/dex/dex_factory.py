"""Factory for creating DEX instances."""

import logging
from typing import Dict, Any, Optional, Type
from enum import Enum

from .base_dex import BaseDEX
from .base_dex_v2 import BaseDEXV2
from .base_dex_v3 import BaseDEXV3
from .pancakeswap import PancakeSwapDEX
from .baseswap import BaseSwapDEX
from .swapbased import SwapBasedDEX
from .uniswap_v3 import UniswapV3DEX
from .rocketswap import RocketSwapDEX
from .aerodrome import AerodromeDEX
from .sushiswap import SushiswapDEX
from ..web3.web3_manager import Web3Manager

logger = logging.getLogger(__name__)


class DEXProtocol(Enum):
    """Supported DEX protocols."""

    V2 = "v2"
    V3 = "v3"


class DEXType(Enum):
    """Supported DEX types."""

    PANCAKESWAP = "pancakeswap"
    BASESWAP = "baseswap"
    SWAPBASED = "swapbased"
    UNISWAP_V3 = "uniswap_v3"
    ROCKETSWAP = "rocketswap"
    AERODROME = "aerodrome"
    SUSHISWAP = "sushiswap"


class DEXFactory:
    """Factory for creating and managing DEX instances."""

    # Protocol mapping
    PROTOCOL_MAP = {
        DEXType.PANCAKESWAP: DEXProtocol.V3,
        DEXType.BASESWAP: DEXProtocol.V2,
        DEXType.SWAPBASED: DEXProtocol.V2,
        DEXType.UNISWAP_V3: DEXProtocol.V3,
        DEXType.ROCKETSWAP: DEXProtocol.V2,
        DEXType.AERODROME: DEXProtocol.V2,
        DEXType.SUSHISWAP: DEXProtocol.V2,
    }

    # Implementation mapping
    IMPLEMENTATION_MAP = {
        DEXType.PANCAKESWAP: PancakeSwapDEX,
        DEXType.BASESWAP: BaseSwapDEX,
        DEXType.SWAPBASED: SwapBasedDEX,
        DEXType.UNISWAP_V3: UniswapV3DEX,
        DEXType.ROCKETSWAP: RocketSwapDEX,
        DEXType.AERODROME: AerodromeDEX,
        DEXType.SUSHISWAP: SushiswapDEX,
    }

    # Required config keys for each protocol
    V2_REQUIRED_CONFIG = {"router": str, "factory": str, "fee": int}

    V3_REQUIRED_CONFIG = {"router": str, "factory": str, "quoter": str, "fee": int}

    @classmethod
    def create_dex(
        cls, dex_type: DEXType, web3_manager: Web3Manager, config: Dict[str, Any]
    ) -> BaseDEX:
        """
        Create a DEX instance.

        Args:
            dex_type: Type of DEX to create
            web3_manager: Web3Manager instance
            config: DEX configuration

        Returns:
            BaseDEX: Configured DEX instance

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate DEX type
        if dex_type not in cls.IMPLEMENTATION_MAP:
            raise ValueError(f"Unsupported DEX type: {dex_type}")

        # Get protocol and implementation
        protocol = cls.PROTOCOL_MAP[dex_type]
        implementation = cls.IMPLEMENTATION_MAP[dex_type]

        # Validate config
        cls._validate_config(config, protocol)

        # Create instance
        return implementation(web3_manager, config)

    @classmethod
    def create_all(
        cls, web3_manager: Web3Manager, configs: Dict[str, Dict[str, Any]]
    ) -> Dict[str, BaseDEX]:
        """
        Create multiple DEX instances.

        Args:
            web3_manager: Web3Manager instance
            configs: Dictionary mapping DEX names to configs

        Returns:
            Dict[str, BaseDEX]: Dictionary mapping DEX names to instances

        Raises:
            ValueError: If any configuration is invalid
        """
        dexes = {}
        for dex_name, config in configs.items():
            try:
                dex_type = DEXType(dex_name.lower())
                if not config.get("enabled", True):
                    logger.info(f"Skipping disabled DEX {dex_name}")
                    continue

                if dex_type in cls.IMPLEMENTATION_MAP:
                    dexes[dex_name] = cls.create_dex(dex_type, web3_manager, config)
                else:
                    logger.warning(f"Skipping unsupported DEX type: {dex_name}")
            except ValueError as e:
                logger.warning(f"Skipping DEX {dex_name}: {str(e)}")
                continue
        return dexes

    @classmethod
    def _validate_config(cls, config: Dict[str, Any], protocol: DEXProtocol) -> None:
        """
        Validate DEX configuration.

        Args:
            config: Configuration to validate
            protocol: DEX protocol

        Raises:
            ValueError: If configuration is invalid
        """
        required_config = (
            cls.V3_REQUIRED_CONFIG
            if protocol == DEXProtocol.V3
            else cls.V2_REQUIRED_CONFIG
        )

        # Check required keys
        for key, expected_type in required_config.items():
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")
            if not isinstance(config[key], expected_type):
                raise ValueError(
                    f"Invalid type for {key}. Expected {expected_type.__name__}, "
                    f"got {type(config[key]).__name__}"
                )

        # Validate addresses
        for key in ["router", "factory"]:
            if not cls._is_valid_address(config[key]):
                raise ValueError(f"Invalid address for {key}: {config[key]}")

        if protocol == DEXProtocol.V3:
            if not cls._is_valid_address(config["quoter"]):
                raise ValueError(f"Invalid quoter address: {config['quoter']}")

        # Validate fee
        if not 0 <= config["fee"] <= 10000:
            raise ValueError(
                f"Invalid fee: {config['fee']}. Must be between 0 and 10000"
            )

    @staticmethod
    def _is_valid_address(address: str) -> bool:
        """Check if address is valid."""
        if not isinstance(address, str):
            return False
        if not address.startswith("0x"):
            return False
        try:
            int(address, 16)
            return len(address) == 42
        except ValueError:
            return False

    @classmethod
    def get_protocol(cls, dex_type: DEXType) -> DEXProtocol:
        """Get protocol for DEX type."""
        return cls.PROTOCOL_MAP[dex_type]

    @classmethod
    def get_implementation(cls, dex_type: DEXType) -> Type[BaseDEX]:
        """Get implementation class for DEX type."""
        return cls.IMPLEMENTATION_MAP[dex_type]

    @classmethod
    def get_required_config(cls, protocol: DEXProtocol) -> Dict[str, type]:
        """Get required config for protocol."""
        return (
            cls.V3_REQUIRED_CONFIG
            if protocol == DEXProtocol.V3
            else cls.V2_REQUIRED_CONFIG
        )
