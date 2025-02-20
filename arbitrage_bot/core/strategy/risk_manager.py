"""Risk management utilities."""

import logging
from typing import Dict, Any, Optional
from ..analysis.market_analyzer import MarketAnalyzer
from ..web3.web3_manager import Web3Manager

logger = logging.getLogger(__name__)


def create_risk_manager(
    risk_params: Dict[str, Any],
    web3_manager: Web3Manager,
    config: Dict[str, Any]
) -> "RiskManager":
    """
    Create risk manager instance.

    Args:
        risk_params (Dict[str, Any]): Risk management parameters
        web3_manager (Web3Manager): Web3Manager instance
        config (Dict[str, Any]): Configuration dictionary

    Returns:
        RiskManager: Risk manager instance
    """
    return RiskManager(risk_params, web3_manager, config)


class RiskManager:
    """Manages trading risk and exposure."""

    def __init__(self, risk_params: Dict[str, Any], web3_manager: Web3Manager, config: Dict[str, Any]):
        """
        Initialize risk manager.

        Args:
            risk_params (Dict[str, Any]): Risk management parameters
            web3_manager (Web3Manager): Web3Manager instance
            config (Dict[str, Any]): Configuration dictionary
        """
        self.market_analyzer = MarketAnalyzer(web3_manager=web3_manager, config=config)
        self.risk_params = risk_params
        logger.info("Risk manager initialized with params: %s", risk_params)

    async def validate_trade(self, trade_data: Dict[str, Any]) -> bool:
        """
        Validate if trade meets risk criteria.

        Args:
            trade_data (Dict[str, Any]): Trade parameters

        Returns:
            bool: True if trade is valid
        """
        try:
            # Assess trade risk
            risk = await self.assess_trade_risk(trade_data)

            # Check risk score
            if risk["risk_score"] > 0.8:  # 80% risk threshold
                logger.warning(
                    "Trade rejected: Risk score too high (%f)", risk["risk_score"]
                )
                return False

            # Check profit threshold
            min_profit = self.risk_params.get("min_profit_threshold", 0.002)
            if trade_data.get("expected_profit", 0) < min_profit:
                logger.warning("Trade rejected: Profit below threshold")
                return False

            # Check position size
            max_size = min(
                risk["max_position"], self.risk_params.get("max_trade_size", 1.0)
            )
            if trade_data.get("amount", 0) > max_size:
                logger.warning("Trade rejected: Position size too large")
                return False

            # Check liquidity
            min_liquidity = self.risk_params.get("min_liquidity", 1000)
            if risk["conditions"].get("liquidity", 0) * min_liquidity < trade_data.get(
                "amount", 0
            ):
                logger.warning("Trade rejected: Insufficient liquidity")
                return False

            logger.info("Trade validated successfully")
            return True

        except Exception as e:
            logger.error("Error validating trade: %s", e)
            return False

    async def assess_trade_risk(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess risk for potential trade.

        Args:
            trade_data (Dict[str, Any]): Trade parameters

        Returns:
            Dict[str, Any]: Risk assessment
        """
        try:
            # Get market conditions
            conditions = await self.market_analyzer.analyze_market_conditions(
                trade_data["token"]
            )

            # Calculate risk metrics
            risk_score = self._calculate_risk_score(conditions)
            max_position = self._calculate_max_position(conditions)
            stop_loss = self._calculate_stop_loss(conditions)

            return {
                "risk_score": risk_score,
                "max_position": max_position,
                "stop_loss": stop_loss,
                "conditions": conditions,
            }

        except Exception as e:
            logger.error(f"Failed to assess trade risk: {e}")
            return {
                "risk_score": 1.0,  # Maximum risk
                "max_position": 0.0,  # No position
                "stop_loss": None,
                "conditions": {},
            }

    def _calculate_risk_score(self, conditions: Dict[str, Any]) -> float:
        """
        Calculate overall risk score.

        Args:
            conditions (Dict[str, Any]): Market conditions

        Returns:
            float: Risk score between 0 and 1
        """
        # Weight different risk factors
        weights = {"volatility": 0.4, "liquidity": 0.3, "volume": 0.2, "trend": 0.1}

        risk_score = 0.0

        for metric, weight in weights.items():
            value = conditions.get(metric, 0)
            if metric == "liquidity":
                # Invert liquidity since higher is better
                value = 1 - value
            risk_score += value * weight

        return min(max(risk_score, 0.0), 1.0)

    def _calculate_max_position(self, conditions: Dict[str, Any]) -> float:
        """
        Calculate maximum position size.

        Args:
            conditions (Dict[str, Any]): Market conditions

        Returns:
            float: Maximum position size
        """
        base_position = 1.0  # Base position in ETH

        # Adjust based on liquidity
        liquidity_factor = conditions.get("liquidity", 0)
        position = base_position * liquidity_factor

        # Adjust based on volatility
        volatility = conditions.get("volatility", 0)
        if volatility > 0.5:
            position *= 1 - (volatility - 0.5)

        return max(position, 0.0)

    def _calculate_stop_loss(self, conditions: Dict[str, Any]) -> Optional[float]:
        """
        Calculate stop loss price.

        Args:
            conditions (Dict[str, Any]): Market conditions

        Returns:
            Optional[float]: Stop loss price or None
        """
        volatility = conditions.get("volatility", 0)

        if volatility > 0.8:
            # Too volatile for stop loss
            return None

        # Base stop loss at 2%
        stop_loss = 0.02

        # Adjust based on volatility
        stop_loss *= 1 + volatility

        return min(stop_loss, 0.05)  # Cap at 5%
