@echo off
echo Starting Arbitrage Monitoring Dashboard...
echo Dashboard will be available at http://localhost:8080

REM Create directory if it doesn't exist
if not exist "monitoring_data" mkdir "monitoring_data"

REM Launch the monitoring dashboard
python -m dashboard.arbitrage_monitor

echo Press Ctrl+C to stop the dashboard