#!/usr/bin/env python3
"""
Run All Components

This script runs all components of the arbitrage bot system.
"""

import os
import sys
import time
import subprocess
import argparse
import signal
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run_all")

# Global variables
processes = []

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run all components of the arbitrage bot system")
    parser.add_argument("--use-real-data", action="store_true", help="Use real data only")
    parser.add_argument("--clear-memory", action="store_true", help="Clear memory bank before starting")
    return parser.parse_args()

def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) to gracefully shut down all processes."""
    logger.info("Shutting down all processes...")
    for proc in processes:
        if proc.poll() is None:  # If process is still running
            logger.info(f"Terminating process: {proc.args}")
            proc.terminate()

    # Wait for processes to terminate
    for proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(f"Process did not terminate gracefully: {proc.args}")
            proc.kill()

    logger.info("All processes terminated")
    sys.exit(0)

def clear_memory_bank():
    """Clear memory bank before starting."""
    logger.info("Clearing memory bank...")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/reset_memory_service.py"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Memory bank cleared successfully")
        logger.debug(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clear memory bank: {e}")
        logger.error(f"Error output: {e.stderr}")
        sys.exit(1)

def start_bot(use_real_data=False):
    """Start the arbitrage bot."""
    logger.info("Starting arbitrage bot...")
    env = os.environ.copy()
    if use_real_data:
        env["USE_REAL_DATA_ONLY"] = "true"

    bot_process = subprocess.Popen(
        [sys.executable, "run_bot.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    processes.append(bot_process)
    logger.info(f"Arbitrage bot started with PID: {bot_process.pid}")
    return bot_process

def start_dashboard(use_real_data=False):
    """Start the dashboard."""
    logger.info("Starting dashboard...")
    env = os.environ.copy()
    if use_real_data:
        env["USE_REAL_DATA_ONLY"] = "true"

    dashboard_process = subprocess.Popen(
        [sys.executable, "run_dashboard.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    processes.append(dashboard_process)
    logger.info(f"Dashboard started with PID: {dashboard_process.pid}")
    return dashboard_process

def monitor_processes():
    """Monitor running processes and log their output."""
    logger.info("Monitoring processes...")

    # Set up process output monitoring
    for proc in processes:
        proc.stdout_lines = []

    try:
        while True:
            for proc in processes:
                if proc.poll() is not None:
                    logger.error(f"Process exited unexpectedly: {proc.args} with code {proc.returncode}")
                    # Print the last few lines of output
                    if proc.stdout_lines:
                        logger.error("Last output lines:")
                        for line in proc.stdout_lines[-10:]:
                            logger.error(f"  {line.strip()}")
                    return False

                # Read output
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break

                    # Store line for debugging
                    proc.stdout_lines.append(line)
                    if len(proc.stdout_lines) > 1000:
                        proc.stdout_lines.pop(0)

                    # Print line with process identifier
                    process_name = "bot" if "run_bot.py" in proc.args else "dashboard"
                    print(f"[{process_name}] {line.strip()}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        return False

    return True

def main():
    """Main entry point."""
    args = parse_args()

    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Starting all components of the arbitrage bot system")
    logger.info(f"Use real data only: {args.use_real_data}")

    # Clear memory bank if requested
    if args.clear_memory:
        clear_memory_bank()

    # Start components
    bot_process = start_bot(args.use_real_data)
    time.sleep(2)  # Give the bot a head start

    dashboard_process = start_dashboard(args.use_real_data)
    time.sleep(2)  # Wait for dashboard to start

    # Open dashboard in browser
    dashboard_port = int(os.environ.get("DASHBOARD_PORT", 9050))
    dashboard_url = f"http://localhost:{dashboard_port}"
    logger.info(f"Dashboard available at: {dashboard_url}")

    try:
        import webbrowser
        webbrowser.open(dashboard_url)
    except Exception as e:
        logger.warning(f"Failed to open browser: {e}")

    # Monitor processes
    success = monitor_processes()

    # Cleanup
    signal_handler(None, None)

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
