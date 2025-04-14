#!/usr/bin/env python
"""Restart the dashboard server with updated configuration."""

import argparse
import logging
import os
import signal
import subprocess
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("restart_dashboard")

def kill_process_by_port(port):
    """Kill a process listening on a specific port."""
    try:
        # Find process ID using netstat
        if os.name == 'nt':  # Windows
            cmd = f"netstat -ano | findstr :{port}"
            output = subprocess.check_output(cmd, shell=True).decode('utf-8')
            
            # Parse output to find PID
            for line in output.strip().split('\n'):
                if 'LISTENING' in line:
                    pid = line.strip().split()[-1]
                    logger.info(f"Found process {pid} listening on port {port}")
                    
                    # Kill the process
                    subprocess.call(f"taskkill /F /PID {pid}", shell=True)
                    logger.info(f"Killed process {pid}")
                    return True
        else:  # Linux/Mac
            cmd = f"lsof -i :{port} -t"
            pid = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            if pid:
                os.kill(int(pid), signal.SIGTERM)  # Use SIGTERM instead of SIGKILL
                logger.info(f"Killed process {pid}")
                return True
                
        return False
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
        return False

def restart_dashboard(env="test"):
    """Restart the dashboard server.
    
    Args:
        env: Environment to use.
    """
    logger.info(f"Restarting dashboard server in {env} environment")
    
    # Kill existing dashboard server
    dashboard_port = 8081  # Default dashboard port
    api_port = 8001  # Default API port
    
    # Try to kill processes on these ports
    kill_process_by_port(dashboard_port)
    kill_process_by_port(api_port)
    
    # Wait for processes to terminate
    time.sleep(2)
    
    # Start API server
    logger.info("Starting API server")
    api_process = subprocess.Popen(
        ["python", "bot_api_server.py", "--env", env],
        stdout=open("logs/api_restart.log", "w"),
        stderr=subprocess.STDOUT,
    )
    
    # Wait for API server to start
    time.sleep(2)
    
    # Start dashboard server
    logger.info("Starting dashboard server")
    dashboard_process = subprocess.Popen(
        ["python", "run_dashboard.py", "--env", env],
        stdout=open("logs/dashboard_restart.log", "w"),
        stderr=subprocess.STDOUT,
    )
    
    # Wait for dashboard server to start
    time.sleep(2)
    
    # Print URLs
    logger.info("Dashboard server restarted")
    logger.info("API server: http://localhost:8001")
    logger.info("Dashboard: http://localhost:8081")
    
    # Return processes
    return api_process, dashboard_process

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Restart the dashboard server")
    parser.add_argument(
        "--env",
        type=str,
        default="test",
        help="Environment to use (development, production, test)",
    )
    args = parser.parse_args()
    
    api_process, dashboard_process = restart_dashboard(args.env)
    
    # Wait for interrupt
    try:
        while True:
            # Check if processes are still running
            if api_process.poll() is not None:
                logger.error(f"API server process terminated with code {api_process.returncode}")
                break
            
            if dashboard_process.poll() is not None:
                logger.error(f"Dashboard server process terminated with code {dashboard_process.returncode}")
                break
            
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    
    # Stop all processes
    logger.info("Stopping all processes")
    
    for process in [dashboard_process, api_process]:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5.0)
    
    logger.info("All processes stopped")

if __name__ == "__main__":
    main()
