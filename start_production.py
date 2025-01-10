"""Start production bot and dashboard with environment variables."""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Start production bot and dashboard."""
    print("Starting Arbitrage Bot and Dashboard in LIVE MODE...")

    # Check if .env.production exists
    if not Path('.env.production').exists():
        print("Error: .env.production file not found")
        print("Please copy .env.production.template and fill in your settings")
        sys.exit(1)

    # Check if production config exists
    if not Path('configs/production_config.json').exists():
        print("Error: configs/production_config.json not found")
        sys.exit(1)

    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)

    # Load environment variables from .env.production
    load_dotenv('.env.production')

    # Set different WebSocket ports for bot and dashboard
    env = os.environ.copy()
    env['BOT_WEBSOCKET_PORT'] = '8770'  # Bot WebSocket port
    env['DASHBOARD_WEBSOCKET_PORT'] = '8771'  # Dashboard WebSocket port

    # Start bot process
    bot_process = subprocess.Popen(
        ['python', 'production.py'],
        env=env
    )

    # Start dashboard process
    dashboard_process = subprocess.Popen(
        ['python', '-m', 'arbitrage_bot.dashboard.run'],
        env=env
    )

    print("Bot and dashboard started in LIVE MODE.")
    print("Press Ctrl+C to stop all processes...")

    try:
        # Wait for processes to complete
        bot_process.wait()
        dashboard_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        bot_process.terminate()
        dashboard_process.terminate()
        bot_process.wait()
        dashboard_process.wait()
        print("All processes stopped.")

if __name__ == '__main__':
    main()
