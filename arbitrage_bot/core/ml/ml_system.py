"""Machine learning system for optimizing arbitrage strategies."""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
from pathlib import Path

from ..analytics.analytics_system import AnalyticsSystem
from ..dex.dex_manager import DEXManager
from ..dex.utils import COMMON_TOKENS

logger = logging.getLogger(__name__)

class MLSystem:
    """Machine learning system for trade optimization."""

    def __init__(
        self,
        analytics: AnalyticsSystem,
        dex_manager: DEXManager,
        models_dir: str = "models",
        min_training_samples: int = 1000,
        retraining_interval: int = 24  # hours
    ):
        """Initialize ML system."""
        self.analytics = analytics
        self.dex_manager = dex_manager
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.min_training_samples = min_training_samples
        self.retraining_interval = retraining_interval
        
        # Initialize models
        self.success_classifier = None
        self.profit_regressor = None
        self.scaler = StandardScaler()
        
        # Track last training time
        self.last_training = datetime.min
        
        # Feature importance tracking
        self.feature_importance: Dict[str, float] = {}

    async def predict_trade_success(
        self,
        opportunity: Dict[str, Any]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Predict probability of trade success.
        
        Args:
            opportunity: Trade opportunity details
            
        Returns:
            Tuple[float, Dict[str, Any]]: Success probability and feature importances
        """
        try:
            # Check if models need training
            await self._ensure_models_trained()
            
            if not self.success_classifier:
                return 0.5, {}  # Default to 50% if no model
            
            # Extract features
            features = self._extract_features(opportunity)
            if not features:
                return 0.5, {}
            
            # Scale features
            scaled_features = self.scaler.transform([features])
            
            # Get prediction probability
            prob = self.success_classifier.predict_proba(scaled_features)[0][1]
            
            # Get feature importance
            importance = dict(zip(
                self.feature_importance.keys(),
                self.success_classifier.feature_importances_
            ))
            
            return float(prob), importance
            
        except Exception as e:
            logger.error(f"Error predicting trade success: {e}")
            return 0.5, {}

    async def predict_profit(
        self,
        opportunity: Dict[str, Any]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Predict expected profit for trade.
        
        Args:
            opportunity: Trade opportunity details
            
        Returns:
            Tuple[float, Dict[str, Any]]: Predicted profit and feature importances
        """
        try:
            # Check if models need training
            await self._ensure_models_trained()
            
            if not self.profit_regressor:
                return opportunity.get('profit_usd', 0.0), {}
            
            # Extract features
            features = self._extract_features(opportunity)
            if not features:
                return opportunity.get('profit_usd', 0.0), {}
            
            # Scale features
            scaled_features = self.scaler.transform([features])
            
            # Get prediction
            profit = self.profit_regressor.predict(scaled_features)[0]
            
            # Get feature importance
            importance = dict(zip(
                self.feature_importance.keys(),
                self.profit_regressor.feature_importances_
            ))
            
            return float(profit), importance
            
        except Exception as e:
            logger.error(f"Error predicting profit: {e}")
            return opportunity.get('profit_usd', 0.0), {}

    async def analyze_market_conditions(self) -> Dict[str, Any]:
        """Analyze current market conditions."""
        try:
            conditions = {
                'volatility': {},
                'liquidity': {},
                'competition': {},
                'recommendations': []
            }
            
            # Get recent trades
            trades = self.analytics.trade_metrics[-100:]  # Last 100 trades
            if not trades:
                return conditions
            
            # Calculate volatility
            for dex_name in self.dex_manager.get_dex_names():
                dex_trades = [t for t in trades if t['buy_dex'] == dex_name]
                if dex_trades:
                    prices = [t['amount_out'] / t['amount_in'] for t in dex_trades]
                    conditions['volatility'][dex_name] = np.std(prices)
            
            # Analyze liquidity
            for token in COMMON_TOKENS.values():
                token_trades = [t for t in trades if t['token_in'] == token]
                if token_trades:
                    volumes = [t['amount_in'] for t in token_trades]
                    conditions['liquidity'][token] = np.mean(volumes)
            
            # Analyze competition
            failed_trades = [t for t in trades if not t['success']]
            competition_rate = len(failed_trades) / len(trades)
            conditions['competition']['rate'] = competition_rate
            
            # Generate recommendations
            if competition_rate > 0.2:  # >20% failed trades
                conditions['recommendations'].append(
                    "High competition detected. Consider increasing gas prices."
                )
            
            high_vol_dexes = [
                dex for dex, vol in conditions['volatility'].items()
                if vol > np.mean(list(conditions['volatility'].values()))
            ]
            if high_vol_dexes:
                conditions['recommendations'].append(
                    f"High volatility on {', '.join(high_vol_dexes)}. "
                    "Consider adjusting slippage tolerance."
                )
            
            return conditions
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {e}")
            return {
                'volatility': {},
                'liquidity': {},
                'competition': {},
                'recommendations': [f"Error: {e}"]
            }

    async def _ensure_models_trained(self) -> None:
        """Ensure ML models are trained with recent data."""
        try:
            now = datetime.now()
            if (
                self.success_classifier and
                now - self.last_training < timedelta(hours=self.retraining_interval)
            ):
                return
            
            # Get training data
            trades = self.analytics.trade_metrics
            if len(trades) < self.min_training_samples:
                logger.warning(
                    f"Insufficient training data: {len(trades)} samples, "
                    f"need {self.min_training_samples}"
                )
                return
            
            # Prepare features and labels
            features = []
            success_labels = []
            profit_labels = []
            
            for trade in trades:
                trade_features = self._extract_features(trade)
                if not trade_features:
                    continue
                
                features.append(trade_features)
                success_labels.append(1 if trade['success'] else 0)
                profit_labels.append(trade['profit_usd'])
            
            if not features:
                return
            
            # Split data
            X = np.array(features)
            y_success = np.array(success_labels)
            y_profit = np.array(profit_labels)
            
            X_train, X_test, y_success_train, y_success_test = train_test_split(
                X, y_success, test_size=0.2
            )
            _, _, y_profit_train, y_profit_test = train_test_split(
                X, y_profit, test_size=0.2
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train success classifier
            self.success_classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.success_classifier.fit(X_train_scaled, y_success_train)
            
            # Train profit regressor
            self.profit_regressor = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                random_state=42
            )
            self.profit_regressor.fit(X_train_scaled, y_profit_train)
            
            # Update feature importance
            feature_names = [
                'amount_in',
                'price_impact',
                'gas_cost',
                'path_length',
                'market_volatility',
                'competition_rate',
                'historical_success',
                'liquidity_depth'
            ]
            self.feature_importance = dict(zip(
                feature_names,
                self.success_classifier.feature_importances_
            ))
            
            # Save models
            self._save_models()
            
            # Update training timestamp
            self.last_training = now
            
            # Log performance metrics
            success_score = self.success_classifier.score(X_test_scaled, y_success_test)
            profit_score = self.profit_regressor.score(X_test_scaled, y_profit_test)
            logger.info(
                f"Models trained - Success accuracy: {success_score:.2f}, "
                f"Profit R2: {profit_score:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error training models: {e}")

    def _extract_features(self, trade: Dict[str, Any]) -> Optional[List[float]]:
        """Extract features from trade data."""
        try:
            # Basic features
            features = [
                float(trade['amount_in']),
                float(trade.get('price_impact', 0)),
                float(trade.get('gas_cost_usd', 0)),
                len(trade.get('buy_path', [])),
            ]
            
            # Market features
            market_conditions = self.analyze_market_conditions()
            dex_name = trade.get('buy_dex', '')
            token = trade.get('token_in', '')
            
            features.extend([
                float(market_conditions['volatility'].get(dex_name, 0)),
                float(market_conditions['competition']['rate']),
                float(self._get_historical_success_rate(dex_name)),
                float(market_conditions['liquidity'].get(token, 0))
            ])
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None

    def _get_historical_success_rate(self, dex_name: str) -> float:
        """Get historical success rate for DEX."""
        try:
            dex_stats = self.analytics.dex_metrics.get(dex_name, {})
            total = dex_stats.get('total_trades', 0)
            if total == 0:
                return 0.0
            return dex_stats.get('successful_trades', 0) / total
            
        except Exception as e:
            logger.error(f"Error getting historical success rate: {e}")
            return 0.0

    def _save_models(self) -> None:
        """Save ML models to disk."""
        try:
            if self.success_classifier:
                joblib.dump(
                    self.success_classifier,
                    self.models_dir / 'success_classifier.joblib'
                )
            
            if self.profit_regressor:
                joblib.dump(
                    self.profit_regressor,
                    self.models_dir / 'profit_regressor.joblib'
                )
            
            if self.scaler:
                joblib.dump(
                    self.scaler,
                    self.models_dir / 'scaler.joblib'
                )
                
        except Exception as e:
            logger.error(f"Error saving models: {e}")

    def _load_models(self) -> None:
        """Load ML models from disk."""
        try:
            classifier_path = self.models_dir / 'success_classifier.joblib'
            regressor_path = self.models_dir / 'profit_regressor.joblib'
            scaler_path = self.models_dir / 'scaler.joblib'
            
            if classifier_path.exists():
                self.success_classifier = joblib.load(classifier_path)
            
            if regressor_path.exists():
                self.profit_regressor = joblib.load(regressor_path)
            
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)
                
        except Exception as e:
            logger.error(f"Error loading models: {e}")
