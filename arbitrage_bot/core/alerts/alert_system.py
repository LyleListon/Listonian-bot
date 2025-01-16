"""Alert system for monitoring and notifications."""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from ..analytics.analytics_system import AnalyticsSystem
from ..monitoring.transaction_monitor import TransactionMonitor
from ..analysis.market_analyzer import MarketAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class AlertCondition:
    """Alert condition configuration."""
    type: str  # price, volume, gas, trend, etc.
    symbol: Optional[str]  # Token symbol for price/volume alerts
    operator: str  # above, below, equals, crosses
    value: Decimal  # Threshold value
    cooldown: int  # Minimum time between alerts (seconds)
    enabled: bool

@dataclass
class Alert:
    """Alert instance."""
    condition: AlertCondition
    timestamp: float
    message: str
    severity: str  # info, warning, error
    acknowledged: bool

class AlertSystem:
    """Monitors conditions and generates alerts."""

    def __init__(
        self,
        analytics: AnalyticsSystem,
        tx_monitor: TransactionMonitor,
        market_analyzer: MarketAnalyzer,
        config: Dict[str, Any]
    ):
        """Initialize alert system.

        Args:
            analytics: Analytics system instance
            tx_monitor: Transaction monitor instance
            market_analyzer: Market analyzer instance
            config: Configuration dictionary
        """
        self.analytics = analytics
        self.tx_monitor = tx_monitor
        self.market_analyzer = market_analyzer
        self.config = config
        
        # Alert configuration
        self.conditions: Dict[str, AlertCondition] = {}
        self.alerts: List[Alert] = []
        self.last_triggered: Dict[str, float] = {}
        
        # Alert handlers
        self.alert_handlers: Set[Any] = set()
        
        # Default conditions
        self._setup_default_conditions()
        
        logger.info("Alert system initialized")

    def _setup_default_conditions(self):
        """Set up default alert conditions."""
        try:
            # Price alerts
            self.add_condition(
                "price_high",
                AlertCondition(
                    type="price",
                    symbol="WETH",
                    operator="above",
                    value=Decimal("2000"),  # $2000
                    cooldown=300,  # 5 minutes
                    enabled=True
                )
            )
            
            # Volume alerts
            self.add_condition(
                "volume_low",
                AlertCondition(
                    type="volume",
                    symbol="WETH",
                    operator="below",
                    value=Decimal("1000000"),  # $1M
                    cooldown=3600,  # 1 hour
                    enabled=True
                )
            )
            
            # Gas alerts
            self.add_condition(
                "gas_high",
                AlertCondition(
                    type="gas",
                    symbol=None,
                    operator="above",
                    value=Decimal("100"),  # 100 GWEI
                    cooldown=300,  # 5 minutes
                    enabled=True
                )
            )
            
            # Trend alerts
            self.add_condition(
                "trend_change",
                AlertCondition(
                    type="trend",
                    symbol="WETH",
                    operator="crosses",
                    value=Decimal("0"),  # Direction change
                    cooldown=900,  # 15 minutes
                    enabled=True
                )
            )
            
            # Success rate alerts
            self.add_condition(
                "success_rate_low",
                AlertCondition(
                    type="success_rate",
                    symbol=None,
                    operator="below",
                    value=Decimal("0.8"),  # 80%
                    cooldown=1800,  # 30 minutes
                    enabled=True
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to set up default conditions: {e}")

    def add_condition(self, name: str, condition: AlertCondition):
        """Add or update alert condition."""
        try:
            self.conditions[name] = condition
            logger.info(f"Added alert condition: {name}")
        except Exception as e:
            logger.error(f"Failed to add condition {name}: {e}")

    def remove_condition(self, name: str):
        """Remove alert condition."""
        try:
            if name in self.conditions:
                del self.conditions[name]
                logger.info(f"Removed alert condition: {name}")
        except Exception as e:
            logger.error(f"Failed to remove condition {name}: {e}")

    def add_handler(self, handler: Any):
        """Add alert handler."""
        self.alert_handlers.add(handler)

    def remove_handler(self, handler: Any):
        """Remove alert handler."""
        self.alert_handlers.discard(handler)

    async def start_monitoring(self):
        """Start alert monitoring."""
        try:
            while True:
                try:
                    await self._check_conditions()
                except Exception as e:
                    logger.error(f"Error checking conditions: {e}")
                    
                await asyncio.sleep(5)  # Check every 5 seconds
                
        except Exception as e:
            logger.error(f"Alert monitoring failed: {e}")
            raise

    async def _check_conditions(self):
        """Check all alert conditions."""
        current_time = time.time()
        
        for name, condition in self.conditions.items():
            try:
                if not condition.enabled:
                    continue
                    
                # Check cooldown
                last_trigger = self.last_triggered.get(name, 0)
                if current_time - last_trigger < condition.cooldown:
                    continue
                    
                # Check condition
                triggered = False
                message = ""
                severity = "info"
                
                if condition.type == "price":
                    triggered, message, severity = await self._check_price_condition(condition)
                elif condition.type == "volume":
                    triggered, message, severity = await self._check_volume_condition(condition)
                elif condition.type == "gas":
                    triggered, message, severity = await self._check_gas_condition(condition)
                elif condition.type == "trend":
                    triggered, message, severity = await self._check_trend_condition(condition)
                elif condition.type == "success_rate":
                    triggered, message, severity = await self._check_success_rate_condition(condition)
                    
                if triggered:
                    # Create alert
                    alert = Alert(
                        condition=condition,
                        timestamp=current_time,
                        message=message,
                        severity=severity,
                        acknowledged=False
                    )
                    
                    # Add to history
                    self.alerts.append(alert)
                    
                    # Update last triggered
                    self.last_triggered[name] = current_time
                    
                    # Notify handlers
                    await self._notify_handlers(alert)
                    
            except Exception as e:
                logger.error(f"Failed to check condition {name}: {e}")

    async def _check_price_condition(self, condition: AlertCondition) -> tuple[bool, str, str]:
        """Check price alert condition."""
        try:
            market = await self.market_analyzer.get_market_condition(condition.symbol)
            if not market:
                return False, "", "info"
                
            price = market.price
            
            if condition.operator == "above" and price > condition.value:
                return True, f"{condition.symbol} price above ${condition.value:,.2f}", "warning"
            elif condition.operator == "below" and price < condition.value:
                return True, f"{condition.symbol} price below ${condition.value:,.2f}", "warning"
                
            return False, "", "info"
            
        except Exception as e:
            logger.error(f"Failed to check price condition: {e}")
            return False, "", "info"

    async def _check_volume_condition(self, condition: AlertCondition) -> tuple[bool, str, str]:
        """Check volume alert condition."""
        try:
            market = await self.market_analyzer.get_market_condition(condition.symbol)
            if not market:
                return False, "", "info"
                
            volume = market.volume_24h
            
            if condition.operator == "above" and volume > condition.value:
                return True, f"{condition.symbol} volume above ${condition.value:,.0f}", "info"
            elif condition.operator == "below" and volume < condition.value:
                return True, f"{condition.symbol} volume below ${condition.value:,.0f}", "warning"
                
            return False, "", "info"
            
        except Exception as e:
            logger.error(f"Failed to check volume condition: {e}")
            return False, "", "info"

    async def _check_gas_condition(self, condition: AlertCondition) -> tuple[bool, str, str]:
        """Check gas alert condition."""
        try:
            # Get gas metrics from gas optimizer
            gas_price = await self.analytics.gas_optimizer.get_optimal_gas_price()
            if not gas_price:
                return False, "", "info"
                
            gas_price_gwei = gas_price / 10**9  # Convert to GWEI
            
            if condition.operator == "above" and gas_price_gwei > condition.value:
                return True, f"Gas price above {condition.value:.0f} GWEI ({gas_price_gwei:.0f} GWEI)", "warning"
            elif condition.operator == "below" and gas_price_gwei < condition.value:
                return True, f"Gas price below {condition.value:.0f} GWEI ({gas_price_gwei:.0f} GWEI)", "info"
                
            return False, "", "info"
            
        except Exception as e:
            logger.error(f"Failed to check gas condition: {e}")
            return False, "", "info"

    async def _check_trend_condition(self, condition: AlertCondition) -> tuple[bool, str, str]:
        """Check trend alert condition."""
        try:
            market = await self.market_analyzer.get_market_condition(condition.symbol)
            if not market:
                return False, "", "info"
                
            if condition.operator == "crosses":
                # Check if trend direction changed
                last_trend = self.alerts[-1].condition.value if self.alerts else None
                current_trend = market.trend.direction
                
                if last_trend and current_trend != last_trend:
                    return True, f"{condition.symbol} trend changed to {current_trend}", "warning"
                    
            return False, "", "info"
            
        except Exception as e:
            logger.error(f"Failed to check trend condition: {e}")
            return False, "", "info"

    async def _check_success_rate_condition(self, condition: AlertCondition) -> tuple[bool, str, str]:
        """Check success rate alert condition."""
        try:
            metrics = await self.tx_monitor.get_metrics()
            if not metrics:
                return False, "", "info"
                
            success_rate = metrics["success_rate"]
            
            if condition.operator == "below" and success_rate < float(condition.value):
                return True, f"Success rate below {float(condition.value):.0%}", "error"
                
            return False, "", "info"
            
        except Exception as e:
            logger.error(f"Failed to check success rate condition: {e}")
            return False, "", "info"

    async def _notify_handlers(self, alert: Alert):
        """Notify all alert handlers."""
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Failed to notify handler: {e}")

    def get_alerts(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None
    ) -> List[Alert]:
        """Get filtered alerts."""
        try:
            alerts = self.alerts
            
            if start_time:
                alerts = [a for a in alerts if a.timestamp >= start_time]
            if end_time:
                alerts = [a for a in alerts if a.timestamp <= end_time]
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            if acknowledged is not None:
                alerts = [a for a in alerts if a.acknowledged == acknowledged]
                
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []

    def acknowledge_alert(self, alert: Alert):
        """Mark alert as acknowledged."""
        try:
            alert.acknowledged = True
            logger.info(f"Alert acknowledged: {alert.message}")
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")

async def create_alert_system(
    analytics: AnalyticsSystem,
    tx_monitor: TransactionMonitor,
    market_analyzer: MarketAnalyzer,
    config: Dict[str, Any]
) -> AlertSystem:
    """Create and start alert system."""
    try:
        system = AlertSystem(analytics, tx_monitor, market_analyzer, config)
        asyncio.create_task(system.start_monitoring())
        return system
    except Exception as e:
        logger.error(f"Failed to create alert system: {e}")
        raise
