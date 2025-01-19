# System Patterns and Architecture

## DEX Integration Framework

### Core Components

1. DEX Registry Pattern
   - Central management of DEX integrations via `DEXRegistry` class
   - Dynamic registration/unregistration of DEXes
   - Consistent interface for accessing DEX functionality
   - Located in: `arbitrage_bot/core/dex/dex_registry.py`

2. Base DEX Classes
   - `BaseDEX`: Common interface for all DEXes
   - `BaseV2DEX`: Specialized for V2-style DEXes (pair-based)
   - `BaseV3DEX`: Specialized for V3-style DEXes (concentrated liquidity)
   - Located in: `arbitrage_bot/core/dex/base_dex_*.py`

3. DEX Implementations
   - Each DEX inherits from appropriate base class
   - Consistent error handling and logging
   - Example implementations:
     - PancakeSwap V3: `arbitrage_bot/core/dex/implementations/pancakeswap_v3.py`
     - BaseSwap V2: `arbitrage_bot/core/dex/implementations/baseswap_v2.py`

### Integration Points

1. Market Analyzer Integration
   - Uses DEX registry for all DEX operations
   - Consistent quote handling across DEXes
   - Improved error handling and logging
   - File: `arbitrage_bot/core/analysis/market_analyzer.py`

2. Configuration
   - DEX-specific settings in config files
   - Required parameters:
     - V2: router, factory, fee_numerator
     - V3: quoter, factory, fee_tiers

### Adding New DEXes

1. Choose appropriate base class (V2 or V3)
2. Implement required methods:
   - get_quote
   - check_liquidity
   - Additional DEX-specific methods
3. Register with DEXRegistry in MarketAnalyzer initialization

### Error Handling

1. Consistent error patterns:
   - DEX-specific errors wrapped in QuoteResult
   - Detailed logging with context
   - Automatic error propagation to monitoring

2. Rate Limiting:
   - Per-DEX rate limiting
   - Exponential backoff
   - Automatic retry logic

### Monitoring and Metrics

1. Per-DEX metrics:
   - Quote success rate
   - Response times
   - Error rates
   - Liquidity levels

2. Aggregated metrics:
   - Cross-DEX price comparisons
   - Arbitrage opportunities
   - System health indicators

## Next Steps

1. Implement additional DEXes:
   - Aerodrome
   - SwapBased
   - RocketSwap

2. Enhance monitoring:
   - Add DEX-specific health checks
   - Implement automatic failover
   - Add performance benchmarking

3. Optimize gas usage:
   - Implement multicall for batch quotes
   - Add gas estimation per DEX
   - Optimize path encoding

## Implementation Guidelines

1. New DEX Integration:
```python
from ..base_dex_v2 import BaseV2DEX  # or base_dex_v3
from ..dex_registry import QuoteResult

class NewDEX(BaseV2DEX):
    def __init__(self, web3, config):
        super().__init__(web3, config)
        self.name = "new_dex"
        self.version = "v2"  # or "v3"
        
    async def get_quote(self, token_in, token_out, amount_in):
        try:
            # DEX-specific quote logic
            return QuoteResult(
                amount_out=quote,
                fee=fee,
                price_impact=impact,
                path=[token_in, token_out],
                success=True
            )
        except Exception as e:
            self.log_error(e, {
                "method": "get_quote",
                "token_in": token_in,
                "token_out": token_out
            })
            return QuoteResult(
                amount_out=0,
                fee=0,
                price_impact=0,
                path=[],
                success=False,
                error=str(e)
            )
```

2. Registration:
```python
# In MarketAnalyzer._initialize_dexes
from ..dex.implementations.new_dex import NewDEX

if dex_name == "new_dex":
    dex = NewDEX(self.w3, dex_config)
    self.dex_registry.register(dex)
```

## Testing Strategy

1. Unit Tests:
   - Test each DEX implementation independently
   - Mock Web3 responses
   - Verify error handling

2. Integration Tests:
   - Test DEX interactions with live networks
   - Verify quote accuracy
   - Test rate limiting

3. System Tests:
   - Test full arbitrage workflow
   - Verify monitoring and metrics
   - Test failover scenarios
