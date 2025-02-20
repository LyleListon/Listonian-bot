# Startup Guide
Last Updated: February 20, 2025 02:19 EST

## Prerequisites
1. Python 3.8 or higher
2. Node.js 14 or higher
3. Git
4. PowerShell 7.0+ (Windows) or Bash (Linux/Mac)
5. Minimum System Requirements:
   - RAM: 4GB minimum, 8GB recommended
   - CPU: 2 cores minimum, 4 cores recommended
   - Storage: 10GB free space
   - Network: Stable internet connection, minimum 10Mbps
   - Ports: 5000 (Dashboard), 8545 (RPC)

## Initial Setup

### 1. Environment Setup
1. Clone the repository
2. Copy .env.production.template to .env.production
3. Fill in your environment variables in .env.production:
   - BASE_RPC_URL (Your Base network RPC URL)
   - WALLET_ADDRESS (Your trading wallet address)
   - PRIVATE_KEY (Your wallet's private key)
   - ALCHEMY_API_KEY (Your Alchemy API key)
   - PROFIT_RECIPIENT (Address to receive profits)

### 2. Initialize Secure Environment
```bash
python init_secure.py
```
This step is CRITICAL. It:
- Encrypts sensitive values from .env.production
- Enables $SECURE: references in config files
- Must be run before starting any system components
- Creates necessary secure storage

Required Files Before Running:
1. .env.production (copied from .env.production.template) containing:
   - WALLET_ADDRESS
   - PRIVATE_KEY
   - PROFIT_RECIPIENT
   - ALCHEMY_API_KEY

2. configs/config.json with network settings
3. configs/wallet_config.json with wallet settings

Expected Output:
1. Initialization messages:
   ```
   Storing credentials:
   Wallet Address: 0x...
   Private Key: 0x...
   Profit Recipient: 0x...
   
   Securing sensitive data...
   
   Verifying stored values:
   Stored Wallet Address: 0x...
   Stored Private Key: 0x...
   Stored Profit Recipient: 0x...
   
   ✅ Secure environment initialized successfully!
   ```

2. File Changes:
   - secure/ directory created
   - configs/wallet_config.json updated with $SECURE: references
   - configs/wallet_config.json.bak created as backup
   - configs/config.json updated with $SECURE: references

Verification Steps:
1. Check secure/ directory exists
2. Verify success message displayed
3. Confirm config files updated:
   - config.json should show $SECURE: references
   - wallet_config.json should show $SECURE: references
4. Verify backup file exists:
   - configs/wallet_config.json.bak should contain original values

Common Error Messages:
- "Missing .env.production": Copy template and fill values
- "Missing config.json": Ensure config file exists
- "Missing wallet_config.json": Create wallet config
- Invalid wallet address format: Check address format
- Invalid private key format: Ensure key format correct

### 3. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install

# Initialize memory system
python init_memory.py
```

## Starting the System

### 1. All-in-One Startup (Recommended)
```bash
# Windows
./start_all.ps1

# Linux/Mac
./start_all.sh
```

The startup script performs these steps automatically:

1. Environment Setup:
   - Creates required directories (logs, data/memory, data/storage)
   - Sets DASHBOARD_PORT to 5000
   - Configures PYTHONPATH
   - Loads environment variables from .env.production

2. Dependency Checks:
   - Verifies Python installation (3.8+ required)
   - Installs required packages from requirements.txt
   - Validates config file presence
   - Checks secure environment initialization

3. Cleanup Operations:
   - Stops any existing Python processes
   - Clears port 5000 if in use
   - Creates fresh log files with timestamps

4. Component Startup:
   - Starts main arbitrage bot
   - Waits 10 seconds for initialization
   - Launches dashboard interface
   - Waits 5 seconds for dashboard startup

Expected Output:
```
Starting Listonian Arbitrage Bot Setup...
Checking dependencies...
Checking secure environment...
Loading environment variables...
Cleaning up any existing Python processes...
Creating required directories...
Starting main arbitrage bot...
Waiting for bot initialization...
Starting minimal dashboard...

===============================
Listonian Arbitrage Bot Status
===============================

Main Bot: Running (providing live data)

Dashboard: Running (visualizing data)

Monitor the logs directory for detailed output:
- logs/bot_YYYYMMDD_HHMMSS.log (main bot logs)
- logs/dashboard_YYYYMMDD_HHMMSS.log (dashboard logs)

Access dashboard at: http://localhost:5000

Press Ctrl+C to stop all processes.
```

Log Files Created:
- logs/bot_[timestamp].error.log
- logs/dashboard_[timestamp].error.log

Required Directories:
- logs/
- data/memory/
- data/storage/
- minimal_dashboard/static/
- minimal_dashboard/templates/

### 2. Individual Component Start (Advanced)
Only use this method if you need to run components separately for debugging.

#### Dashboard:
```bash
./start_dashboard.ps1  # Windows
./start_dashboard.sh   # Linux/Mac
```

The dashboard startup:
1. Sets up environment variables:
   - PYTHONPATH=.
   - PYTHONASYNCIODEBUG=1
   - PYTHONUNBUFFERED=1

2. Performs eventlet patching:
   - Patches socket operations
   - Patches threading
   - Patches time functions

3. Verifies patching success:
   - Checks socket patching
   - Validates threading patches
   - Confirms time function patches

4. Configures logging:
   - Sets INFO level logging
   - Uses timestamp format
   - Creates dashboard logger

Expected Output:
```
Starting dashboard with eventlet patching...
INFO - Socket patched: True
INFO - Threading patched: True
INFO - Time patched: True
INFO - Eventlet patching verified
Running dashboard...
```

Common Dashboard Issues:
- "Failed to verify eventlet patching": Restart with clean Python environment
- "Address already in use": Check for running dashboard instances
- "Import error: eventlet": Install missing dependencies
- "Permission denied": Check file access rights
- "Logging initialization failed": Verify logs directory permissions

#### Bot:
```bash
./start_bot.ps1  # Windows
./start_bot.sh   # Linux/Mac
```

The bot startup:
1. Creates timestamped log files:
   - logs/bot_[timestamp].log (output)
   - logs/bot_[timestamp].err (errors)
   - logs/dashboard_[timestamp].log (output)
   - logs/dashboard_[timestamp].err (errors)

2. Validates required files:
   - .env.production
   - configs/production_config.json
   - production.py
   - arbitrage_bot/dashboard/run.py

3. Loads environment variables from .env.production

4. Starts processes:
   - Main bot process (production.py)
   - Dashboard process (arbitrage_bot.dashboard.run)

Expected Output:
```
Starting Arbitrage Bot and Dashboard in LIVE MODE...
Starting bot process...
Starting dashboard process...
Bot and dashboard started in LIVE MODE.
Bot logs:
  Output: logs/bot_YYYYMMDD_HHMMSS.log
  Errors: logs/bot_YYYYMMDD_HHMMSS.err
Dashboard logs:
  Output: logs/dashboard_YYYYMMDD_HHMMSS.log
  Errors: logs/dashboard_YYYYMMDD_HHMMSS.err
```

Common Bot Issues:
- "Python 3.8 or higher is required": Update Python installation
- ".env.production file not found": Copy template and configure
- "production_config.json not found": Check configs directory
- "Required file not found": Verify all component files present
- Process termination: Check log files for errors

Common Startup Issues:
1. Port 5000 in use:
   - Script will attempt to free the port
   - If unsuccessful, manually check running processes
   - Use `netstat -ano | findstr :5000` to identify process

2. Python Process Conflicts:
   - Script automatically stops existing Python processes
   - If issues persist, manually end processes
   - Use Task Manager or `taskkill /F /IM python.exe`

3. Directory Permission Issues:
   - Ensure write access to logs/ directory
   - Check permissions on data/ directories
   - Verify minimal_dashboard/ access

4. Environment Variable Problems:
   - Verify .env.production loaded correctly
   - Check PYTHONPATH setting
   - Confirm DASHBOARD_PORT availability

## Dashboard Access
1. Main interface: http://localhost:5000
2. Features:
   - Real-time market opportunities
   - Gas price monitoring
   - Monthly gas usage statistics
   - Transfer tracking
   - Memory statistics
   - Trade history

## System Verification

### 1. Dashboard Verification
- Dashboard accessible at http://localhost:5000
- WebSocket connection established (check browser console)
- Gas prices updating
- Market opportunities visible
- Memory stats showing

### 2. Log Verification
Check these log files for proper operation:
```
logs/
├── bot.log (Main bot operations)
├── dashboard.log (Dashboard activity)
├── monitoring/
│   ├── monitoring_[timestamp].json (Periodic monitoring data)
│   ├── competitor_patterns.json (Detected trading patterns)
│   ├── block_reorgs.json (Chain reorganization events)
│   └── metrics.json (System performance metrics)
├── gas/
│   ├── YYYYMM.json (Monthly gas stats)
│   └── current.log (Real-time tracking)
├── gas_usage.log (Gas tracking)
├── memory.log (Memory operations)
└── monitoring.log (System monitoring)
```

### 3. System Monitoring
The system tracks:
- Gas costs per transaction
- Monthly usage statistics
- Transfer patterns
- Network congestion
- Block reorganizations
- Competitor trading patterns
- System performance metrics
- Price trends
- Memory usage
- Transaction success rates
- Execution times

Monitoring Features:
1. Transaction Analysis
   - Real-time mempool monitoring
   - Transaction pattern detection
   - Gas price optimization
   - Success rate tracking

2. Competitor Tracking
   - Trading pattern analysis
   - Performance metrics
   - Success rate monitoring
   - Gas usage patterns

3. Network Monitoring
   - Block reorganization detection
   - Chain stability metrics
   - Network congestion analysis
   - Gas price trends

4. System Health
   - Memory usage tracking
   - Cache efficiency
   - Process performance
   - Resource utilization

## Troubleshooting

### 1. Common Issues
- Dashboard not starting:
  * Verify init_secure.py was run
  * Check port 5000 is available
  * Verify WebSocket ports open
  * Check system resources
  * Verify network connectivity
- Bot not connecting:
  * Check RPC URL is valid
  * Verify wallet has funds
  * Check gas settings in config
  * Test network connectivity
  * Verify API key validity
- Gas tracking issues:
  * Verify logs/gas directory exists
  * Check write permissions
  * Validate gas configuration
  * Monitor disk space
  * Check log rotation settings

### 2. Configuration Verification
- Check .env.production has all required values
- Verify config.json uses $SECURE: references
- Validate gas settings in config.json
- Check memory configuration
- Verify profit recipient address

Configuration Backup:
1. Regular backups of config files
2. Secure storage of encryption keys
3. Version control of configurations
4. Documentation of changes

### 3. Log Analysis
Key log locations:
```
logs/
├── bot.log (Main operations)
├── dashboard.log (UI activity)
├── gas/
│   ├── YYYYMM.json (Monthly gas stats)
│   └── current.log (Real-time tracking)
├── memory.log (Memory operations)
└── monitoring.log (System status)
```

Log Rotation:
- Logs rotated daily
- Compressed after 7 days
- Archived after 30 days
- Deleted after 90 days

## Security Notes

### 1. Sensitive Data
- Never commit .env.production
- Always use $SECURE: references
- Keep private keys secure
- Regularly rotate API keys
- Use strong encryption
- Monitor access logs
- Regular security audits

### 2. Wallet Security
- Use dedicated trading wallet
- Maintain minimum required balance
- Monitor gas reserves
- Keep emergency ETH buffer
- Regular balance checks
- Transaction monitoring
- Alert system setup

## Maintenance

### 1. Regular Tasks
- Monitor gas usage patterns
- Review profit distribution
- Check log rotations
- Verify memory cleanup
- Update dependencies
- Security audits
- Performance monitoring

### 2. Updates
- Check for new releases
- Update dependencies
- Backup configurations
- Test after updates
- Document changes
- Monitor performance
- Verify security

### 3. Backup Procedures
- Daily configuration backups
- Weekly state snapshots
- Monthly system backups
- Secure key storage
- Recovery testing
- Documentation updates

## Support
- Check logs/ directory for detailed error messages
- Review documentation in docs/
- Monitor system metrics
- Track gas usage patterns
- Performance monitoring
- Resource utilization
- Network connectivity

Remember: 
- Always maintain sufficient ETH for gas fees
- Regular system maintenance is crucial
- Monitor system resources
- Keep security measures updated
- Document all changes
