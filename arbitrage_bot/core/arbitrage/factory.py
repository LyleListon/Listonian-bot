"""
Arbitrage System Factory

This module provides factory functions for creating components in the arbitrage system.
These functions handle the creation and initialization of components with proper
dependency injection.
"""

import logging
from typing import Dict, Any, Optional, Type, cast

from ..web3.interfaces import Web3Client
from .interfaces import (
    ArbitrageSystem,
    DiscoveryManager, 
    ExecutionManager,
    AnalyticsManager,
    MarketDataProvider,
    OpportunityDetector,
    OpportunityValidator,
    ExecutionStrategy
)
from .base_system import ArbitrageSystemImpl
from .discovery.default_manager import DefaultDiscoveryManager
from .discovery.detectors.cross_dex_detector import CrossDexDetector
from .discovery.detectors.triangular_detector import TriangularDetector
from .discovery.validators.basic_validator import BasicValidator
from .execution.default_manager import DefaultExecutionManager
from .execution.strategies.standard_strategy import StandardExecutionStrategy
from .execution.strategies.flashbots_strategy import FlashbotsExecutionStrategy
from .execution.strategies.flash_loan_strategy import FlashLoanExecutionStrategy
from .execution.transaction_monitor import TransactionMonitor

logger = logging.getLogger(__name__)


