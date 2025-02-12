import asyncio
import socketio
import json
import sys
from typing import Optional

class DashboardMonitor:
    """Monitor for the arbitrage bot dashboard."""
    
    def __init__(self, start_port: int = 5000, end_port: int = 5010):
        """Initialize dashboard monitor."""
        self.start_port = start_port
        self.end_port = end_port
        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.setup_handlers()
        
    def setup_handlers(self):
        """Set up Socket.IO event handlers."""
        @self.sio.event
        def connect():
            print("Connected to dashboard")
            
        @self.sio.event
        def disconnect():
            print("Disconnected from dashboard")
            
        @self.sio.on('memory_stats')
        def on_memory_stats(data):
            print("\nMemory Stats:")
            print(json.dumps(data, indent=2))
            
        @self.sio.on('storage_stats')
        def on_storage_stats(data):
            print("\nStorage Stats:")
            print(json.dumps(data, indent=2))
            
        @self.sio.on('distribution_stats')
        def on_distribution_stats(data):
            print("\nDistribution Stats:")
            print(json.dumps(data, indent=2))
            
        @self.sio.on('execution_stats')
        def on_execution_stats(data):
            print("\nExecution Stats:")
            print(json.dumps(data, indent=2))
    
    def find_dashboard_port(self) -> Optional[int]:
        """Try to connect to dashboard on different ports."""
        for port in range(self.start_port, self.end_port + 1):
            try:
                url = f'http://localhost:{port}'
                print(f"Trying to connect to {url}...")
                self.sio.connect(url, wait_timeout=2)
                print(f"Successfully connected to dashboard on port {port}")
                return port
            except Exception as e:
                print(f"Could not connect to port {port}: {e}")
                continue
        return None
    
    def run(self):
        """Run the dashboard monitor."""
        try:
            port = self.find_dashboard_port()
            if port is None:
                print("Could not find dashboard on any port")
                return
                
            print("Press Ctrl+C to exit")
            self.sio.wait()
            
        except KeyboardInterrupt:
            print("\nStopping monitor...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if self.sio.connected:
                self.sio.disconnect()

if __name__ == '__main__':
    monitor = DashboardMonitor()
    monitor.run()