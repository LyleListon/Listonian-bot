import os
import sys
import subprocess
import time
import signal
import platform

# Set environment variables
os.environ['PYTHONPATH'] = os.getcwd()
os.environ['MEMORY_BANK_PATH'] = os.path.join(os.getcwd(), 'memory-bank')

# Create necessary directories
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

# Initialize memory bank
try:
    print("Initializing memory bank...")
    subprocess.run([sys.executable, 'scripts/initialize_memory_bank.py'], check=True)
    print("Memory bank initialized successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error initializing memory bank: {e}")
    sys.exit(1)

# Start the dashboard
print("Starting dashboard...")
dashboard_process = None

try:
    # Kill any existing Python processes that might be using the port
    if platform.system() == 'Windows':
        try:
            subprocess.run(['powershell', '-Command', 
                           "Get-NetTCPConnection -LocalPort 9050 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"], 
                           check=False)
        except Exception as e:
            print(f"Warning: Could not kill processes on port 9050: {e}")
    
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
    
    # Try to open the dashboard in the default browser
    print("Opening dashboard in browser...")
    if platform.system() == 'Windows':
        subprocess.run(['start', 'http://localhost:9050'], shell=True, check=False)
    
    print("Dashboard started successfully!")
    print("Dashboard URL: http://localhost:9050")
    
    # Keep the script running to maintain the dashboard
    while True:
        # Check if the process is still running
        if dashboard_process.poll() is not None:
            stdout, stderr = dashboard_process.communicate()
            print(f"Dashboard process exited with code {dashboard_process.returncode}")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            sys.exit(1)
        
        # Read and print output from the dashboard process
        stdout_line = dashboard_process.stdout.readline()
        if stdout_line:
            print(f"DASHBOARD: {stdout_line.strip()}")
        
        stderr_line = dashboard_process.stderr.readline()
        if stderr_line:
            print(f"DASHBOARD ERROR: {stderr_line.strip()}")
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("Stopping dashboard...")
    if dashboard_process:
        if platform.system() == 'Windows':
            dashboard_process.send_signal(signal.CTRL_C_EVENT)
        else:
            dashboard_process.terminate()
        dashboard_process.wait()
    print("Dashboard stopped.")
except Exception as e:
    print(f"Error: {e}")
    if dashboard_process:
        dashboard_process.terminate()
        dashboard_process.wait()
    sys.exit(1)
