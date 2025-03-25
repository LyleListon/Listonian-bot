# Listonian Arbitrage Bot Startup Guide

## Prerequisites
1. Python 3.12+ installed
2. Git installed
3. Environment variables configured in secure/.env:
   - BASE_RPC_URL: Base network RPC URL
   - PRIVATE_KEY: Wallet private key
   - FLASHBOTS_AUTH_KEY: Flashbots authentication key

## Initial Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -e .
```

3. Initialize memory bank:
```bash
python init_memory_bank.py
```

4. Configure the bot:
   - Copy .env.production.template to secure/.env
   - Update secure/.env with your credentials
   - Review and update config.json settings

## Starting the Bot

### Windows Users
1. Using the combined launcher (recommended):
```bash
start_bot_with_dashboard.bat
```

This will:
- Start the arbitrage bot
- Launch the dashboard
- Open the dashboard in your browser
- Monitor both processes

2. Using PowerShell:
```powershell
.\start_bot_with_dashboard.ps1
```

### Manual Start
1. Start the bot:
```bash
python run_bot.py
```

2. Start the dashboard:
```bash
python run_dashboard.py
```

## Accessing the Dashboard
- URL: http://localhost:9050
- Real-time metrics and monitoring
- System resource tracking
- Performance analytics

## Monitoring
1. Log files:
   - logs/bot.err - Bot error logs
   - logs/dashboard.err - Dashboard error logs

2. Memory bank:
   - memory-bank/state/metrics.json - Current metrics
   - memory-bank/state/opportunities.json - Active opportunities

## Stopping the Bot
1. If using combined launcher:
   - Press Ctrl+C in respective terminals
   - Both bot and dashboard will shut down cleanly

2. If started manually:
   - Press Ctrl+C in each terminal
   - Wait for graceful shutdown

## Troubleshooting
1. Connection issues:
   - Verify BASE_RPC_URL is accessible
   - Check Flashbots authentication
   - Ensure wallet has sufficient funds

2. Dashboard issues:
   - Check port 9050 is available
   - Verify WebSocket connection
   - Review dashboard error logs

3. Bot issues:
   - Check bot error logs
   - Verify configuration
   - Review memory bank state

## Support Files
- DEPLOYMENT_CHECKLIST.md - Deployment steps
- FLASH_LOAN_GUIDE.md - Flash loan setup
- FLASHBOTS_INTEGRATION_GUIDE.md - Flashbots setup
- PROJECT_ARCHITECTURE.md - System architecture