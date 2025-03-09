"""System monitoring utility"""

import psutil
import time
from typing import Dict, Any


class SystemMonitor:
    """System resource monitor"""

    def __init__(self):
        """Initialize system monitor"""
        self.process = psutil.Process()
        self.last_net_io = psutil.net_io_counters()
        self.last_check = time.time()

    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics

        Returns:
            Dictionary containing system stats
        """
        # CPU
        cpu_percent = psutil.cpu_percent()

        # Memory
        memory = psutil.virtual_memory()
        memory_stats = {
            "total": memory.total / (1024 * 1024 * 1024),  # GB
            "used": memory.used / (1024 * 1024 * 1024),  # GB
            "percent": memory.percent,
        }

        # Disk
        disk = psutil.disk_usage("/")
        disk_stats = {
            "total": disk.total / (1024 * 1024 * 1024),  # GB
            "used": disk.used / (1024 * 1024 * 1024),  # GB
            "percent": disk.percent,
        }

        # Network I/O
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        time_diff = current_time - self.last_check

        bytes_sent = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / (
            1024 * 1024
        )  # MB
        bytes_recv = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / (
            1024 * 1024
        )  # MB
        packets_sent = current_net_io.packets_sent - self.last_net_io.packets_sent
        packets_recv = current_net_io.packets_recv - self.last_net_io.packets_recv

        network_stats = {
            "bytes_sent": bytes_sent / time_diff,
            "bytes_recv": bytes_recv / time_diff,
            "packets_sent": packets_sent,
            "packets_recv": packets_recv,
        }

        self.last_net_io = current_net_io
        self.last_check = current_time

        # Process stats
        process_stats = {
            "cpu_percent": self.process.cpu_percent(),
            "memory_percent": self.process.memory_percent(),
            "threads": self.process.num_threads(),
            "open_files": len(self.process.open_files()),
        }

        return {
            "cpu": cpu_percent,
            "memory": memory_stats,
            "disk": disk_stats,
            "network": network_stats,
            "process": process_stats,
        }
