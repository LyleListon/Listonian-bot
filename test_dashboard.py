import sys
import subprocess
import time

print("Starting dashboard with explicit error capture...")

# Run the dashboard with explicit output redirection
process = subprocess.Popen(
    [sys.executable, 'run_dashboard.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

print(f"Dashboard process started with PID: {process.pid}")

# Wait for a bit to let it initialize
time.sleep(5)

# Check if the process is still running
if process.poll() is not None:
    stdout, stderr = process.communicate()
    print(f"Dashboard process exited with code {process.returncode}")
    print(f"STDOUT: {stdout}")
    print(f"STDERR: {stderr}")
    sys.exit(1)

print("Dashboard process is running. Monitoring output...")

# Monitor the output for a while
timeout = time.time() + 30  # 30 seconds timeout
while time.time() < timeout:
    # Read output
    stdout_line = process.stdout.readline()
    if stdout_line:
        print(f"DASHBOARD OUT: {stdout_line.strip()}")
    
    stderr_line = process.stderr.readline()
    if stderr_line:
        print(f"DASHBOARD ERR: {stderr_line.strip()}")
    
    # Check if process is still running
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        print(f"Dashboard process exited with code {process.returncode}")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        break
    
    time.sleep(0.1)

print("Test complete. Terminating dashboard process...")
process.terminate()
process.wait()
print("Dashboard process terminated.")
