"""Start production bot and dashboard with environment variables."""

import os
import sys
import signal
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Global flag for shutdown
shutdown_flag = False

def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_flag
    print(f"\nReceived signal {signum}")
    print("Initiating graceful shutdown...")
    shutdown_flag = True

# Register signal handlers
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

class ProcessManager:
    """Manage production processes."""
    
    def __init__(self):
        self.processes = {}
        self.env = os.environ.copy()
    
    async def start_process(self, name: str, command: list):
        """Start a process and monitor it."""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                env=self.env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.processes[name] = process
            print(f"Started {name} (PID: {process.pid})")
            
            # Monitor process output
            await asyncio.gather(
                self._monitor_output(name, process.stdout, "stdout"),
                self._monitor_output(name, process.stderr, "stderr")
            )
            
            return process
        except Exception as e:
            print(f"Error starting {name}: {e}")
            return None
    
    async def _monitor_output(self, name: str, stream: asyncio.StreamReader, stream_name: str):
        """Monitor process output stream."""
        while True:
            line = await stream.readline()
            if not line:
                break
            print(f"[{name}] {line.decode().strip()}")
    
    async def stop_all(self):
        """Stop all processes gracefully."""
        print("\nStopping all processes...")
        for name, process in self.processes.items():
            print(f"Stopping {name}...")
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
                print(f"Stopped {name}")
            except asyncio.TimeoutError:
                print(f"Force killing {name}...")
                process.kill()
                await process.wait()
            except Exception as e:
                print(f"Error stopping {name}: {e}")

async def main():
    """Start production bot and dashboard."""
    print("=" * 70)
    print("STARTING ARBITRAGE BOT AND DASHBOARD IN PRODUCTION MODE")
    print("=" * 70)

    # Verify required files
    required_files = {
        'Production config': Path('configs/production.json'),
        'Environment file': Path('.env'),
        'Production script': Path('production.py'),
        'Dashboard module': Path('arbitrage_bot/dashboard/run.py')
    }

    for name, path in required_files.items():
        if not path.exists():
            print(f"Error: {name} not found at {path}")
            print("Please ensure all required files are in place")
            sys.exit(1)

    # Create required directories
    Path('logs').mkdir(exist_ok=True)
    Path('monitoring_data').mkdir(exist_ok=True)

    # Load environment variables
    load_dotenv('.env')

    # Set WebSocket ports
    os.environ['BOT_WEBSOCKET_PORT'] = '8770'
    os.environ['DASHBOARD_WEBSOCKET_PORT'] = '8771'

    # Initialize process manager
    manager = ProcessManager()

    try:
        # Start bot and dashboard
        await asyncio.gather(
            manager.start_process(
                'bot',
                ['python', 'production.py']
            ),
            manager.start_process(
                'dashboard',
                ['python', '-m', 'arbitrage_bot.dashboard.run']
            )
        )

        print("\nBot and dashboard started in PRODUCTION MODE")
        print("Monitor the system at: http://localhost:8080")
        print("\nPress Ctrl+C to stop all processes...")

        # Wait for shutdown signal
        while not shutdown_flag:
            await asyncio.sleep(1)

    except Exception as e:
        print(f"\nError in main process: {e}")
    finally:
        # Ensure proper cleanup
        await manager.stop_all()
        print("\nAll processes stopped")
        print("System shutdown complete")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Handle through signal handler
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