async def create_arbitrage_system(
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> ArbitrageSystem:
    """
    Create and initialize an arbitrage system instance.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration for the arbitrage system
        
    Returns:
        Initialized arbitrage system
    """
    config = config or {}
    logger.info("Creating arbitrage system")
    
    # Create components
    discovery_manager = await create_discovery_manager(web3_client, config.get("discovery"))
    execution_manager = await create_execution_manager(web3_client, config.get("execution"))
    analytics_manager = await create_analytics_manager(web3_client, config.get("analytics"))
    market_data_provider = await create_market_data_provider(web3_client, config.get("market_data"))
    
    # Create system
    system = ArbitrageSystemImpl(
        discovery_manager=discovery_manager,
        execution_manager=execution_manager,
        analytics_manager=analytics_manager,
        market_data_provider=market_data_provider,
        config=config
    )
    
    # Initialize system
    await system.initialize()
    
    return system


async def create_discovery_manager(
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> DiscoveryManager:
    """
    Create and initialize a discovery manager.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration for the discovery manager
        
    Returns:
        Initialized discovery manager
    """
    config = config or {}
    logger.info("Creating discovery manager")
    
    # Create detectors
    detectors = []
    if config.get("enable_cross_dex_detection", True):
        cross_dex_detector = await create_cross_dex_detector(
            web3_client, 
            config.get("cross_dex_detector")
        )
        detectors.append(cross_dex_detector)
    
    if config.get("enable_triangular_detection", True):
        triangular_detector = await create_triangular_detector(
            web3_client, 
            config.get("triangular_detector")
        )
        detectors.append(triangular_detector)
    
    # Create validators
    validators = []
    basic_validator = await create_basic_validator(
        web3_client, 
        config.get("basic_validator")
    )
    validators.append(basic_validator)
    
    # Create manager
    manager = DefaultDiscoveryManager(
        detectors=detectors,
        validators=validators,
        config=config
    )
    
    # Initialize manager
    await manager.initialize()
    
    return manager


async def create_execution_manager(
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> ExecutionManager:
    """
    Create and initialize an execution manager.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration for the execution manager
        
    Returns:
        Initialized execution manager
    """
    config = config or {}
    logger.info("Creating execution manager")
    
    # Create strategies
    strategies = {}
    
    # Standard strategy
    if config.get("enable_standard_strategy", True):
        standard_strategy = await create_standard_strategy(
            web3_client, 
            config.get("standard_strategy")
        )
        strategies["standard"] = standard_strategy
    
    # Flashbots strategy
    if config.get("enable_flashbots_strategy", True):
        flashbots_strategy = await create_flashbots_strategy(
            web3_client, 
            config.get("flashbots_strategy")
        )
        strategies["flashbots"] = flashbots_strategy
    
    # Flash loan strategy
    if config.get("enable_flash_loan_strategy", True):
        flash_loan_strategy = await create_flash_loan_strategy(
            web3_client, 
            config.get("flash_loan_strategy")
        )
        strategies["flash_loan"] = flash_loan_strategy
    
    # Create transaction monitor
    transaction_monitor = TransactionMonitor(
        web3_client=web3_client,
        config=config.get("transaction_monitor")
    )
    
    # Create manager
    manager = DefaultExecutionManager(
        strategies=strategies,
        transaction_monitor=transaction_monitor,
        web3_client=web3_client,
        config=config
    )
    
    # Initialize manager
    await manager.initialize()
    
    return manager


async def create_analytics_manager(
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> Optional[AnalyticsManager]:
    """
    Create and initialize an analytics manager.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration for the analytics manager
        
    Returns:
        Initialized analytics manager or None if disabled
    """
    config = config or {}
    
    # Analytics manager is not yet implemented
    logger.info("Analytics manager not yet implemented")
    return None


async def create_market_data_provider(
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> Optional[MarketDataProvider]:
    """
    Create and initialize a market data provider.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration for the market data provider
        
    Returns:
        Initialized market data provider or None if disabled
    """
    config = config or {}
    
    # Market data provider is not yet implemented
    logger.info("Market data provider not yet implemented")
    return None


async def create_cross_dex_detector(
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> OpportunityDetector:
    """
    Create and initialize a cross-DEX opportunity detector.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration for the detector
        
    Returns:
        Initialized cross-DEX detector
    """
    config = config or {}
    logger.info("Creating cross-DEX detector")
    
    detector = CrossDexDetector(
        web3_client=web3_client,
        config=config
    )
    
    # Initialize detector
    await detector.initialize()
    
    return detector


async def create_triangular_detector(
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> OpportunityDetector:
    """
    Create and initialize a triangular opportunity detector.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration for the detector
        
    Returns:
        Initialized triangular detector
    """
    config = config or {}
    logger.info("Creating triangular detector")
    
    detector = TriangularDetector(
        web3_client=web3_client,
        config=config
    )
    
    # Initialize detector
    await detector.initialize()
    
    return detector


async def create_basic_validator(
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> OpportunityValidator:
    """
    Create and initialize a basic opportunity validator.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration for the validator
        
    Returns:
        Initialized validator
    """
    config = config or {}
    logger.info("Creating basic validator")
    
    validator = BasicValidator(
        web3_client=web3_client,
        config=config
    )
    
    # Initialize validator
    await validator.initialize()
    
    return validator


async def create_standard_strategy(
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> ExecutionStrategy:
    """
    Create and initialize a standard execution strategy.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration for the strategy
        
    Returns:
        Initialized strategy
    """
    config = config or {}
    logger.info("Creating standard execution strategy")
    
    strategy = StandardExecutionStrategy(
        web3_client=web3_client,
        config=config
    )
    
    # Initialize strategy
    await strategy.initialize()
    
    return strategy


async def create_flashbots_strategy(
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> ExecutionStrategy:
    """
    Create and initialize a Flashbots execution strategy.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration for the strategy
        
    Returns:
        Initialized strategy
    """
    config = config or {}
    logger.info("Creating Flashbots execution strategy")
    
    from ..web3.flashbots.flashbots_provider import FlashbotsProvider
    
    # Create Flashbots provider
    flashbots_rpc = config.get("flashbots_rpc")
    flashbots_signing_key = config.get("flashbots_signing_key")
    
    provider = FlashbotsProvider(
        web3_client=web3_client,
        flashbots_rpc=flashbots_rpc,
        flashbots_signing_key=flashbots_signing_key,
        config=config
    )
    
    # Create strategy with Flashbots provider
    strategy = FlashbotsExecutionStrategy(
        web3_client=web3_client,
        flashbots_provider=provider,
        config=config
    )
    
    # Initialize strategy
    await strategy.initialize()
    
    return strategy


async def create_flash_loan_strategy(
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> ExecutionStrategy:
    """
    Create and initialize a Flash Loan execution strategy.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration for the strategy
        
    Returns:
        Initialized strategy
    """
    config = config or {}
    logger.info("Creating Flash Loan execution strategy")
    
    # Import here to avoid circular imports
    from .execution.strategies.flash_loan_strategy import FlashLoanExecutionStrategy
    
    # Create strategy
    strategy = FlashLoanExecutionStrategy(
        web3_client=web3_client,
        config=config
    )
    
    # Initialize strategy
    await strategy.initialize()
    
    return strategy