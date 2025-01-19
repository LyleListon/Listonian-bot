# Quick Start Guide: Arbitrage Bot & Dashboard

## 1. Environment Setup

```bash
# Create and activate Python environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
npm install
```

## 2. Configuration

1. Environment files are already set up:
   - .env: Main configuration
   - .env.sepolia: Sepolia testnet configuration

2. Verify config.yaml has minimum settings:
```yaml
network:
  rpc_url: "${RPC_URL}"
  chain_id: 11155111  # Sepolia

trading:
  min_profit_threshold: 0.5
  max_trade_size: "1"
  gas_price_limit: "100"

monitoring:
  log_level: "INFO"
  dashboard_port: 5000
```

## 3. Starting Services

1. Start Dashboard (Terminal 1):
```bash
.\venv\Scripts\activate
cd dashboard
python app.py
```

2. Access Dashboard:
   - Open http://127.0.0.1:5000 in your browser
   - Verify connection status
   - Check price feed updates

## 4. Verification

1. Dashboard:
   - Check console for successful startup
   - Verify database initialization
   - Monitor WebSocket connections
   - Check system metrics display

2. Common Checks:
   - Network connectivity
   - Database status
   - Price feed updates
   - System resource usage

## 5. Common Issues

1. Port Issues:
   - If port 5000 is in use:
     ```bash
     # Find and kill process using port 5000
     netstat -ano | findstr :5000
     taskkill /PID <process_id> /F
     ```

2. Database Issues:
   - Database will auto-initialize on first run
   - Check arbitrage_bot.db file creation
   - Monitor logs for SQL errors

3. Connection Issues:
   - Verify RPC URL in .env
   - Check network connectivity
   - Monitor WebSocket status

## 6. Monitoring

- Dashboard logs: Check terminal output
- System metrics: Available in dashboard UI
- Database: arbitrage_bot.db
- Process ID: dashboard.pid

## Important Notes

1. The dashboard runs on http://127.0.0.1:5000
2. Keep terminal running for live updates
3. Monitor system resources
4. Check WebSocket connections
5. Review trade history in dashboard

## Troubleshooting

If you encounter issues:
1. Check terminal output for errors
2. Verify environment variables
3. Monitor database connections
4. Review network connectivity
5. Check system resources
