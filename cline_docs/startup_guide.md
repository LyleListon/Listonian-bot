# Startup Guide
Last Updated: February 23, 2025 06:17 EST

## Prerequisites
1. Python 3.12 or higher (required for improved async support)
2. Node.js 14 or higher
3. Git
4. PowerShell 7.0+ (Windows) or Bash (Linux/Mac)
5. Minimum System Requirements:
   - RAM: 8GB minimum, 16GB recommended (for async operations)
   - CPU: 4 cores minimum, 8 cores recommended (for concurrent processing)
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

### 3. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install

# Initialize memory system
python init_memory.py
```

## System Requirements

### 1. Async Support
- Python 3.12+ required for improved async features
- Proper async/await implementation
- Thread safety mechanisms
- Resource management
- Error handling patterns

### 2. Thread Safety
- Lock management for shared resources
- Concurrent access control
- State consistency protection
- Resource protection
- Atomic operations

### 3. Resource Management
- Async resource initialization
- Proper cleanup procedures
- Resource monitoring
- Error recovery
- Performance tracking

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
   - Verifies Python installation (3.12+ required)
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

2. Configures async environment:
   - Initializes asyncio event loop
   - Sets up thread safety mechanisms
   - Configures resource management
   - Enables proper error handling

3. Verifies async setup:
   - Checks event loop
   - Validates thread safety
   - Confirms resource management
   - Tests error handling

4. Configures logging:
   - Sets INFO level logging
   - Uses timestamp format
   - Creates dashboard logger

Expected Output:
```
Starting dashboard with async support...
INFO - Event loop initialized
INFO - Thread safety enabled
INFO - Resource management active
INFO - Error handling configured
Running dashboard...
```

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

3. Initializes async environment:
   - Sets up event loop
   - Configures thread safety
   - Initializes resource management
   - Enables error handling

4. Starts processes:
   - Main bot process (production.py)
   - Dashboard process (arbitrage_bot.dashboard.run)

## System Verification

### 1. Async Implementation
- Event loop running properly
- Thread safety mechanisms active
- Resource management working
- Error handling functioning
- Performance monitoring active

### 2. Thread Safety
- Lock management working
- Resource protection active
- Data consistency maintained
- Concurrent access controlled
- State consistency protected

### 3. Resource Management
- Initialization successful
- Cleanup procedures working
- Resource monitoring active
- Error recovery functioning
- Performance tracking enabled

## Troubleshooting

### 1. Async Issues
- Event loop not starting:
  * Check Python version (3.12+ required)
  * Verify async implementation
  * Check resource availability
  * Monitor thread safety
  * Review error logs

### 2. Thread Safety Issues
- Lock contention:
  * Monitor lock usage
  * Check deadlock prevention
  * Verify resource sharing
  * Review concurrent access
  * Check state consistency

### 3. Resource Management Issues
- Resource leaks:
  * Monitor cleanup procedures
  * Check initialization
  * Verify error recovery
  * Track resource usage
  * Review performance metrics

Remember: 
- Always maintain sufficient ETH for gas fees
- Regular system maintenance is crucial
- Monitor system resources
- Keep security measures updated
- Document all changes
- Check async implementation
- Verify thread safety
- Monitor resource usage
