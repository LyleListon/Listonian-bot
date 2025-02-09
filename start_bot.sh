#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Set log files with timestamp
timestamp=$(date +%Y%m%d_%H%M%S)
bot_log_out="logs/bot_${timestamp}.log"
bot_log_err="logs/bot_${timestamp}.err"
dashboard_log_out="logs/dashboard_${timestamp}.log"
dashboard_log_err="logs/dashboard_${timestamp}.err"

echo "Starting Arbitrage Bot and Dashboard in LIVE MODE..."

# Check Python installation
if ! command -v python &> /dev/null; then
    echo "Error: Python 3.8 or higher is required"
    exit 1
fi

# Check required files
if [ ! -f ".env.production" ]; then
    echo "Error: .env.production file not found"
    echo "Please copy .env.production.template and fill in your settings"
    exit 1
fi

if [ ! -f "configs/production_config.json" ]; then
    echo "Error: configs/production_config.json not found"
    exit 1
fi

# Load environment variables
export $(cat .env.production | grep -v '^#' | xargs)

# Set dashboard ports
export DASHBOARD_PORT=5000
export DASHBOARD_WEBSOCKET_PORT=8771

# Configure port forwarding for Codespace
if [ -n "$CODESPACE_NAME" ]; then
    echo "Running in Codespace environment"
    echo "Dashboard will be available at: https://$CODESPACE_NAME-5000.app.github.dev"
    echo "WebSocket will be available at: wss://$CODESPACE_NAME-8771.app.github.dev"
fi

# Start bot process
echo "Starting bot process..."
python production.py > "$bot_log_out" 2> "$bot_log_err" &
bot_pid=$!

# Start dashboard process
echo "Starting dashboard process..."
python -m arbitrage_bot.dashboard.run > "$dashboard_log_out" 2> "$dashboard_log_err" &
dashboard_pid=$!

echo "Bot and dashboard started in LIVE MODE."
echo "Bot logs:"
echo "  Output: $bot_log_out"
echo "  Errors: $bot_log_err"
echo "Dashboard logs:"
echo "  Output: $dashboard_log_out"
echo "  Errors: $dashboard_log_err"

# Function to tail logs
tail_logs() {
    tail -f "$bot_log_out" "$bot_log_err" "$dashboard_log_out" "$dashboard_log_err" &
    tail_pid=$!
}

# Start tailing logs
tail_logs

# Handle shutdown
cleanup() {
    echo "Stopping processes..."
    kill $bot_pid $dashboard_pid $tail_pid 2>/dev/null
    echo "Shutdown complete"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for processes
wait $bot_pid $dashboard_pid