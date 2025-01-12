"""DEX manager for handling multiple DEX instances."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta

from .dex_factory import DEXFactory, DEXType, DEXProtocol
from .base_dex import BaseDEX
from ..web3.web3_manager import Web3Manager

logger = logging.getLogger(__name__)

@dataclass
class DEXStatus:
    """Status information for a DEX."""
    name: str
    protocol: DEXProtocol
    initialized: bool
    last_success: Optional[datetime]
    error_count: int
    last_error: Optional[str]
    disabled: bool

class DEXManager:
    """Manager for handling multiple DEX instances."""

    @property
    def web3(self):
        """Get Web3 instance."""
        return self.web3_manager.w3

    def __init__(
        self,
        web3_manager: Web3Manager,
        configs: Dict[str, Dict[str, Any]],
        max_errors: int = 3,
        recovery_delay: int = 300
    ):
        """
        Initialize DEX manager.
        
        Args:
            web3_manager: Web3Manager instance
            configs: Dictionary mapping DEX names to configs
            max_errors: Maximum errors before disabling DEX (default: 3)
            recovery_delay: Seconds to wait before recovery attempt (default: 300)
        """
        self.web3_manager = web3_manager
        self.configs = configs
        self.max_errors = max_errors
        self.recovery_delay = recovery_delay
        
        # Initialize containers
        self.dexes: Dict[str, BaseDEX] = {}
        self.status: Dict[str, DEXStatus] = {}
        self.initialized = False
        
        # Track active operations
        self._active_recoveries: Set[str] = set()

    async def initialize(self) -> bool:
        """
        Initialize all configured DEXs.
        
        Returns:
            bool: True if at least one DEX initialized successfully
        """
        try:
            # Create DEX instances
            for dex_name, config in self.configs.items():
                try:
                    # Create DEX instance
                    dex_type = DEXType(dex_name.lower())
                    protocol = DEXFactory.get_protocol(dex_type)
                    
                    # Initialize status tracking
                    self.status[dex_name] = DEXStatus(
                        name=dex_name,
                        protocol=protocol,
                        initialized=False,
                        last_success=None,
                        error_count=0,
                        last_error=None,
                        disabled=False
                    )
                    
                    # Create and initialize DEX
                    dex = DEXFactory.create_dex(dex_type, self.web3_manager, config)
                    success = await dex.initialize()
                    
                    if success:
                        self.dexes[dex_name] = dex
                        self.status[dex_name].initialized = True
                        self.status[dex_name].last_success = datetime.now()
                        logger.info(f"Initialized {dex_name} successfully")
                    else:
                        self._handle_error(dex_name, "Initialization failed")
                        
                except Exception as e:
                    self._handle_error(dex_name, str(e))
                    
            # Check if any DEXs initialized
            self.initialized = len(self.dexes) > 0
            if not self.initialized:
                logger.error("No DEXs initialized successfully")
            
            return self.initialized
            
        except Exception as e:
            logger.error(f"Failed to initialize DEX manager: {e}")
            return False

    def get_dex_by_address(self, address: str) -> Optional[BaseDEX]:
        """Get DEX instance by router address."""
        if not address:
            return None
            
        address = address.lower()
        for dex in self.dexes.values():
            # Check router address attribute
            if hasattr(dex, 'router_address'):
                if isinstance(dex.router_address, str) and dex.router_address.lower() == address:
                    return dex
            
            # Check router contract attribute
            if hasattr(dex, 'router'):
                if hasattr(dex.router, 'address'):
                    if isinstance(dex.router.address, str) and dex.router.address.lower() == address:
                        return dex
                    
            # Check factory address
            if hasattr(dex, 'factory_address'):
                if isinstance(dex.factory_address, str) and dex.factory_address.lower() == address:
                    return dex
                    
            # Check factory contract
            if hasattr(dex, 'factory'):
                if hasattr(dex.factory, 'address'):
                    if isinstance(dex.factory.address, str) and dex.factory.address.lower() == address:
                        return dex
        
        return None

    def get_dex(self, name: str) -> Optional[BaseDEX]:
        """
        Get DEX instance by name.
        
        Args:
            name: DEX name
            
        Returns:
            Optional[BaseDEX]: DEX instance if available and not disabled
        """
        if name not in self.dexes:
            return None
            
        status = self.status[name]
        if status.disabled:
            return None
            
        return self.dexes[name]

    def get_all_dexes(self) -> List[BaseDEX]:
        """Get all available DEX instances."""
        return [
            dex for name, dex in self.dexes.items()
            if not self.status[name].disabled
        ]

    def get_status(self, name: str) -> Optional[DEXStatus]:
        """Get status for a DEX."""
        return self.status.get(name)

    def get_all_status(self) -> Dict[str, DEXStatus]:
        """Get status for all DEXs."""
        return self.status.copy()

    async def recover_dex(self, name: str) -> bool:
        """
        Attempt to recover a failed DEX.
        
        Args:
            name: DEX name
            
        Returns:
            bool: True if recovery successful
        """
        if name not in self.configs:
            return False
            
        if name in self._active_recoveries:
            logger.info(f"Recovery already in progress for {name}")
            return False
            
        try:
            self._active_recoveries.add(name)
            
            status = self.status[name]
            if not status.disabled:
                return True
                
            # Check recovery delay
            if status.last_error:
                elapsed = datetime.now() - status.last_error
                if elapsed.total_seconds() < self.recovery_delay:
                    return False
            
            # Attempt recovery
            dex_type = DEXType(name.lower())
            dex = DEXFactory.create_dex(
                dex_type,
                self.web3_manager,
                self.configs[name]
            )
            
            success = await dex.initialize()
            if success:
                self.dexes[name] = dex
                status.initialized = True
                status.disabled = False
                status.error_count = 0
                status.last_success = datetime.now()
                status.last_error = None
                logger.info(f"Successfully recovered {name}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to recover {name}: {e}")
            return False
            
        finally:
            self._active_recoveries.remove(name)

    async def recover_all(self) -> Dict[str, bool]:
        """
        Attempt to recover all failed DEXs.
        
        Returns:
            Dict[str, bool]: Mapping of DEX names to recovery success
        """
        results = {}
        for name in self.configs:
            if self.status[name].disabled:
                results[name] = await self.recover_dex(name)
        return results

    def _handle_error(self, name: str, error: str) -> None:
        """Handle DEX error."""
        status = self.status[name]
        status.error_count += 1
        status.last_error = datetime.now()
        
        if status.error_count >= self.max_errors:
            status.disabled = True
            logger.warning(
                f"Disabled {name} after {status.error_count} errors. "
                f"Last error: {error}"
            )
        else:
            logger.error(
                f"Error in {name} ({status.error_count}/{self.max_errors}): {error}"
            )

    async def monitor_health(
        self,
        interval: int = 60,
        auto_recover: bool = True
    ) -> None:
        """
        Monitor DEX health and attempt recovery.
        
        Args:
            interval: Check interval in seconds
            auto_recover: Whether to automatically attempt recovery
        """
        while True:
            try:
                for name, dex in self.dexes.items():
                    status = self.status[name]
                    if status.disabled:
                        continue
                        
                    try:
                        # Basic health check
                        factory = await dex.router.functions.factory().call()
                        if not factory:
                            raise ValueError("Invalid factory")
                            
                        status.last_success = datetime.now()
                        
                    except Exception as e:
                        self._handle_error(name, str(e))
                        
                if auto_recover:
                    await self.recover_all()
                    
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                
            await asyncio.sleep(interval)


async def create_dex_manager(
    web3_manager: Optional[Web3Manager] = None,
    configs: Optional[Dict[str, Dict[str, Any]]] = None,
    max_errors: int = 3,
    recovery_delay: int = 300
) -> DEXManager:
    """
    Create DEX manager instance.

    Args:
        web3_manager: Optional Web3Manager instance
        configs: Optional DEX configurations
        max_errors: Maximum errors before disabling DEX
        recovery_delay: Seconds to wait before recovery attempt

    Returns:
        DEXManager: DEX manager instance
    """
    if not web3_manager:
        from ..web3.web3_manager import create_web3_manager
        web3_manager = await create_web3_manager()

    if not configs:
        # Load default configs
        from ...utils.config_loader import load_config
        configs = load_config().get('dexes', {})

    manager = DEXManager(
        web3_manager=web3_manager,
        configs=configs,
        max_errors=max_errors,
        recovery_delay=recovery_delay
    )

    await manager.initialize()
    return manager
