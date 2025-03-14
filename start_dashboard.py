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
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    # Check each process's connections
                    for conn in proc.connections():
                        if conn.laddr.port == port:
                            logger.info(f"Killing process {proc.pid} using port {port}")
                            if sys.platform == 'win32':
                                subprocess.run(['taskkill', '/F', '/PID', str(proc.pid)], capture_output=True)
                            else:
                                os.kill(proc.pid, signal.SIGTERM)
                            time.sleep(1)  # Wait for process to terminate
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
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

def monitor_process(process, script_name):
    """Monitor a process's output and status."""
    while True:
        output = process.stdout.readline()
        if output:
            logger.info(f"[{script_name}] {output.strip()}")
        
        error = process.stderr.readline()
        if error:
            logger.error(f"[{script_name}] {error.strip()}")
        
        if output == '' and error == '' and process.poll() is not None:
            break

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
            # Check if either process has terminated
            for name, process in processes.items():
                if process.poll() is not None:
                    logger.error(f"{name} process has terminated unexpectedly")
                    cleanup_processes(processes)
                    sys.exit(1)
            
            # Monitor output
            for name, process in processes.items():
                output = process.stdout.readline()
                if output:
                    logger.info(f"[{name}] {output.strip()}")
                error = process.stderr.readline()
                if error:
                    logger.error(f"[{name}] {error.strip()}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        cleanup_processes(processes)
        # Make sure the port is cleared
        kill_process_on_port(DASHBOARD_PORT)
        logger.info("Dashboard system stopped")

if __name__ == "__main__":
    main()