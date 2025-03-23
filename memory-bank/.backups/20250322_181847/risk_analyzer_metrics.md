# Risk Analyzer Empirical Metrics Guide

## Overview
The Risk Analyzer now tracks comprehensive empirical metrics to measure its effectiveness in protecting against MEV attacks and optimizing gas usage.

## Key Metrics Categories

### 1. Detection Accuracy
- **True Positives**: Correctly identified attacks
- **False Positives**: Incorrectly flagged transactions
- **True Negatives**: Correctly identified safe transactions
- **False Negatives**: Missed attacks
- **Overall Accuracy**: (TP + TN) / Total
- **Precision**: TP / (TP + FP)

### 2. Gas Savings
- **Total Gas Saved**: Cumulative gas saved from MEV protection
- **Average Per Transaction**: Gas saved per protected transaction
- **Highest Single Save**: Largest gas saving from a single intervention
- **Monthly Trends**: Gas savings tracked by month

### 3. Profit Protection
- **Protected Value (USD)**: Total value protected from MEV attacks
- **Prevented Losses (USD)**: Estimated losses prevented
- **Successful Interventions**: Number of successful protections
- **Monthly Protection**: Value protected tracked by month

### 4. Performance Timing
- **Analyze Mempool**: Time spent analyzing mempool
- **Detect Attacks**: Time spent on attack detection
- **Pattern Analysis**: Time spent analyzing transaction patterns

### 5. Attack Patterns
- Distribution of different attack types
- Pattern frequency analysis
- Confidence score distribution
- Risk level distribution

### 6. Block Coverage
- **Total Blocks Analyzed**: Number of blocks scanned
- **Blocks with Attacks**: Number of blocks containing attacks
- **Coverage Percentage**: Percentage of chain analyzed

## Accessing Metrics

```python
# Get comprehensive metrics report
metrics = await risk_analyzer.get_effectiveness_metrics()

# Example metrics output:
{
    'accuracy_metrics': {
        'overall_accuracy': '95.5%',
        'precision': '92.3%',
        'detection_breakdown': {...}
    },
    'gas_metrics': {
        'total_gas_saved': 1500000,
        'average_gas_saved': 75000,
        'highest_single_save': 150000,
        'monthly_trend': {...}
    },
    'profit_metrics': {
        'protected_value_usd': '$500,000.00',
        'prevented_losses_usd': '$25,000.00',
        'successful_interventions': 20,
        'monthly_trend': {...}
    },
    'performance_metrics': {
        'analyze_mempool': '0.125s',
        'detect_attacks': '0.085s',
        'pattern_analysis': '0.045s'
    },
    'pattern_analysis': {...},
    'confidence_distribution': {...},
    'block_coverage': {...},
    'risk_level_distribution': {...}
}
```

## Interpreting Results

### Accuracy Thresholds
- **Excellent**: > 95% accuracy, > 90% precision
- **Good**: > 85% accuracy, > 80% precision
- **Needs Improvement**: < 85% accuracy or < 80% precision

### Performance Targets
- **Mempool Analysis**: < 0.2s
- **Attack Detection**: < 0.1s
- **Pattern Analysis**: < 0.05s

### Gas Savings Goals
- **Minimum**: 50,000 gas per intervention
- **Target**: > 100,000 gas per intervention
- **Excellent**: > 200,000 gas per intervention

## Using Metrics for Optimization

1. **Monitor Accuracy Trends**
   - Track false positive rate
   - Adjust confidence thresholds if needed
   - Fine-tune pattern detection

2. **Optimize Gas Savings**
   - Identify most effective intervention types
   - Focus on high-impact protection strategies
   - Adjust gas price thresholds

3. **Improve Performance**
   - Monitor execution times
   - Optimize slow operations
   - Consider caching strategies

4. **Pattern Analysis**
   - Identify emerging attack patterns
   - Update detection strategies
   - Adjust risk parameters

## Regular Review Process

1. **Daily Monitoring**
   - Check accuracy metrics
   - Review gas savings
   - Monitor performance times

2. **Weekly Analysis**
   - Review pattern distributions
   - Analyze false positives
   - Assess optimization opportunities

3. **Monthly Review**
   - Compare monthly trends
   - Evaluate strategy effectiveness
   - Update thresholds if needed

## Integration with Dashboard

The metrics are designed to integrate with the monitoring dashboard, providing:
- Real-time accuracy tracking
- Gas savings visualization
- Performance monitoring
- Attack pattern analysis
- Trend visualization

## Future Enhancements

1. **Machine Learning Integration**
   - Pattern recognition improvement
   - Predictive analytics
   - Automated threshold adjustment

2. **Advanced Analytics**
   - Cross-chain correlation
   - Market impact analysis
   - Profit optimization modeling