"""
Performance metrics collection system.
Collects and processes various system performance metrics.
"""

import psutil
import time
from datetime import datetime
from typing import Dict, List, Optional
import threading
from queue import Queue

class MetricsCollector:
    """Collects and processes system performance metrics."""
    
    def __init__(self):
        self.metrics_queue = Queue()
        self.running = False
        self.collection_thread = None
        self.metrics_history: Dict[str, List[Dict]] = {
            'system': [],
            'trading': [],
            'blockchain': [],
            'memory': []
        }
        self.max_history_size = 1000  # Keep last 1000 data points per metric type

    def start(self):
        """Start metrics collection."""
        if not self.running:
            self.running = True
            self.collection_thread = threading.Thread(
                target=self._collection_loop,
                daemon=True
            )
            self.collection_thread.start()

    def stop(self):
        """Stop metrics collection."""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join()

    def _collection_loop(self):
        """Main metrics collection loop."""
        while self.running:
            try:
                # Collect system metrics
                system_metrics = self.collect_system_metrics()
                self._store_metrics('system', system_metrics)

                # Collect memory metrics
                memory_metrics = self.collect_memory_metrics()
                self._store_metrics('memory', memory_metrics)

                # Process any custom metrics in the queue
                while not self.metrics_queue.empty():
                    metric_type, metric_data = self.metrics_queue.get_nowait()
                    self._store_metrics(metric_type, metric_data)

                time.sleep(1)  # Collect metrics every second
            except Exception as e:
                from ..manager import monitor
                monitor.track_error(e, {
                    'component': 'metrics_collector',
                    'timestamp': datetime.now().isoformat()
                })
                time.sleep(5)  # Back off on error

    def _store_metrics(self, metric_type: str, metrics: Dict):
        """Store metrics with timestamp."""
        if metric_type not in self.metrics_history:
            self.metrics_history[metric_type] = []

        metrics['timestamp'] = datetime.now().isoformat()
        self.metrics_history[metric_type].append(metrics)

        # Maintain history size limit
        if len(self.metrics_history[metric_type]) > self.max_history_size:
            self.metrics_history[metric_type].pop(0)

    def collect_system_metrics(self) -> Dict:
        """Collect system performance metrics."""
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent,
            'cpu_count': psutil.cpu_count(),
            'load_average': psutil.getloadavg()
        }

    def collect_memory_metrics(self) -> Dict:
        """Collect detailed memory metrics."""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'free': memory.free,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_free': swap.free
        }

    def add_trading_metrics(self, metrics: Dict):
        """Add trading-related metrics."""
        self.metrics_queue.put(('trading', metrics))

    def add_blockchain_metrics(self, metrics: Dict):
        """Add blockchain-related metrics."""
        self.metrics_queue.put(('blockchain', metrics))

    def get_recent_metrics(self, 
                          metric_type: str, 
                          limit: int = 100) -> List[Dict]:
        """Get recent metrics of specified type."""
        if metric_type not in self.metrics_history:
            return []
        
        return self.metrics_history[metric_type][-limit:]

    def get_metrics_summary(self) -> Dict:
        """Get summary of all metrics."""
        summary = {}
        
        for metric_type, metrics in self.metrics_history.items():
            if not metrics:
                continue
                
            latest = metrics[-1]
            summary[metric_type] = {
                'latest': latest,
                'count': len(metrics),
                'timestamp': latest['timestamp']
            }
            
            # Add type-specific summaries
            if metric_type == 'system':
                cpu_values = [m['cpu_percent'] for m in metrics]
                summary[metric_type]['cpu_avg'] = sum(cpu_values) / len(cpu_values)
                summary[metric_type]['cpu_max'] = max(cpu_values)
            
            elif metric_type == 'trading':
                if 'profit' in latest:
                    profits = [m.get('profit', 0) for m in metrics]
                    summary[metric_type]['total_profit'] = sum(profits)
                    summary[metric_type]['avg_profit'] = sum(profits) / len(profits)
        
        return summary

# Global metrics collector instance
metrics_collector = MetricsCollector()