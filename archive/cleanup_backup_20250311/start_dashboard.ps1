# PowerShell script to start dashboard with proper environment setup

Write-Host "Starting dashboard with eventlet patching..."

# Create a temporary Python script that will be run in a fresh interpreter
$tempScript = @"
import sys
import os

# Set up the environment
os.environ['PYTHONPATH'] = '.'
os.environ['PYTHONASYNCIODEBUG'] = '1'
os.environ['PYTHONUNBUFFERED'] = '1'

# Create another temporary script for the actual patching
patch_script = '''
# This must be the first import
import eventlet
eventlet.monkey_patch(all=True)

import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('dashboard')

def verify_patch():
    import socket
    import threading
    import time
    
    is_socket_patched = 'eventlet.green.socket' in str(socket.socket)
    is_threading_patched = 'eventlet.green.threading' in str(threading.Thread)
    is_time_patched = hasattr(time.sleep, '__module__') and 'eventlet' in time.sleep.__module__
    
    logger.info(f'Socket patched: {is_socket_patched}')
    logger.info(f'Threading patched: {is_threading_patched}')
    logger.info(f'Time patched: {is_time_patched}')
    
    return all([is_socket_patched, is_threading_patched, is_time_patched])

if verify_patch():
    logger.info('Eventlet patching verified')
    from arbitrage_bot.dashboard.run import main
    main()
else:
    logger.error('Failed to verify eventlet patching')
    sys.exit(1)
'''

# Write the patch script
with open('temp_patch.py', 'w') as f:
    f.write(patch_script)

# Execute the patch script in a fresh Python process
import subprocess
subprocess.run([sys.executable, 'temp_patch.py'])

# Clean up
import os
if os.path.exists('temp_patch.py'):
    os.remove('temp_patch.py')
"@

# Write the temporary launcher script
$tempFile = Join-Path $PWD "temp_launcher.py"
$tempScript | Out-File -Encoding UTF8 $tempFile

try {
    # Run the launcher script
    Write-Host "Running dashboard..."
    python $tempFile

} finally {
    # Clean up
    if (Test-Path $tempFile) {
        Remove-Item $tempFile
    }
}