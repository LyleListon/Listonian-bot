# ML System Database Schema

## Current Limitations
1. Simple key-value storage in JSON
2. Limited query capabilities
3. No time-series optimization
4. Basic metrics storage

## Enhanced Schema Design

### 1. Market Data Tables

```sql
-- Price data with high temporal granularity
CREATE TABLE price_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_symbol TEXT NOT NULL,
    dex_name TEXT NOT NULL,
    price DECIMAL(18,8) NOT NULL,
    timestamp DATETIME NOT NULL,
    volume_1h DECIMAL(18,8),
    volume_24h DECIMAL(18,8),
    liquidity DECIMAL(18,8),
    price_change_1h DECIMAL(18,8),
    price_change_24h DECIMAL(18,8),
    
    -- Indexes for efficient querying
    INDEX idx_price_time (timestamp),
    INDEX idx_price_token (token_symbol),
    INDEX idx_price_dex (dex_name)
);

-- Liquidity pool states
CREATE TABLE pool_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pool_address TEXT NOT NULL,
    dex_name TEXT NOT NULL,
    token0_symbol TEXT NOT NULL,
    token1_symbol TEXT NOT NULL,
    token0_amount DECIMAL(18,8) NOT NULL,
    token1_amount DECIMAL(18,8) NOT NULL,
    timestamp DATETIME NOT NULL,
    total_value_locked DECIMAL(18,8),
    fee_tier INTEGER,
    
    INDEX idx_pool_time (timestamp),
    INDEX idx_pool_address (pool_address)
);

-- Order book snapshots
CREATE TABLE orderbook_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dex_name TEXT NOT NULL,
    token_pair TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    bids TEXT NOT NULL,  -- JSON array of price/amount pairs
    asks TEXT NOT NULL,  -- JSON array of price/amount pairs
    spread DECIMAL(18,8),
    depth_50bps DECIMAL(18,8),
    depth_100bps DECIMAL(18,8),
    
    INDEX idx_orderbook_time (timestamp),
    INDEX idx_orderbook_pair (token_pair)
);
```

### 2. Blockchain Data Tables

```sql
-- Network state tracking
CREATE TABLE network_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    block_number INTEGER NOT NULL,
    gas_price DECIMAL(18,8) NOT NULL,
    base_fee DECIMAL(18,8),
    priority_fee DECIMAL(18,8),
    block_utilization DECIMAL(5,2),
    transaction_count INTEGER,
    
    INDEX idx_network_time (timestamp),
    INDEX idx_network_block (block_number)
);

-- Mempool monitoring
CREATE TABLE mempool_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    pending_count INTEGER NOT NULL,
    pending_value DECIMAL(18,8),
    gas_price_distribution TEXT,  -- JSON histogram
    transaction_types TEXT,  -- JSON count by type
    
    INDEX idx_mempool_time (timestamp)
);
```

### 3. Trading Activity Tables

```sql
-- Arbitrage opportunities
CREATE TABLE arbitrage_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    token_pair TEXT NOT NULL,
    dex_from TEXT NOT NULL,
    dex_to TEXT NOT NULL,
    profit_usd DECIMAL(18,8) NOT NULL,
    amount_in DECIMAL(18,8) NOT NULL,
    amount_out DECIMAL(18,8) NOT NULL,
    gas_estimate INTEGER,
    execution_success BOOLEAN,
    failure_reason TEXT,
    
    INDEX idx_arb_time (timestamp),
    INDEX idx_arb_pair (token_pair)
);

-- Market patterns
CREATE TABLE market_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    pattern_type TEXT NOT NULL,
    token_pair TEXT NOT NULL,
    confidence DECIMAL(5,2) NOT NULL,
    duration_seconds INTEGER,
    price_impact DECIMAL(18,8),
    volume_profile TEXT,  -- JSON time series
    
    INDEX idx_pattern_time (timestamp),
    INDEX idx_pattern_pair (token_pair)
);
```

### 4. ML Feature Tables

```sql
-- Preprocessed features
CREATE TABLE ml_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    feature_set TEXT NOT NULL,  -- e.g., 'market', 'network', 'combined'
    features TEXT NOT NULL,  -- JSON feature vector
    feature_version INTEGER NOT NULL,
    
    INDEX idx_features_time (timestamp),
    INDEX idx_features_set (feature_set)
);

-- Model predictions
CREATE TABLE model_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    input_features TEXT NOT NULL,  -- JSON feature vector
    prediction TEXT NOT NULL,  -- JSON prediction output
    confidence DECIMAL(5,2),
    actual_outcome TEXT,  -- JSON actual result
    
    INDEX idx_pred_time (timestamp),
    INDEX idx_pred_model (model_name, model_version)
);
```

### 5. Performance Tracking Tables

```sql
-- Model performance metrics
CREATE TABLE model_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DECIMAL(18,8) NOT NULL,
    window_size TEXT NOT NULL,  -- e.g., '1h', '24h', '7d'
    
    INDEX idx_perf_time (timestamp),
    INDEX idx_perf_model (model_name, model_version)
);

-- System performance tracking
CREATE TABLE system_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    component_name TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DECIMAL(18,8) NOT NULL,
    additional_data TEXT,  -- JSON extra information
    
    INDEX idx_sys_time (timestamp),
    INDEX idx_sys_component (component_name)
);
```

## Implementation Strategy

### Phase 1: Core Tables (1 week)
1. Implement price_data and pool_states
2. Add network_states
3. Create arbitrage_opportunities
4. Set up basic indexes

### Phase 2: Advanced Tables (1 week)
1. Add orderbook_states
2. Implement mempool_states
3. Create market_patterns
4. Set up feature tables

### Phase 3: ML Support (1 week)
1. Add ml_features
2. Implement model_predictions
3. Create performance tables
4. Set up monitoring

### Phase 4: Optimization (1 week)
1. Optimize indexes
2. Add partitioning
3. Implement archiving
4. Set up backups

## Migration Plan

1. Data Migration
```python
async def migrate_existing_data():
    """Migrate existing data to new schema"""
    old_trades = await db.get_trades({})
    old_metrics = await db.get_metrics()
    
    # Migrate trades to new tables
    for trade in old_trades:
        await migrate_trade(trade)
        
    # Migrate metrics to new tables
    for metric in old_metrics:
        await migrate_metric(metric)
```

2. Code Updates
```python
class EnhancedDatabase(Database):
    """Enhanced database with new schema support"""
    
    async def initialize_schema(self):
        """Create new schema tables"""
        
    async def migrate_data(self):
        """Migrate existing data"""
        
    async def validate_migration(self):
        """Verify migration success"""
```

Would you like to start implementing any particular part of this schema?