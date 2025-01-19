#!/usr/bin/env python3
"""Process management CLI for arbitrage bot."""

import os
import sys
import json
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Dict, Any
from arbitrage_bot.core.process.manager import ProcessManager
from arbitrage_bot.utils.config_loader import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ProcessManager')

async def start_instance(manager: ProcessManager, instance_id: str):
    """Start a new bot instance."""
    if await manager.start_instance(instance_id):
        logger.info(f"Started instance {instance_id}")
    else:
        logger.error(f"Failed to start instance {instance_id}")
        
async def stop_instance(manager: ProcessManager, instance_id: str):
    """Stop a bot instance."""
    if await manager.stop_instance(instance_id):
        logger.info(f"Stopped instance {instance_id}")
    else:
        logger.error(f"Failed to stop instance {instance_id}")
        
def print_instance_info(info: Dict[str, Any]):
    """Print instance information."""
    print(f"PID: {info['pid']}")
    print(f"Status: {info['status']}")
    print(f"Uptime: {info['uptime']:.1f} seconds")
    print(f"Memory: {info['memory_mb']:.1f} MB")
    print(f"CPU: {info['cpu_percent']:.1f}%")
    print("Ports:")
    for service, port in info['ports'].items():
        print(f"  {service}: {port}")
    print()
    
async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Arbitrage Bot Process Manager")
    parser.add_argument("action", choices=["start", "stop", "list", "info", "monitor"])
    parser.add_argument("--id", help="Instance ID")
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = load_config()
        
        # Create process manager
        manager = ProcessManager(config)
        
        if args.action == "start":
            if not args.id:
                parser.error("Instance ID required for start action")
            await start_instance(manager, args.id)
            
        elif args.action == "stop":
            if not args.id:
                parser.error("Instance ID required for stop action")
            await stop_instance(manager, args.id)
            
        elif args.action == "list":
            instances = manager.list_instances()
            if not instances:
                print("No instances running")
            else:
                print(f"Running instances ({len(instances)}):")
                for instance in instances:
                    print(f"\nInstance: {instance['instance_id']}")
                    print_instance_info(instance)
                    
        elif args.action == "info":
            if not args.id:
                parser.error("Instance ID required for info action")
            info = manager.get_instance_info(args.id)
            if info:
                print(f"Instance: {args.id}")
                print_instance_info(info)
            else:
                print(f"Instance {args.id} not found")
                
        elif args.action == "monitor":
            print("Starting process monitor...")
            monitor_task = asyncio.create_task(manager.monitor_instances())
            try:
                while True:
                    instances = manager.list_instances()
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"\nRunning instances ({len(instances)}):")
                    for instance in instances:
                        print(f"\nInstance: {instance['instance_id']}")
                        print_instance_info(instance)
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
                print("\nMonitor stopped")
                
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    asyncio.run(main())
