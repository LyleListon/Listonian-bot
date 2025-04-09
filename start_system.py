#!/usr/bin/env python3
"""
Comprehensive system startup script that ensures all components are running correctly.
"""

import os
import sys
import subprocess
import time
import signal
import platform
import webbrowser
from pathlib import Path

# Check if .env file exists
def check_env_file():
    """Check if .env file exists and create a sample one if it doesn't."""
    if not os.path.exists('.env'):
        print("Error: .env file not found")
        print("Creating a sample .env file...")

        with open('.env', 'w') as f:
            f.write("""# Base Network RPC URL (Required)
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY

# Wallet Configuration (Required)
PRIVATE_KEY=YOUR_PRIVATE_KEY
WALLET_ADDRESS=YOUR_WALLET_ADDRESS
PROFIT_RECIPIENT=YOUR_WALLET_ADDRESS

# Flashbots Configuration (Required)
FLASHBOTS_AUTH_KEY=YOUR_FLASHBOTS_KEY

# API Keys (Required)
ALCHEMY_API_KEY=YOUR_API_KEY

# Optional Configuration
LOG_LEVEL=INFO
DASHBOARD_ENABLED=true
DASHBOARD_PORT=9050

# Memory Bank Path for Dashboard
MEMORY_BANK_PATH=./memory-bank
""")

        print("Sample .env file created. Please edit it with your actual values.")

        # Open the file in a text editor
        if platform.system() == 'Windows':
            os.system('notepad .env')
        elif platform.system() == 'Darwin':  # macOS
            os.system('open -a TextEdit .env')
        else:  # Linux and other Unix-like systems
            editors = ['nano', 'vim', 'vi', 'gedit']
            for editor in editors:
                try:
                    subprocess.run(['which', editor], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    os.system(f'{editor} .env')
                    break
                except subprocess.CalledProcessError:
                    continue

        print("Please restart this script after editing the .env file.")
        sys.exit(1)

    print(".env file found")

# Now load the environment variables
from dotenv import load_dotenv
load_dotenv()

# Get dashboard port from environment or use default
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", 9050))

# Set environment variables
os.environ['PYTHONPATH'] = os.getcwd()
os.environ['MEMORY_BANK_PATH'] = os.path.join(os.getcwd(), 'memory-bank')

# Global process tracking
processes = {
    'dashboard': None,
    'bot': None,
    'mcp_servers': []
}

def create_directories():
    """Create necessary directories for the system."""
    print("Creating necessary directories...")
    directories = [
        'logs',
        'memory-bank',
        'memory-bank/trades',
        'memory-bank/metrics',
        'memory-bank/state'
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    print("Directories created successfully.")

def initialize_memory_bank():
    """Initialize the memory bank with sample data."""
    print("Initializing memory bank...")
    try:
        subprocess.run([sys.executable, 'scripts/initialize_memory_bank.py'], check=True)
        print("Memory bank initialized successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error initializing memory bank: {e}")
        sys.exit(1)

def kill_processes_on_port(port):
    """Kill any processes using the specified port."""
    print(f"Killing any processes using port {port}...")
    if platform.system() == 'Windows':
        try:
            subprocess.run(['powershell', '-Command',
                           f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}"],
                           check=False)
        except Exception as e:
            print(f"Warning: Could not kill processes on port {port}: {e}")

def start_dashboard():
    """Start the dashboard component."""
    print("Starting dashboard...")

    # Kill any existing processes on the dashboard port
    kill_processes_on_port(DASHBOARD_PORT)

    # Start the dashboard with explicit output redirection
    dashboard_process = subprocess.Popen(
        [sys.executable, 'run_dashboard.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    print(f"Dashboard started with PID: {dashboard_process.pid}")

    # Wait for the dashboard to initialize
    print("Waiting for dashboard to initialize...")
    time.sleep(5)

    # Check if the process is still running
    if dashboard_process.poll() is not None:
        stdout, stderr = dashboard_process.communicate()
        print(f"Dashboard process exited with code {dashboard_process.returncode}")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        sys.exit(1)

    # Store the process
    processes['dashboard'] = dashboard_process

    # Try to open the dashboard in the default browser
    print("Opening dashboard in browser...")
    try:
        webbrowser.open(f"http://localhost:{DASHBOARD_PORT}")
    except Exception as e:
        print(f"Warning: Could not open browser: {e}")

    print("Dashboard started successfully!")
    print(f"Dashboard URL: http://localhost:{DASHBOARD_PORT}")

def start_bot():
    """Start the arbitrage bot."""
    print("Starting arbitrage bot...")

    # Start the bot with explicit output redirection
    bot_process = subprocess.Popen(
        [sys.executable, 'run_bot.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    print(f"Bot started with PID: {bot_process.pid}")

    # Wait for the bot to initialize
    print("Waiting for bot to initialize...")
    time.sleep(5)

    # Check if the process is still running
    if bot_process.poll() is not None:
        stdout, stderr = bot_process.communicate()
        print(f"Bot process exited with code {bot_process.returncode}")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        sys.exit(1)

    # Store the process
    processes['bot'] = bot_process

    print("Bot started successfully!")

def monitor_processes():
    """Monitor all running processes and restart if necessary."""
    try:
        while True:
            # Check dashboard
            if processes['dashboard'] and processes['dashboard'].poll() is not None:
                stdout, stderr = processes['dashboard'].communicate()
                print(f"Dashboard process exited with code {processes['dashboard'].returncode}")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                print("Restarting dashboard...")
                start_dashboard()

            # Check bot
            if processes['bot'] and processes['bot'].poll() is not None:
                stdout, stderr = processes['bot'].communicate()
                print(f"Bot process exited with code {processes['bot'].returncode}")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                print("Restarting bot...")
                start_bot()

            # Read and print output from the dashboard process
            if processes['dashboard']:
                stdout_line = processes['dashboard'].stdout.readline()
                if stdout_line:
                    print(f"DASHBOARD: {stdout_line.strip()}")

                stderr_line = processes['dashboard'].stderr.readline()
                if stderr_line:
                    print(f"DASHBOARD ERROR: {stderr_line.strip()}")

            # Read and print output from the bot process
            if processes['bot']:
                stdout_line = processes['bot'].stdout.readline()
                if stdout_line:
                    print(f"BOT: {stdout_line.strip()}")

                stderr_line = processes['bot'].stderr.readline()
                if stderr_line:
                    print(f"BOT ERROR: {stderr_line.strip()}")

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping all processes...")
        cleanup()
        print("All processes stopped.")

def cleanup():
    """Clean up all processes."""
    # Stop dashboard
    if processes['dashboard']:
        print("Stopping dashboard...")
        if platform.system() == 'Windows':
            processes['dashboard'].send_signal(signal.CTRL_C_EVENT)
        else:
            processes['dashboard'].terminate()
        processes['dashboard'].wait(timeout=5)

    # Stop bot
    if processes['bot']:
        print("Stopping bot...")
        if platform.system() == 'Windows':
            processes['bot'].send_signal(signal.CTRL_C_EVENT)
        else:
            processes['bot'].terminate()
        processes['bot'].wait(timeout=5)

    # Stop MCP servers
    for mcp_server in processes['mcp_servers']:
        print(f"Stopping MCP server with PID: {mcp_server.pid}...")
        if platform.system() == 'Windows':
            mcp_server.send_signal(signal.CTRL_C_EVENT)
        else:
            mcp_server.terminate()
        mcp_server.wait(timeout=5)

def main():
    """Main function to start all components."""
    try:
        # Check .env file
        print("\nStep 1: Checking .env file...")
        check_env_file()

        # Create directories
        create_directories()

        # Initialize memory bank
        initialize_memory_bank()

        # Start dashboard
        start_dashboard()

        # Start bot
        start_bot()

        # Monitor processes
        monitor_processes()
    except Exception as e:
        print(f"Error: {e}")
        cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()
