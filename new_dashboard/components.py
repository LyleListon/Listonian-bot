"""
Production Components Module

Provides real system component integrations for the dashboard:
- Web3 Manager with Flashbots integration
- Flash Loan Manager with Balancer integration
- Market Analyzer with multi-path support
- Arbitrage Executor with bundle simulation
"""

from typing import Dict, Any, Optional
from decimal import Decimal

from arbitrage_bot.core.web3.web3_manager import Web3Manager
from arbitrage_bot.core.unified_flash_loan_manager import EnhancedFlashLoanManager
from arbitrage_bot.core.market_analyzer import MarketAnalyzer
from arbitrage_bot.core.arbitrage_executor import ArbitrageExecutor
from arbitrage_bot.core.memory.memory_bank import MemoryBank
from .dashboard.services.system_service import SystemService


def create_production_components(config: Dict[str, Any]) -> Dict[str, Any]:
    """Create production system components."""
    try:
        # Initialize Web3 manager with Flashbots integration
        web3_manager = Web3Manager(config)

        # Initialize flash loan manager with Balancer integration
        flash_loan_manager = EnhancedFlashLoanManager(
            web3=web3_manager.web3,
            flashbots_provider=web3_manager.flashbots_provider,
            memory_bank=MemoryBank(
                storage_dir=config.get("storage", {}).get(
                    "memory_bank_dir", "data/memory_bank"
                )
            ),
        )

        # Initialize market analyzer with multi-path support
        market_analyzer = MarketAnalyzer(web3_manager=web3_manager, config=config)

        # Initialize arbitrage executor with bundle simulation
        arbitrage_executor = ArbitrageExecutor(
            web3_manager=web3_manager,
            flash_loan_manager=flash_loan_manager,
            market_analyzer=market_analyzer,
            config=config,
        )

        # Initialize memory bank
        memory_bank = MemoryBank(
            storage_dir=config.get("storage", {}).get(
                "memory_bank_dir", "data/memory_bank"
            )
        )

        # Initialize system service
        from .dashboard.services.metrics_service import MetricsService
        from .dashboard.services.memory_service import MemoryService

        memory_service = MemoryService("data")
        metrics_service = MetricsService(memory_service)
        system_service = SystemService(memory_service, metrics_service)

        return {
            "web3_manager": web3_manager,
            "flash_loan_manager": flash_loan_manager,
            "market_analyzer": market_analyzer,
            "arbitrage_executor": arbitrage_executor,
            "memory_bank": memory_bank,
            "system_service": system_service,
        }

    except Exception as e:
        raise RuntimeError(f"Failed to initialize production components: {e}")
