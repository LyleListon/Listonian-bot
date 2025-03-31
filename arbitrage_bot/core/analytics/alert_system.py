"""
Alert System Module

Provides alerting capabilities for the arbitrage system.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Callable
from decimal import Decimal
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class AlertSystem:
    """
    Manages alerts for the arbitrage system.
    
    Features:
    - Threshold-based alerts
    - Anomaly detection alerts
    - Predictive alerts
    - Notification delivery through multiple channels
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the alert system.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.initialized = False
        self.lock = asyncio.Lock()
        
        # Alert settings
        self.alert_thresholds = self.config.get('alert_thresholds', {})
        self.alert_channels = self.config.get('alert_channels', ['log'])
        self.alert_cooldown = int(self.config.get('alert_cooldown', 300))  # 5 minutes
        
        # Storage for alerts
        self._alerts = []
        self._last_alert_times = {}
        
        # Storage paths
        self.storage_dir = self.config.get('storage_dir', 'analytics')
        self.alerts_file = os.path.join(self.storage_dir, 'alerts.json')
        
        # Notification handlers
        self._notification_handlers = {
            'log': self._notify_log,
            'email': self._notify_email,
            'webhook': self._notify_webhook,
            'telegram': self._notify_telegram
        }
        
        # Anomaly detection settings
        self.anomaly_detection_enabled = self.config.get('anomaly_detection_enabled', True)
        self.anomaly_sensitivity = float(self.config.get('anomaly_sensitivity', 2.0))  # Standard deviations
        
        # Predictive alert settings
        self.predictive_alerts_enabled = self.config.get('predictive_alerts_enabled', True)
        self.prediction_horizon = int(self.config.get('prediction_horizon', 24))  # hours
        
    async def initialize(self) -> bool:
        """
        Initialize the alert system.
        
        Returns:
            True if initialization successful
        """
        try:
            # Create storage directory if it doesn't exist
            os.makedirs(self.storage_dir, exist_ok=True)
            
            # Load historical alerts if available
            await self._load_alerts()
            
            self.initialized = True
            logger.info("Alert system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize alert system: {e}")
            return False
    
    async def _load_alerts(self) -> None:
        """Load historical alerts from storage."""
        try:
            if os.path.exists(self.alerts_file):
                async with self.lock:
                    with open(self.alerts_file, 'r') as f:
                        data = json.load(f)
                    
                    # Convert string timestamps to datetime objects
                    for alert in data:
                        if 'timestamp' in alert:
                            alert['timestamp'] = datetime.fromisoformat(alert['timestamp'])
                    
                    self._alerts = data
                    logger.info(f"Loaded {len(data)} historical alerts")
            else:
                logger.info("No historical alerts found")
        except Exception as e:
            logger.error(f"Error loading historical alerts: {e}")
    
    async def _save_alerts(self) -> None:
        """Save alerts to storage."""
        try:
            async with self.lock:
                # Convert datetime objects to ISO format strings for JSON serialization
                data_to_save = []
                for alert in self._alerts:
                    alert_copy = alert.copy()
                    if isinstance(alert_copy.get('timestamp'), datetime):
                        alert_copy['timestamp'] = alert_copy['timestamp'].isoformat()
                    data_to_save.append(alert_copy)
                
                with open(self.alerts_file, 'w') as f:
                    json.dump(data_to_save, f, indent=2)
                
                logger.info(f"Saved {len(data_to_save)} alerts to {self.alerts_file}")
        except Exception as e:
            logger.error(f"Error saving alerts: {e}")
    
    async def add_alert(self, alert_type: str, message: str, severity: str = "info", 
                       data: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new alert.
        
        Args:
            alert_type: Type of alert (e.g., "threshold", "anomaly", "predictive")
            message: Alert message
            severity: Alert severity ("info", "warning", "error", "critical")
            data: Optional additional data
        """
        if not self.initialized:
            raise RuntimeError("Alert system not initialized")
        
        # Create alert object
        alert = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.utcnow(),
            'data': data or {}
        }
        
        async with self.lock:
            # Add to alerts
            self._alerts.append(alert)
            
            # Save to storage
            await self._save_alerts()
            
            # Send notifications
            await self._send_notifications(alert)
    
    async def _send_notifications(self, alert: Dict[str, Any]) -> None:
        """Send notifications for an alert through configured channels."""
        # Check cooldown
        alert_key = f"{alert['type']}_{alert['severity']}"
        current_time = asyncio.get_event_loop().time()
        
        if alert_key in self._last_alert_times:
            time_since_last = current_time - self._last_alert_times[alert_key]
            if time_since_last < self.alert_cooldown:
                logger.debug(f"Skipping notification for {alert_key} due to cooldown")
                return
        
        # Update last alert time
        self._last_alert_times[alert_key] = current_time
        
        # Send through each channel
        for channel in self.alert_channels:
            handler = self._notification_handlers.get(channel)
            if handler:
                try:
                    await handler(alert)
                except Exception as e:
                    logger.error(f"Error sending notification through {channel}: {e}")
            else:
                logger.warning(f"Unknown notification channel: {channel}")
    
    async def _notify_log(self, alert: Dict[str, Any]) -> None:
        """Send notification through logging."""
        severity = alert['severity']
        message = f"ALERT [{severity.upper()}]: {alert['message']}"
        
        if severity == "critical":
            logger.critical(message)
        elif severity == "error":
            logger.error(message)
        elif severity == "warning":
            logger.warning(message)
        else:  # info
            logger.info(message)
    
    async def _notify_email(self, alert: Dict[str, Any]) -> None:
        """Send notification through email."""
        # This is a placeholder - in a real implementation, we would use an email library
        email_config = self.config.get('email', {})
        recipients = email_config.get('recipients', [])
        
        if not recipients:
            logger.warning("No email recipients configured")
            return
        
        logger.info(f"Would send email alert to {recipients}: {alert['message']}")
    
    async def _notify_webhook(self, alert: Dict[str, Any]) -> None:
        """Send notification through webhook."""
        # This is a placeholder - in a real implementation, we would use aiohttp or similar
        webhook_config = self.config.get('webhook', {})
        url = webhook_config.get('url')
        
        if not url:
            logger.warning("No webhook URL configured")
            return
        
        logger.info(f"Would send webhook alert to {url}: {alert['message']}")
    
    async def _notify_telegram(self, alert: Dict[str, Any]) -> None:
        """Send notification through Telegram."""
        # This is a placeholder - in a real implementation, we would use a Telegram API library
        telegram_config = self.config.get('telegram', {})
        chat_id = telegram_config.get('chat_id')
        
        if not chat_id:
            logger.warning("No Telegram chat ID configured")
            return
        
        logger.info(f"Would send Telegram alert to {chat_id}: {alert['message']}")
    
    async def check_threshold_alerts(self, metrics: Dict[str, Any]) -> None:
        """
        Check for threshold-based alerts.
        
        Args:
            metrics: Dictionary of metrics to check against thresholds
        """
        if not self.initialized:
            raise RuntimeError("Alert system not initialized")
        
        for metric_name, metric_value in metrics.items():
            # Check if we have thresholds for this metric
            if metric_name not in self.alert_thresholds:
                continue
            
            thresholds = self.alert_thresholds[metric_name]
            
            # Check critical threshold
            if 'critical' in thresholds and self._check_threshold(metric_value, thresholds['critical']):
                await self.add_alert(
                    alert_type="threshold",
                    message=f"{metric_name} has reached a critical level: {metric_value}",
                    severity="critical",
                    data={
                        'metric_name': metric_name,
                        'metric_value': metric_value,
                        'threshold': thresholds['critical']
                    }
                )
            # Check error threshold
            elif 'error' in thresholds and self._check_threshold(metric_value, thresholds['error']):
                await self.add_alert(
                    alert_type="threshold",
                    message=f"{metric_name} has reached an error level: {metric_value}",
                    severity="error",
                    data={
                        'metric_name': metric_name,
                        'metric_value': metric_value,
                        'threshold': thresholds['error']
                    }
                )
            # Check warning threshold
            elif 'warning' in thresholds and self._check_threshold(metric_value, thresholds['warning']):
                await self.add_alert(
                    alert_type="threshold",
                    message=f"{metric_name} has reached a warning level: {metric_value}",
                    severity="warning",
                    data={
                        'metric_name': metric_name,
                        'metric_value': metric_value,
                        'threshold': thresholds['warning']
                    }
                )
            # Check info threshold
            elif 'info' in thresholds and self._check_threshold(metric_value, thresholds['info']):
                await self.add_alert(
                    alert_type="threshold",
                    message=f"{metric_name} has reached an info level: {metric_value}",
                    severity="info",
                    data={
                        'metric_name': metric_name,
                        'metric_value': metric_value,
                        'threshold': thresholds['info']
                    }
                )
    
    def _check_threshold(self, value: Any, threshold: Dict[str, Any]) -> bool:
        """
        Check if a value exceeds a threshold.
        
        Args:
            value: Value to check
            threshold: Threshold configuration with operator and value
            
        Returns:
            True if threshold is exceeded
        """
        operator = threshold.get('operator', '>')
        threshold_value = threshold.get('value', 0)
        
        if operator == '>':
            return value > threshold_value
        elif operator == '>=':
            return value >= threshold_value
        elif operator == '<':
            return value < threshold_value
        elif operator == '<=':
            return value <= threshold_value
        elif operator == '==':
            return value == threshold_value
        elif operator == '!=':
            return value != threshold_value
        else:
            logger.warning(f"Unknown threshold operator: {operator}")
            return False
    
    async def check_anomaly_alerts(self, metric_name: str, current_value: float, 
                                  historical_values: List[float]) -> None:
        """
        Check for anomaly-based alerts.
        
        Args:
            metric_name: Name of the metric
            current_value: Current value of the metric
            historical_values: List of historical values for the metric
        """
        if not self.initialized or not self.anomaly_detection_enabled:
            return
        
        if len(historical_values) < 10:
            # Not enough data for anomaly detection
            return
        
        # Calculate mean and standard deviation
        mean = sum(historical_values) / len(historical_values)
        variance = sum((x - mean) ** 2 for x in historical_values) / len(historical_values)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            # No variation in historical data
            return
        
        # Calculate z-score
        z_score = abs(current_value - mean) / std_dev
        
        # Check if it's an anomaly
        if z_score > self.anomaly_sensitivity:
            direction = "above" if current_value > mean else "below"
            await self.add_alert(
                alert_type="anomaly",
                message=f"Anomaly detected in {metric_name}: {current_value} is {direction} normal range",
                severity="warning" if z_score < self.anomaly_sensitivity * 1.5 else "error",
                data={
                    'metric_name': metric_name,
                    'current_value': current_value,
                    'mean': mean,
                    'std_dev': std_dev,
                    'z_score': z_score
                }
            )
    
    async def add_predictive_alert(self, metric_name: str, predicted_value: float, 
                                  prediction_time: datetime, confidence: float) -> None:
        """
        Add a predictive alert.
        
        Args:
            metric_name: Name of the metric
            predicted_value: Predicted value of the metric
            prediction_time: Time of the prediction
            confidence: Confidence level (0-1)
        """
        if not self.initialized or not self.predictive_alerts_enabled:
            return
        
        # Check if we have thresholds for this metric
        if metric_name not in self.alert_thresholds:
            return
        
        thresholds = self.alert_thresholds[metric_name]
        
        # Find the highest severity threshold that would be triggered
        severity = "info"
        threshold_value = None
        threshold_operator = None
        
        for level in ['critical', 'error', 'warning', 'info']:
            if level in thresholds and self._check_threshold(predicted_value, thresholds[level]):
                severity = level
                threshold_value = thresholds[level].get('value')
                threshold_operator = thresholds[level].get('operator')
                break
        
        if threshold_value is not None:
            time_until = (prediction_time - datetime.utcnow()).total_seconds() / 3600  # hours
            
            await self.add_alert(
                alert_type="predictive",
                message=f"Predicted {metric_name} will be {threshold_operator} {threshold_value} in {time_until:.1f} hours",
                severity=severity,
                data={
                    'metric_name': metric_name,
                    'predicted_value': predicted_value,
                    'prediction_time': prediction_time.isoformat(),
                    'confidence': confidence,
                    'threshold_value': threshold_value,
                    'threshold_operator': threshold_operator
                }
            )
    
    async def get_alerts(self, alert_type: Optional[str] = None, 
                        severity: Optional[str] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get alerts with filtering.
        
        Args:
            alert_type: Optional filter by alert type
            severity: Optional filter by severity
            start_time: Optional filter by start time
            end_time: Optional filter by end time
            limit: Maximum number of alerts to return
            
        Returns:
            List of alerts matching the filters
        """
        if not self.initialized:
            raise RuntimeError("Alert system not initialized")
        
        async with self.lock:
            # Apply filters
            filtered_alerts = self._alerts
            
            if alert_type:
                filtered_alerts = [a for a in filtered_alerts if a.get('type') == alert_type]
            
            if severity:
                filtered_alerts = [a for a in filtered_alerts if a.get('severity') == severity]
            
            if start_time:
                filtered_alerts = [a for a in filtered_alerts if a.get('timestamp', datetime.min) >= start_time]
            
            if end_time:
                filtered_alerts = [a for a in filtered_alerts if a.get('timestamp', datetime.max) <= end_time]
            
            # Sort by timestamp (newest first)
            filtered_alerts.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
            
            # Apply limit
            return filtered_alerts[:limit]
    
    async def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get a summary of alerts.
        
        Returns:
            Dictionary with alert summary
        """
        if not self.initialized:
            raise RuntimeError("Alert system not initialized")
        
        async with self.lock:
            # Count alerts by type and severity
            type_counts = {}
            severity_counts = {
                'info': 0,
                'warning': 0,
                'error': 0,
                'critical': 0
            }
            
            # Count alerts in the last 24 hours
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)
            alerts_24h = 0
            
            for alert in self._alerts:
                # Count by type
                alert_type = alert.get('type', 'unknown')
                if alert_type not in type_counts:
                    type_counts[alert_type] = 0
                type_counts[alert_type] += 1
                
                # Count by severity
                severity = alert.get('severity', 'info')
                if severity in severity_counts:
                    severity_counts[severity] += 1
                
                # Count in last 24 hours
                if alert.get('timestamp', datetime.min) >= last_24h:
                    alerts_24h += 1
            
            return {
                'total_alerts': len(self._alerts),
                'alerts_24h': alerts_24h,
                'by_type': type_counts,
                'by_severity': severity_counts,
                'latest_alert': self._alerts[-1] if self._alerts else None
            }
    
    def set_alert_threshold(self, metric_name: str, severity: str, operator: str, value: Any) -> None:
        """
        Set an alert threshold.
        
        Args:
            metric_name: Name of the metric
            severity: Alert severity ("info", "warning", "error", "critical")
            operator: Comparison operator (">", ">=", "<", "<=", "==", "!=")
            value: Threshold value
        """
        if metric_name not in self.alert_thresholds:
            self.alert_thresholds[metric_name] = {}
        
        self.alert_thresholds[metric_name][severity] = {
            'operator': operator,
            'value': value
        }
        
        logger.info(f"Set {severity} threshold for {metric_name}: {operator} {value}")

async def create_alert_system(config: Optional[Dict[str, Any]] = None) -> AlertSystem:
    """
    Create and initialize an alert system.
    
    Args:
        config: Optional configuration
        
    Returns:
        Initialized AlertSystem instance
    """
    alert_system = AlertSystem(config)
    if not await alert_system.initialize():
        raise RuntimeError("Failed to initialize alert system")
    return alert_system