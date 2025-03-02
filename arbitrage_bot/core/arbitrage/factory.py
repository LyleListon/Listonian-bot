"""
Arbitrage System Factory Module

This module provides factory functions for creating and configuring arbitrage system
components based on configuration settings.
"""

import importlib
import logging
from typing import Any, Dict, List, Optional, Type, cast

from .base_system import BaseArbitrageSystem
from .interfaces import (
    ArbitrageAnalytics,
    ArbitrageSystem,
    ExecutionManager,
    ExecutionStrategy,
    MarketDataProvider,
    OpportunityDetector,
    OpportunityDiscoveryManager,
    OpportunityValidator,
    TransactionMonitor,
)


logger = logging.getLogger(__name__)


async def create_arbitrage_system(
    config: Dict[str, Any],
    discovery_manager: Optional[OpportunityDiscoveryManager] = None,
    execution_manager: Optional[ExecutionManager] = None,
    analytics_manager: Optional[ArbitrageAnalytics] = None,
    market_data_provider: Optional[MarketDataProvider] = None,
) -> ArbitrageSystem:
    """
    Create and configure a complete arbitrage system.
    
    This function creates and configures all components of the arbitrage system
    based on the provided configuration. Components can be provided directly
    to override the default creation logic.
    
    Args:
        config: System configuration dictionary
        discovery_manager: Optional pre-configured discovery manager
        execution_manager: Optional pre-configured execution manager
        analytics_manager: Optional pre-configured analytics manager
        market_data_provider: Optional pre-configured market data provider
        
    Returns:
        Configured arbitrage system
    """
    # Create components if not provided
    if discovery_manager is None:
        discovery_manager = await create_discovery_manager(config)
    
    if execution_manager is None:
        execution_manager = await create_execution_manager(config)
    
    if analytics_manager is None:
        analytics_manager = await create_analytics_manager(config)
    
    if market_data_provider is None:
        market_data_provider = await create_market_data_provider(config)
    
    # Create system implementation
    system_impl = config.get("system_implementation", "default")
    
    if system_impl == "default" or system_impl == "base":
        return BaseArbitrageSystem(
            discovery_manager=discovery_manager,
            execution_manager=execution_manager,
            analytics_manager=analytics_manager,
            market_data_provider=market_data_provider,
            config=config,
        )
    else:
        # Load custom implementation
        return await _load_custom_implementation(
            system_impl,
            "ArbitrageSystem",
            discovery_manager=discovery_manager,
            execution_manager=execution_manager,
            analytics_manager=analytics_manager,
            market_data_provider=market_data_provider,
            config=config,
        )


async def create_discovery_manager(
    config: Dict[str, Any],
    detectors: Optional[List[OpportunityDetector]] = None,
    validators: Optional[List[OpportunityValidator]] = None,
) -> OpportunityDiscoveryManager:
    """
    Create and configure an opportunity discovery manager.
    
    This function creates and configures the opportunity discovery manager
    based on the provided configuration. Detectors and validators can be
    provided directly to override the default creation logic.
    
    Args:
        config: System configuration dictionary
        detectors: Optional list of pre-configured detectors
        validators: Optional list of pre-configured validators
        
    Returns:
        Configured opportunity discovery manager
    """
    discovery_config = config.get("discovery_manager", {})
    manager_impl = discovery_config.get("implementation", "default")
    
    # Create detectors if not provided
    if detectors is None:
        detectors = []
        detector_configs = discovery_config.get("detectors", [])
        
        for detector_config in detector_configs:
            detector_type = detector_config.get("type")
            if not detector_type:
                logger.warning(f"Detector config missing 'type': {detector_config}")
                continue
                
            try:
                detector = await create_opportunity_detector(
                    detector_type, detector_config
                )
                detectors.append(detector)
            except Exception as e:
                logger.error(
                    f"Failed to create detector '{detector_type}': {e}", 
                    exc_info=True
                )
    
    # Create validators if not provided
    if validators is None:
        validators = []
        validator_configs = discovery_config.get("validators", [])
        
        for validator_config in validator_configs:
            validator_type = validator_config.get("type")
            if not validator_type:
                logger.warning(f"Validator config missing 'type': {validator_config}")
                continue
                
            try:
                validator = await create_opportunity_validator(
                    validator_type, validator_config
                )
                validators.append(validator)
            except Exception as e:
                logger.error(
                    f"Failed to create validator '{validator_type}': {e}", 
                    exc_info=True
                )
    
    # Create manager implementation
    if manager_impl == "default":
        # Import default implementation
        from .discovery import DefaultDiscoveryManager
        
        manager = DefaultDiscoveryManager(discovery_config)
        
        # Register detectors and validators
        for detector in detectors:
            detector_id = getattr(detector, "detector_id", f"detector_{id(detector)}")
            await manager.register_detector(detector, detector_id)
        
        for validator in validators:
            validator_id = getattr(validator, "validator_id", f"validator_{id(validator)}")
            await manager.register_validator(validator, validator_id)
        
        return manager
    else:
        # Load custom implementation
        manager = await _load_custom_implementation(
            manager_impl, 
            "OpportunityDiscoveryManager",
            config=discovery_config,
        )
        
        # Register detectors and validators
        for detector in detectors:
            detector_id = getattr(detector, "detector_id", f"detector_{id(detector)}")
            await manager.register_detector(detector, detector_id)
        
        for validator in validators:
            validator_id = getattr(validator, "validator_id", f"validator_{id(validator)}")
            await manager.register_validator(validator, validator_id)
        
        return manager


