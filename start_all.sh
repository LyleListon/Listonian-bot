#!/bin/bash

echo "Starting Listonian Arbitrage Bot Setup..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Set timestamp for log files
timestamp=$(date +%Y%m%d_%H%M%S)

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "Error: Python not found. Please install Python 3.8 or higher."
    exit 1
fi

# Create and activate virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
. venv/bin/activate

# Install dependencies with minimal output
echo "Installing dependencies..."
pip install -r requirements.txt web3 eth-tester --quiet 2>/dev/null

if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies. Check logs for details."
    exit 1
fi

# Add current directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Check config files
if [ ! -f configs/config.json ]; then
    echo "Error: config.json not found. Please create configs/config.json with your settings."
    exit 1
fi

if [ ! -f configs/wallet_config.json ]; then
    echo "Error: wallet_config.json not found. Please create configs/wallet_config.json with your wallet settings."
    exit 1
fi

# Load environment variables
if [ -f .env.production ]; then
    echo "Loading environment variables..."
    export $(cat .env.production | xargs)
    
    # Verify critical environment variables
    if [ -z "$PRIVATE_KEY" ] || [ -z "$BASE_RPC_URL" ]; then
        echo "Error: Missing required environment variables"
        exit 1
    fi
    
    echo "Environment variables loaded successfully"
else
    echo "Error: .env.production not found"
    exit 1
fi

# Set Python logging level to reduce output
export PYTHONWARNINGS=ignore
export PYTHONUNBUFFERED=1

# Initialize memory bank first
echo "Initializing memory bank..."
python init_memory.py

if [ $? -ne 0 ]; then
    echo "Error: Failed to initialize memory bank"
    exit 1
fi

# Start main bot with mainnet configuration
echo "Starting arbitrage bot..."
python main.py > "logs/bot_${timestamp}.log" 2> "logs/bot_${timestamp}.err" &
bot_pid=$!

# Wait for bot to initialize (increased wait time)
echo "Waiting for bot initialization..."
sleep 10

# Check if bot is still running
if ! kill -0 $bot_pid 2>/dev/null; then
    echo "Error: Bot failed to start. Check logs/bot_${timestamp}.err for details."
    exit 1
fi

# Set dashboard port to match devcontainer.json port forwarding
export DASHBOARD_PORT=5000

# Start dashboard after bot is initialized
echo "Starting dashboard on port ${DASHBOARD_PORT}..."
python start_dashboard.py > "logs/dashboard_${timestamp}.log" 2> "logs/dashboard_${timestamp}.err" &
dashboard_pid=$!

# Wait for dashboard to initialize
sleep 5

# Display status
echo
echo "==============================="
echo "Listonian Arbitrage Bot Status"
echo "==============================="
echo
echo "Bot: Running (PID: $bot_pid, check logs/bot_${timestamp}.log for details)"
echo "Dashboard: Running on port ${DASHBOARD_PORT} (PID: $dashboard_pid, check logs/dashboard_${timestamp}.log for details)"
echo
echo "Monitor the logs directory for detailed output."
echo "Press Ctrl+C to stop all processes."
echo

# Handle cleanup on exit
cleanup() {
    echo "Stopping processes..."
    kill $dashboard_pid 2>/dev/null
    kill $bot_pid 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Monitor logs for errors only
tail -f "logs/dashboard_${timestamp}.log" "logs/bot_${timestamp}.log" | grep -i "error\|critical\|fatal" &

# Keep script running
wait
