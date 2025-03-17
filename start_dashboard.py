"""
Launch script for the Arbitrage Bot Dashboard.
Starts both the dashboard server and monitor in separate processes.
"""

import os
import sys
import subprocess
import time
import psutil
import signal
import logging
import socket
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dashboard port
DASHBOARD_PORT = 9095

def check_dependencies():
    """Check and install required dependencies."""
    required_packages = [
        'aiohttp',
        'python-socketio',
        'psutil',
        'web3'
    ]
    
    try:
        import pkg_resources
        installed = {pkg.key for pkg in pkg_resources.working_set}
        missing = [pkg for pkg in required_packages if pkg.lower() not in installed]
        
        if missing:
            logger.info("Installing missing dependencies...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
            logger.info("Dependencies installed successfully")
    except Exception as e:
        logger.error(f"Error checking/installing dependencies: {e}")
        sys.exit(1)

def kill_process_on_port(port):
    """Kill any process using the specified port."""
    try:
        # Create a test socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Try to connect to the port
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        # If port is in use (connection successful)
        if result == 0:
            # Try taskkill on Windows
            if sys.platform == 'win32':
                try:
                    subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True)
                    time.sleep(1)
                    return True
                except Exception:
                    pass
            
            # Try creating a test socket to force port release
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.bind(('localhost', port))
                test_socket.close()
                return True
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
    
    return False

def start_process(script_name):
    """Start a Python script as a separate process."""
    try:
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1  # Line buffered
        )
        return process
    except Exception as e:
        logger.error(f"Error starting {script_name}: {e}")
        return None

def read_process_output(process, name):
    """Read and log process output."""
    try:
        if process.stdout:
            output = process.stdout.readline()
            if output.strip():
                logger.info(f"[{name}] {output.strip()}")
        if process.stderr:
            error = process.stderr.readline()
            if error.strip():
                logger.error(f"[{name}] {error.strip()}")
    except Exception as e:
        logger.error(f"Error reading {name} output: {e}")

def cleanup_processes(processes):
    """Clean up running processes."""
    for name, process in processes.items():
        if process and process.poll() is None:
            logger.info(f"Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

def main():
    """Main function to start the dashboard system."""
    # Check dependencies first
    check_dependencies()
    
    # Ensure required files exist
    required_files = ['final_dashboard.py', 'dashboard_monitor.py']
    for file in required_files:
        if not Path(file).exists():
            logger.error(f"Required file {file} not found")
            sys.exit(1)
    
    # Kill any process using our port
    if kill_process_on_port(DASHBOARD_PORT):
        logger.info(f"Cleared port {DASHBOARD_PORT}")
    
    processes = {}
    try:
        # Start dashboard server
        logger.info("Starting dashboard server...")
        time.sleep(1)  # Wait for port to be fully released
        dashboard_process = start_process('final_dashboard.py')
        if not dashboard_process:
            sys.exit(1)
        processes['dashboard'] = dashboard_process
        
        # Wait for dashboard to start
        time.sleep(2)
        
        # Start monitor
        logger.info("Starting dashboard monitor...")
        monitor_process = start_process('dashboard_monitor.py')
        if not monitor_process:
            cleanup_processes(processes)
            sys.exit(1)
        processes['monitor'] = monitor_process
        
        logger.info("\nDashboard system is running!")
        logger.info(f"Open http://localhost:{DASHBOARD_PORT} in your browser")
        logger.info("Press Ctrl+C to stop")
        
        # Monitor both processes
        while True:
            try:
                # Check if any process has terminated
                for name, process in processes.items():
                    if process.poll() is not None:
                        logger.error(f"{name} process has terminated unexpectedly")
                        cleanup_processes(processes)
                        sys.exit(1)
                    read_process_output(process, name)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error monitoring processes: {e}")
                
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        cleanup_processes(processes)
        # Make sure the port is cleared
        kill_process_on_port(DASHBOARD_PORT)
        logger.info("Dashboard system stopped")

if __name__ == "__main__":
    main()