async def create_execution_manager(
    config: Dict[str, Any],
    strategies: Optional[List[ExecutionStrategy]] = None,
    monitors: Optional[List[TransactionMonitor]] = None,
) -> ExecutionManager:
    """
    Create and configure an execution manager.
    
    This function creates and configures the execution manager based on the
    provided configuration. Strategies and monitors can be provided directly
    to override the default creation logic.
    
    Args:
        config: System configuration dictionary
        strategies: Optional list of pre-configured strategies
        monitors: Optional list of pre-configured monitors
        
    Returns:
        Configured execution manager
    """
    execution_config = config.get("execution_manager", {})
    manager_impl = execution_config.get("implementation", "default")
    
    # Create strategies if not provided
    if strategies is None:
        strategies = []
        strategy_configs = execution_config.get("strategies", [])
        
        for strategy_config in strategy_configs:
            strategy_type = strategy_config.get("type")
            if not strategy_type:
                logger.warning(f"Strategy config missing 'type': {strategy_config}")
                continue
                
            try:
                strategy = await create_execution_strategy(
                    strategy_type, strategy_config
                )
                strategies.append(strategy)
            except Exception as e:
                logger.error(
                    f"Failed to create strategy '{strategy_type}': {e}", 
                    exc_info=True
                )
    
    # Create monitors if not provided
    if monitors is None:
        monitors = []
        monitor_configs = execution_config.get("monitors", [])
        
        for monitor_config in monitor_configs:
            monitor_type = monitor_config.get("type")
            if not monitor_type:
                logger.warning(f"Monitor config missing 'type': {monitor_config}")
                continue
                
            try:
                monitor = await create_transaction_monitor(
                    monitor_type, monitor_config
                )
                monitors.append(monitor)
            except Exception as e:
                logger.error(
                    f"Failed to create monitor '{monitor_type}': {e}", 
                    exc_info=True
                )
    
    # Create manager implementation
    if manager_impl == "default":
        # Import default implementation
        from .execution import DefaultExecutionManager
        
        manager = DefaultExecutionManager(execution_config)
        
        # Register strategies and monitors
        for strategy in strategies:
            strategy_id = getattr(strategy, "strategy_id", f"strategy_{id(strategy)}")
            await manager.register_strategy(strategy, strategy_id)
        
        for monitor in monitors:
            monitor_id = getattr(monitor, "monitor_id", f"monitor_{id(monitor)}")
            await manager.register_monitor(monitor, monitor_id)
        
        return manager
    else:
        # Load custom implementation
        manager = await _load_custom_implementation(
            manager_impl, 
            "ExecutionManager",
            config=execution_config,
        )
        
        # Register strategies and monitors
        for strategy in strategies:
            strategy_id = getattr(strategy, "strategy_id", f"strategy_{id(strategy)}")
            await manager.register_strategy(strategy, strategy_id)
        
        for monitor in monitors:
            monitor_id = getattr(monitor, "monitor_id", f"monitor_{id(monitor)}")
            await manager.register_monitor(monitor, monitor_id)
        
        return manager


async def create_analytics_manager(
    config: Dict[str, Any],
) -> ArbitrageAnalytics:
    """
    Create and configure an analytics manager.
    
    This function creates and configures the analytics manager based on the
    provided configuration.
    
    Args:
        config: System configuration dictionary
        
    Returns:
        Configured analytics manager
    """
    analytics_config = config.get("analytics_manager", {})
    manager_impl = analytics_config.get("implementation", "default")
    
    if manager_impl == "default":
        # Import default implementation
        from .analytics import DefaultAnalyticsManager
        
        return DefaultAnalyticsManager(analytics_config)
    else:
        # Load custom implementation
        return await _load_custom_implementation(
            manager_impl, 
            "ArbitrageAnalytics",
            config=analytics_config,
        )


async def create_market_data_provider(
    config: Dict[str, Any],
) -> MarketDataProvider:
    """
    Create and configure a market data provider.
    
    This function creates and configures the market data provider based on the
    provided configuration.
    
    Args:
        config: System configuration dictionary
        
    Returns:
        Configured market data provider
    """
    market_data_config = config.get("market_data_provider", {})
    provider_impl = market_data_config.get("implementation", "default")
    
    if provider_impl == "default":
        # Import default implementation
        from .market_data import DefaultMarketDataProvider
        
        return DefaultMarketDataProvider(market_data_config)
    else:
        # Load custom implementation
        return await _load_custom_implementation(
            provider_impl, 
            "MarketDataProvider",
            config=market_data_config,
        )


