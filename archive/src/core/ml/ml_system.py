"""Machine learning system for predicting trading opportunities."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path

from ..analytics.analytics_system import AnalyticsSystem
from ...utils.database import Database

logger = logging.getLogger(__name__)

class MLSystem:
    """Machine learning system for market analysis and predictions."""

    def __init__(
        self,
        analytics: AnalyticsSystem,
        market_analyzer: Any,
        config: Dict[str, Any],
        db: Optional[Database] = None,
        models_dir: str = "ml_models"
    ):
        """
        Initialize ML system.

        Args:
            analytics: Analytics system instance
            market_analyzer: Market analyzer instance
            config: Configuration dictionary
            db: Optional Database instance
            models_dir: Directory for saving models
        """
        self.analytics = analytics
        self.market_analyzer = market_analyzer
        self.config = config
        self.db = db if db else Database()
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
        # Initialize models
        self.success_predictor: Optional[RandomForestClassifier] = None
        self.profit_predictor: Optional[GradientBoostingRegressor] = None
        self.feature_scaler: Optional[StandardScaler] = None
        
        # Model performance metrics
        self.metrics = {
            'success_accuracy': 0.0,
            'profit_rmse': 0.0,
            'feature_importance': {}
        }
        
        # Training settings
        self.min_training_samples = 1000
        self.retraining_interval = timedelta(hours=6)
        self.last_training_time = datetime.min

    async def initialize(self) -> bool:
        """Initialize ML system."""
        try:
            # Load saved models if available
            success_model_path = self.models_dir / "success_predictor.joblib"
            profit_model_path = self.models_dir / "profit_predictor.joblib"
            scaler_path = self.models_dir / "feature_scaler.joblib"
            
            if all(p.exists() for p in [success_model_path, profit_model_path, scaler_path]):
                self.success_predictor = joblib.load(success_model_path)
                self.profit_predictor = joblib.load(profit_model_path)
                self.feature_scaler = joblib.load(scaler_path)
                logger.info("Loaded existing ML models")
            else:
                # Train new models
                await self._train_models()
            
            logger.info("ML system initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ML system: {e}")
            return False

    async def predict_trade_success(
        self,
        features: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Predict probability of trade success.

        Args:
            features: Trade features

        Returns:
            Tuple[float, Dict[str, float]]: Success probability and feature importance
        """
        try:
            if not self.success_predictor or not self.feature_scaler:
                return 0.5, {}
                
            # Prepare features
            feature_vector = self._prepare_features(features)
            if feature_vector is None:
                return 0.5, {}
                
            # Make prediction
            success_prob = self.success_predictor.predict_proba(feature_vector)[0][1]
            
            # Get feature importance
            importance = dict(zip(
                self.success_predictor.feature_names_in_,
                self.success_predictor.feature_importances_
            ))
            
            return float(success_prob), importance
            
        except Exception as e:
            logger.error(f"Error predicting trade success: {e}")
            return 0.5, {}

    async def predict_profit(
        self,
        features: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Predict expected profit.

        Args:
            features: Trade features

        Returns:
            Tuple[float, Dict[str, float]]: Expected profit and feature importance
        """
        try:
            if not self.profit_predictor or not self.feature_scaler:
                return 0.0, {}
                
            # Prepare features
            feature_vector = self._prepare_features(features)
            if feature_vector is None:
                return 0.0, {}
                
            # Make prediction
            profit = self.profit_predictor.predict(feature_vector)[0]
            
            # Get feature importance
            importance = dict(zip(
                self.profit_predictor.feature_names_in_,
                self.profit_predictor.feature_importances_
            ))
            
            return float(profit), importance
            
        except Exception as e:
            logger.error(f"Error predicting profit: {e}")
            return 0.0, {}

    async def analyze_market_conditions(self) -> Dict[str, Any]:
        """Analyze current market conditions."""
        try:
            # Get market metrics
            market_metrics = await self.market_analyzer.get_market_metrics()
            
            # Calculate volatility
            volatility = {
                dex: self._calculate_volatility(metrics['price_history'])
                for dex, metrics in market_metrics.items()
            }
            
            # Analyze competition
            competition = await self._analyze_competition()
            
            return {
                'volatility': volatility,
                'competition': competition,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {e}")
            return {}

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current model performance metrics."""
        return self.metrics.copy()

    async def retrain_if_needed(self) -> bool:
        """Check if retraining is needed and retrain if necessary."""
        try:
            if (
                datetime.now() - self.last_training_time > self.retraining_interval or
                not self.success_predictor or
                not self.profit_predictor
            ):
                return await self._train_models()
            return True
            
        except Exception as e:
            logger.error(f"Error checking retraining need: {e}")
            return False

    def _prepare_features(self, features: Dict[str, Any]) -> Optional[np.ndarray]:
        """Prepare features for prediction."""
        try:
            # Convert to DataFrame
            df = pd.DataFrame([features])
            
            # Scale features
            if self.feature_scaler:
                return self.feature_scaler.transform(df)
            return None
            
        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            return None

    async def _train_models(self) -> bool:
        """Train ML models."""
        try:
            # Get training data
            trades = await self.db.get_trades({})
            if len(trades) < self.min_training_samples:
                logger.warning("Insufficient training data")
                return False
                
            # Prepare training data
            X, y_success, y_profit = self._prepare_training_data(trades)
            
            # Train success predictor
            self.success_predictor = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.success_predictor.fit(X, y_success)
            
            # Train profit predictor
            self.profit_predictor = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                random_state=42
            )
            self.profit_predictor.fit(X, y_profit)
            
            # Update metrics
            self.metrics['success_accuracy'] = self.success_predictor.score(X, y_success)
            self.metrics['profit_rmse'] = np.sqrt(np.mean(
                (y_profit - self.profit_predictor.predict(X)) ** 2
            ))
            
            # Save models
            joblib.dump(self.success_predictor, self.models_dir / "success_predictor.joblib")
            joblib.dump(self.profit_predictor, self.models_dir / "profit_predictor.joblib")
            joblib.dump(self.feature_scaler, self.models_dir / "feature_scaler.joblib")
            
            self.last_training_time = datetime.now()
            logger.info("Successfully trained ML models")
            return True
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
            return False

    def _prepare_training_data(
        self,
        trades: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare training data from trades."""
        try:
            # Extract features and labels
            features = []
            success_labels = []
            profit_labels = []
            
            for trade in trades:
                # Extract features
                trade_features = {
                    'gas_price': trade['gas_price'],
                    'gas_limit': trade['gas'],
                    'value': trade['value'],
                    'input_length': len(trade['input']),
                    'market_volatility': trade.get('market_volatility', 0),
                    'competition_rate': trade.get('competition_rate', 0)
                }
                features.append(trade_features)
                
                # Extract labels
                success_labels.append(trade['status'] == 'completed')
                profit_labels.append(float(trade.get('profit', 0)))
            
            # Convert to DataFrame and scale features
            X = pd.DataFrame(features)
            self.feature_scaler = StandardScaler()
            X_scaled = self.feature_scaler.fit_transform(X)
            
            return (
                X_scaled,
                np.array(success_labels),
                np.array(profit_labels)
            )
            
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            return np.array([]), np.array([]), np.array([])

    def _calculate_volatility(self, price_history: List[float]) -> float:
        """Calculate price volatility."""
        try:
            if len(price_history) < 2:
                return 0.0
                
            returns = np.diff(price_history) / price_history[:-1]
            return float(np.std(returns))
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.0

    async def _analyze_competition(self) -> Dict[str, Any]:
        """Analyze competition level."""
        try:
            # Get recent trades
            recent_trades = await self.db.get_trades({
                'timestamp': {
                    '$gte': datetime.now() - timedelta(hours=1)
                }
            })
            
            if not recent_trades:
                return {'rate': 0.0, 'active_traders': 0}
                
            # Count unique traders
            unique_traders = len(set(t['from'] for t in recent_trades))
            
            # Calculate competition rate
            trades_per_minute = len(recent_trades) / 60
            
            return {
                'rate': float(trades_per_minute),
                'active_traders': unique_traders
            }
            
        except Exception as e:
            logger.error(f"Error analyzing competition: {e}")
            return {'rate': 0.0, 'active_traders': 0}


async def create_ml_system(
    analytics: AnalyticsSystem,
    market_analyzer: Any,
    config: Dict[str, Any],
    db: Optional[Database] = None
) -> Optional[MLSystem]:
    """
    Create ML system instance.

    Args:
        analytics: Analytics system instance
        market_analyzer: Market analyzer instance
        config: Configuration dictionary
        db: Optional Database instance

    Returns:
        Optional[MLSystem]: ML system instance
    """
    try:
        system = MLSystem(
            analytics=analytics,
            market_analyzer=market_analyzer,
            config=config,
            db=db
        )
        
        success = await system.initialize()
        if not success:
            raise ValueError("Failed to initialize ML system")
            
        return system
        
    except Exception as e:
        logger.error(f"Failed to create ML system: {e}")
        return None
