# Dual LSTM System: Gas Price & Liquidity Analysis

## System Overview

```python
class DualLSTMPredictor:
    """Combined gas price and liquidity prediction system"""
    
    def __init__(self):
        self.gas_predictor = GasPriceLSTM()
        self.liquidity_predictor = LiquidityLSTM()
        self.transaction_analyzer = TransactionViabilityAnalyzer()
```

## 1. Gas Price Prediction System

```python
class GasPriceLSTM:
    def __init__(self):
        self.features = {
            'base_fee': [],
            'priority_fee': [],
            'block_utilization': [],
            'pending_tx_count': [],
            'historical_success_rate': [],
            'time_features': []  # Hour of day, day of week, etc.
        }
        
        self.model = self._build_model()
        
    def _build_model(self):
        """Create gas price prediction model"""
        return Sequential([
            # Input shape based on feature count and sequence length
            LSTM(64, return_sequences=True, 
                 input_shape=(100, len(self.features))),
            Dropout(0.2),  # Prevent overfitting
            LSTM(32),
            Dense(3)  # Predict: [base_fee, priority_fee, confidence]
        ])
        
    async def predict_gas_price(self, current_state: Dict) -> Dict:
        """Predict optimal gas price"""
        return {
            'predicted_base_fee': float,
            'predicted_priority_fee': float,
            'confidence': float,
            'valid_duration': int  # How long prediction is valid
        }
```

## 2. Liquidity Analysis System

```python
class LiquidityLSTM:
    def __init__(self):
        self.features = {
            'pool_reserves': [],
            'swap_volumes': [],
            'price_impact': [],
            'concentration_metrics': [],
            'pool_utilization': [],
            'correlated_pools': []  # Other pools with same tokens
        }
        
        self.model = self._build_model()
        
    def _build_model(self):
        """Create liquidity prediction model"""
        return Sequential([
            LSTM(128, return_sequences=True, 
                 input_shape=(100, len(self.features))),
            Dropout(0.2),
            LSTM(64),
            Dense(4)  # Predict: [liquidity_score, volatility, direction, confidence]
        ])
        
    async def predict_liquidity(self, pool_data: Dict) -> Dict:
        """Predict liquidity conditions"""
        return {
            'liquidity_score': float,  # 0-1 score of liquidity health
            'volatility': float,       # Expected liquidity volatility
            'direction': int,          # -1 (decreasing), 0 (stable), 1 (increasing)
            'confidence': float        # Prediction confidence
        }
```

## 3. Combined Analysis System

```python
class TransactionViabilityAnalyzer:
    """Analyze combined predictions for transaction viability"""
    
    async def analyze_transaction(
        self,
        gas_prediction: Dict,
        liquidity_prediction: Dict,
        transaction_params: Dict
    ) -> Dict:
        """Determine optimal transaction parameters"""
        
        # Calculate optimal timing
        timing_score = self._calculate_timing_score(
            gas_prediction,
            liquidity_prediction
        )
        
        # Estimate success probability
        success_prob = self._estimate_success_probability(
            gas_prediction,
            liquidity_prediction,
            transaction_params
        )
        
        # Calculate optimal gas price
        optimal_gas = self._calculate_optimal_gas(
            gas_prediction,
            success_prob,
            transaction_params
        )
        
        return {
            'should_execute': bool,
            'optimal_timing': {
                'block_number': int,
                'max_delay': int,
                'confidence': float
            },
            'gas_params': {
                'base_fee': float,
                'priority_fee': float,
                'max_fee': float
            },
            'success_probability': float,
            'risk_factors': List[str]
        }
```

## 4. Data Collection System

```python
class DataCollector:
    """Collect and preprocess data for both models"""
    
    async def collect_gas_data(self) -> pd.DataFrame:
        """Collect gas-related data"""
        return await self._query_database("""
            SELECT 
                base_fee,
                priority_fee,
                block_utilization,
                pending_tx_count,
                success_rate,
                EXTRACT(HOUR FROM timestamp) as hour,
                EXTRACT(DOW FROM timestamp) as day_of_week
            FROM network_states
            ORDER BY timestamp DESC
            LIMIT 1000
        """)
        
    async def collect_liquidity_data(self, pool_address: str) -> pd.DataFrame:
        """Collect liquidity-related data"""
        return await self._query_database("""
            SELECT 
                token0_amount,
                token1_amount,
                total_value_locked,
                swap_volume_24h,
                price_impact,
                concentration_metric
            FROM pool_states
            WHERE pool_address = ?
            ORDER BY timestamp DESC
            LIMIT 1000
        """, pool_address)
```

## 5. Training System

```python
class ModelTrainer:
    """Train both models with historical data"""
    
    async def train_models(self):
        """Train both LSTM models"""
        
        # Train gas price model
        gas_data = await self.data_collector.collect_gas_data()
        gas_features = self._prepare_gas_features(gas_data)
        gas_labels = self._prepare_gas_labels(gas_data)
        
        self.gas_predictor.model.fit(
            gas_features,
            gas_labels,
            epochs=100,
            batch_size=32,
            validation_split=0.2,
            callbacks=[
                EarlyStopping(patience=10),
                ModelCheckpoint('gas_model.h5')
            ]
        )
        
        # Train liquidity model
        liquidity_data = await self.data_collector.collect_liquidity_data()
        liquidity_features = self._prepare_liquidity_features(liquidity_data)
        liquidity_labels = self._prepare_liquidity_labels(liquidity_data)
        
        self.liquidity_predictor.model.fit(
            liquidity_features,
            liquidity_labels,
            epochs=100,
            batch_size=32,
            validation_split=0.2,
            callbacks=[
                EarlyStopping(patience=10),
                ModelCheckpoint('liquidity_model.h5')
            ]
        )
```

## 6. Performance Monitoring

```python
class PerformanceMonitor:
    """Monitor prediction accuracy and system performance"""
    
    async def track_prediction(
        self,
        prediction: Dict,
        actual: Dict
    ):
        """Track prediction accuracy"""
        await self._save_metrics({
            'timestamp': datetime.now(),
            'gas_price_error': abs(
                prediction['gas_params']['base_fee'] - 
                actual['gas_params']['base_fee']
            ),
            'liquidity_prediction_accuracy': self._calculate_liquidity_accuracy(
                prediction['liquidity_score'],
                actual['liquidity_score']
            ),
            'success_prediction_accuracy': int(
                prediction['should_execute'] == 
                actual['was_successful']
            )
        })
        
    async def generate_report(self) -> Dict:
        """Generate performance report"""
        return {
            'gas_prediction_accuracy': float,
            'liquidity_prediction_accuracy': float,
            'combined_success_rate': float,
            'false_positives': int,
            'false_negatives': int,
            'average_prediction_time': float,
            'model_drift_indicators': Dict
        }
```

## Implementation Plan

### Phase 1: Data Collection (1 week)
1. Implement DataCollector
2. Set up database queries
3. Create data validation
4. Add data preprocessing

### Phase 2: Model Implementation (2 weeks)
1. Implement GasPriceLSTM
2. Implement LiquidityLSTM
3. Create TransactionViabilityAnalyzer
4. Add model validation

### Phase 3: Training System (1 week)
1. Implement ModelTrainer
2. Add data augmentation
3. Create validation system
4. Set up model persistence

### Phase 4: Monitoring (1 week)
1. Implement PerformanceMonitor
2. Add alerting system
3. Create performance dashboard
4. Set up automated retraining

Would you like to start implementing any particular component of this system?