async def create_opportunity_detector(
    detector_type: str,
    config: Dict[str, Any],
) -> OpportunityDetector:
    """
    Create and configure an opportunity detector.
    
    This function creates and configures an opportunity detector based on the
    provided type and configuration.
    
    Args:
        detector_type: Type of detector to create
        config: Detector configuration dictionary
        
    Returns:
        Configured opportunity detector
    """
    # Check for built-in detectors
    if detector_type == "cross_dex":
        from .detectors import CrossDexDetector
        return CrossDexDetector(config)
    elif detector_type == "triangular":
        from .detectors import TriangularDetector
        return TriangularDetector(config)
    elif detector_type == "multi_path":
        from .detectors import MultiPathDetector
        return MultiPathDetector(config)
    else:
        # Load custom implementation
        return await _load_custom_implementation(
            detector_type, 
            "OpportunityDetector",
            config=config,
        )


async def create_opportunity_validator(
    validator_type: str,
    config: Dict[str, Any],
) -> OpportunityValidator:
    """
    Create and configure an opportunity validator.
    
    This function creates and configures an opportunity validator based on the
    provided type and configuration.
    
    Args:
        validator_type: Type of validator to create
        config: Validator configuration dictionary
        
    Returns:
        Configured opportunity validator
    """
    # Check for built-in validators
    if validator_type == "basic":
        from .validators import BasicValidator
        return BasicValidator(config)
    elif validator_type == "simulation":
        from .validators import SimulationValidator
        return SimulationValidator(config)
    elif validator_type == "price_impact":
        from .validators import PriceImpactValidator
        return PriceImpactValidator(config)
    else:
        # Load custom implementation
        return await _load_custom_implementation(
            validator_type, 
            "OpportunityValidator",
            config=config,
        )


async def create_execution_strategy(
    strategy_type: str,
    config: Dict[str, Any],
) -> ExecutionStrategy:
    """
    Create and configure an execution strategy.
    
    This function creates and configures an execution strategy based on the
    provided type and configuration.
    
    Args:
        strategy_type: Type of strategy to create
        config: Strategy configuration dictionary
        
    Returns:
        Configured execution strategy
    """
    # Check for built-in strategies
    if strategy_type == "standard":
        from .strategies import StandardExecutionStrategy
        return StandardExecutionStrategy(config)
    elif strategy_type == "flash_loan":
        from .strategies import FlashLoanExecutionStrategy
        return FlashLoanExecutionStrategy(config)
    elif strategy_type == "flashbots":
        from .strategies import FlashbotsExecutionStrategy
        return FlashbotsExecutionStrategy(config)
    else:
        # Load custom implementation
        return await _load_custom_implementation(
            strategy_type, 
            "ExecutionStrategy",
            config=config,
        )


async def create_transaction_monitor(
    monitor_type: str,
    config: Dict[str, Any],
) -> TransactionMonitor:
    """
    Create and configure a transaction monitor.
    
    This function creates and configures a transaction monitor based on the
    provided type and configuration.
    
    Args:
        monitor_type: Type of monitor to create
        config: Monitor configuration dictionary
        
    Returns:
        Configured transaction monitor
    """
    # Check for built-in monitors
    if monitor_type == "standard":
        from .monitors import StandardTransactionMonitor
        return StandardTransactionMonitor(config)
    elif monitor_type == "enhanced":
        from .monitors import EnhancedTransactionMonitor
        return EnhancedTransactionMonitor(config)
    else:
        # Load custom implementation
        return await _load_custom_implementation(
            monitor_type, 
            "TransactionMonitor",
            config=config,
        )


async def _load_custom_implementation(
    implementation_path: str,
    expected_type: str,
    **kwargs,
) -> Any:
    """
    Load a custom implementation from a module path.
    
    This function loads a custom implementation from a module path and
    instantiates it with the provided arguments.
    
    Args:
        implementation_path: Path to the implementation module
        expected_type: Expected type of the implementation
        **kwargs: Arguments to pass to the implementation constructor
        
    Returns:
        Instantiated implementation
    """
    try:
        # Parse module path and class name
        if ":" in implementation_path:
            module_path, class_name = implementation_path.split(":", 1)
        else:
            module_path = implementation_path
            class_name = None
            
        # Import module
        module = importlib.import_module(module_path)
        
        # Get class from module
        if class_name:
            implementation_class = getattr(module, class_name)
        else:
            # Try to infer class name from expected type
            implementation_class = None
            for name, obj in module.__dict__.items():
                if name.endswith(expected_type) and isinstance(obj, type):
                    implementation_class = obj
                    break
                    
            if implementation_class is None:
                raise ValueError(
                    f"Could not find {expected_type} implementation in {module_path}"
                )
        
        # Create instance
        return implementation_class(**kwargs)
    
    except (ImportError, AttributeError, ValueError) as e:
        logger.error(
            f"Failed to load custom implementation '{implementation_path}': {e}",
            exc_info=True,
        )
        raise