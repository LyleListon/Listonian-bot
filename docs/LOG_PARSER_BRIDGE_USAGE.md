# Log Parser Bridge Usage Guide

## Overview

The Log Parser Bridge solves the data reporting issue by connecting the arbitrage system's log files to the dashboard's data stores. It watches for new log entries, parses them in real-time, and updates the OpportunityTracker that feeds data to the dashboard.

## Problem Solved

Previously, there was a disconnect in the data flow:
1. The arbitrage system wrote opportunities and executions to log files
2. The dashboard read from OpportunityTracker/GlobalCache
3. No component connected these two systems

The Log Parser Bridge closes this gap by:
- Watching log files for changes
- Parsing new entries in real-time
- Updating OpportunityTracker with parsed data
- Maintaining data consistency across the system

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure the configuration file exists at `configs/log_parser_config.yaml`:
```yaml
parser_bridge:
  watch_directory: "./logs"
  update_frequency: 1.0
  max_batch_size: 1000
  file_patterns:
    - "opportunities_*.log"
    - "execution_*.log"
  parser_rules:
    opportunity:
      pattern: "Found opportunity.*DEX: (.*) -> (.*), Token: (.*), Price diff: ([\\d.]+)%, Amount: ([\\d.]+) ETH, Expected profit: \\$([\\d.]+)"
      groups:
        - dex_from
        - dex_to
        - token
        - price_diff
        - amount
        - profit
    execution:
      pattern: "Trade execution.*Hash: (0x[a-fA-F0-9]+), Status: (\\w+), Profit: \\$([\\d.]+), Gas cost: \\$([\\d.]+)"
      groups:
        - tx_hash
        - status
        - profit
        - gas_cost
```

## Usage

### Starting the Bridge

1. Using the batch file:
```bash
start_log_parser.bat
```

2. Or manually:
```bash
python scripts/start_log_parser.py
```

### Monitoring

The Log Parser Bridge provides several monitoring points:

1. Console Output:
   - Startup information
   - Regular statistics updates
   - Error reporting

2. Log Files:
   - Located in `./logs/`
   - Contains detailed operation logs
   - Error tracking and debugging info

3. Dashboard Integration:
   - Real-time updates in dashboard
   - Opportunity tracking
   - Performance metrics

## Components

### 1. Log Parser Bridge
- Watches log files for changes
- Parses log entries using configured patterns
- Updates OpportunityTracker with parsed data
- Handles errors and retries gracefully

### 2. Configuration Loader
- Loads and validates configuration
- Supports flexible parser rules
- Handles environment-specific settings

### 3. OpportunityTracker
- Thread-safe storage of opportunities
- Maintains statistics and metrics
- Provides filtered data access
- Feeds dashboard with real-time data

## Troubleshooting

### Common Issues

1. No Data in Dashboard
   - Check log file permissions
   - Verify log file patterns match
   - Ensure parser rules are correct
   - Check log format matches patterns

2. Parser Not Starting
   - Verify Python environment
   - Check configuration file exists
   - Ensure required permissions
   - Verify log directory exists

3. Missing Opportunities
   - Check log file format
   - Verify parser patterns
   - Ensure log files are being written
   - Check update frequency setting

### Debugging

1. Enable Debug Logging:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. Check Log Files:
   - Parser logs: `logs/log_parser_*.log`
   - System logs: `logs/system_*.log`
   - Error logs: `logs/error_*.log`

3. Monitor File System:
   - Watch log directory for changes
   - Verify file permissions
   - Check file system events

## Best Practices

1. Configuration
   - Keep patterns up to date
   - Adjust update frequency as needed
   - Monitor resource usage
   - Tune batch sizes appropriately

2. Monitoring
   - Watch error rates
   - Monitor parsing performance
   - Track memory usage
   - Check processing delays

3. Maintenance
   - Rotate log files regularly
   - Clean up old logs
   - Update parser rules as needed
   - Monitor disk space usage

## Performance Considerations

1. Update Frequency
   - Default: 1 second
   - Adjust based on load
   - Balance latency vs. resources

2. Batch Processing
   - Default batch size: 1000
   - Adjust for memory usage
   - Consider log volume

3. Resource Usage
   - Monitor CPU usage
   - Track memory consumption
   - Watch disk I/O
   - Consider network impact

## Security Notes

1. File Access
   - Minimal permissions needed
   - Read-only access to logs
   - Secure log directory

2. Data Handling
   - Validate all parsed data
   - Sanitize log contents
   - Handle sensitive information

3. Error Handling
   - Fail securely
   - Log security events
   - Handle malformed data

## Future Enhancements

1. Planned Features
   - Real-time metrics export
   - Advanced parsing rules
   - Custom transformers
   - Performance analytics

2. Potential Improvements
   - Parallel processing
   - Machine learning integration
   - Advanced monitoring
   - Custom alerting

## Support

For issues or questions:
1. Check the troubleshooting guide
2. Review error logs
3. Check configuration
4. Contact development team