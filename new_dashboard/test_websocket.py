#!/usr/bin/env python
"""
WebSocket Test Client

This script connects to the dashboard WebSocket endpoint and prints received messages.
It can be used to test the WebSocket connection from the command line.
"""

import asyncio
import json
import sys
import time
import websockets
import argparse
from datetime import datetime


async def connect_and_listen(url, timeout=60):
    """Connect to WebSocket and listen for messages."""
    print(f"Connecting to {url}...")
    
    try:
        async with websockets.connect(url) as websocket:
            print(f"Connected to {url}")
            
            # Send initial hello message
            hello_msg = {
                "type": "hello",
                "client": "test-script",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send(json.dumps(hello_msg))
            print(f"Sent: {json.dumps(hello_msg)}")
            
            # Set up ping task
            ping_task = asyncio.create_task(send_pings(websocket))
            
            # Listen for messages with timeout
            start_time = time.time()
            message_count = 0
            
            while time.time() - start_time < timeout:
                try:
                    # Set a timeout for receiving messages
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    message_count += 1
                    
                    # Try to parse as JSON
                    try:
                        data = json.loads(message)
                        print(f"\nReceived message {message_count}:")
                        print(json.dumps(data, indent=2))
                        
                        # Auto-respond to ping messages
                        if data.get("type") == "ping":
                            pong_msg = {
                                "type": "pong",
                                "timestamp": datetime.utcnow().isoformat(),
                                "ping_timestamp": data.get("timestamp")
                            }
                            await websocket.send(json.dumps(pong_msg))
                            print(f"Sent pong response")
                    except json.JSONDecodeError:
                        print(f"\nReceived non-JSON message {message_count}:")
                        print(message)
                    
                except asyncio.TimeoutError:
                    print(".", end="", flush=True)
                    continue
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"\nConnection closed: {e}")
                    break
            
            # Cancel ping task
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass
            
            print(f"\nTest completed. Received {message_count} messages in {time.time() - start_time:.1f} seconds.")
    
    except websockets.exceptions.WebSocketException as e:
        print(f"WebSocket error: {e}")
    except Exception as e:
        print(f"Error: {e}")


async def send_pings(websocket, interval=30):
    """Send periodic ping messages."""
    try:
        while True:
            await asyncio.sleep(interval)
            ping_msg = {
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send(json.dumps(ping_msg))
            print("Sent ping message")
    except asyncio.CancelledError:
        print("Ping task cancelled")
        raise


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="WebSocket Test Client")
    parser.add_argument(
        "--url", 
        default="ws://localhost:9050/ws/metrics",
        help="WebSocket URL to connect to"
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=60,
        help="Test duration in seconds"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(connect_and_listen(args.url, args.timeout))
