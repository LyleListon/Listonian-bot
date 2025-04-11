"""Strategy Configuration Manager"""

import json
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class StrategyConfig:
    """Manages strategy configuration for arbitrage bot"""

    def __init__(self, config_path: str = None):
        """Initialize strategy config manager"""
        # Get configs/data directory relative to this file
        config_dir = Path(__file__).parent / "data"

        # Set default config path if not provided
        if config_path is None:
            config_path = str(config_dir / "strategy_config.json")

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_path) as f:
                config = json.load(f)
            logger.info(f"Loaded strategy config from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading strategy config: {e}")
            return {}

    def get_arbitrage_strategy_params(self) -> Dict[str, Any]:
        """Get arbitrage strategy parameters"""
        try:
            return {
                "min_profit_threshold": 0.1,  # Changed to 0.1%
                "max_trade_amount": 0.5,  # ETH
                "gas_cost_buffer": 0.2,  # 20%
                "slippage_tolerance": 0.01,  # 1%
            }
        except Exception as e:
            logger.error(f"Error getting arbitrage strategy params: {e}")
            return {}

    def get_risk_management_params(self) -> Dict[str, Any]:
        """Get risk management parameters"""
        try:
            return {
                "max_concurrent_trades": 3,
                "trade_cooldown": 300,  # 5 minutes
                "max_slippage": 0.01,  # 1%
                "min_liquidity": 1000,  # USDC
            }
        except Exception as e:
            logger.error(f"Error getting risk management params: {e}")
            return {}

    def get_enabled_pairs(self) -> List[str]:
        """Get list of enabled trading pairs"""
        try:
            # Get pairs from config
            pairs = []
            for pair in self.config.get("pairs", []):
                pairs.append(pair["name"])
            logger.info(f"Enabled pairs: {pairs}")
            return pairs
        except Exception as e:
            logger.error(f"Error getting enabled pairs: {e}")
            return []

    def get_dex_config(self) -> Dict[str, Any]:
        """Get DEX configuration"""
        try:
            return self.config.get("dexes", {})
        except Exception as e:
            logger.error(f"Error getting DEX config: {e}")
            return {}

    def get_token_config(self) -> Dict[str, Any]:
        """Get token configuration"""
        try:
            return self.config.get("tokens", {})
        except Exception as e:
            logger.error(f"Error getting token config: {e}")
            return {}

    def get_pool_config(self, pair_name: str) -> Dict[str, str]:
        """Get pool addresses for a trading pair"""
        try:
            for pair in self.config.get("pairs", []):
                if pair["name"] == pair_name:
                    return pair.get("pools", {})
            return {}
        except Exception as e:
            logger.error(f"Error getting pool config: {e}")
            return {}

    def get_min_profit_threshold(self, pair_name: str) -> float:
        """Get minimum profit threshold for a trading pair"""
        try:
            for pair in self.config.get("pairs", []):
                if pair["name"] == pair_name:
                    return pair.get("min_profit_threshold", 0.002)  # Default to 0.2%
            return 0.002
        except Exception as e:
            logger.error(f"Error getting min profit threshold: {e}")
            return 0.002

    def get_max_trade_size(self, pair_name: str) -> float:
        """Get maximum trade size for a trading pair"""
        try:
            for pair in self.config.get("pairs", []):
                if pair["name"] == pair_name:
                    return pair.get("max_trade_size", 0.5)  # Default to 0.5 ETH
            return 0.5
        except Exception as e:
            logger.error(f"Error getting max trade size: {e}")
            return 0.5


# Singleton instance
_strategy_config = None


def create_strategy_config() -> StrategyConfig:
    """Factory function to create StrategyConfig instance"""
    return StrategyConfig()


def get_strategy_config() -> StrategyConfig:
    """Get strategy config singleton instance"""
    global _strategy_config
    if _strategy_config is None:
        _strategy_config = create_strategy_config()
    return _strategy_config
